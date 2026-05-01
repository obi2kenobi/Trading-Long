"""Side-by-side comparison: v6.4 fixed-% baseline vs globally-optimized ATR set.

Runs full-period backtest (no train/test split) on each (ticker, tf) for each
parameter set and prints a comparison table.

Optimized set comes from the global walk-forward (best mean Sharpe across all
24 folds spanning 6 instruments). It is meant to be the SINGLE robust set we
ship in the Pine script.
"""
from __future__ import annotations
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.strategy import StrategyParams, compute_signals
from src.backtest_engine import run_backtest
from src.metrics import compute_metrics, buy_and_hold_return


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS = Path(__file__).resolve().parent.parent / "reports"

TICKERS = ["SPY", "QQQ", "IWM"]
TF_LABELS = ["240m", "1d"]


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df[["open", "high", "low", "close", "volume"]].dropna()


def baseline_params() -> StrategyParams:
    return StrategyParams()  # v6.4 fixed % defaults


def optimized_params() -> StrategyParams:
    """Best from global walk-forward: balanced Sharpe + DD profile.

    sl=1.5, tp1=1.5, tp2=5.0, tp3=8.0, trail=3.0 (all in ATR multiples)
    Mean Sharpe 0.69, worst-fold DD -13.5%, mean PF 1.47 across 24 folds.
    """
    p = StrategyParams()
    p.use_atr_targets = True
    p.sl_atr_mult = 1.5
    p.tp1_atr_mult = 1.5
    p.tp2_atr_mult = 5.0
    p.tp3_atr_mult = 8.0
    p.trailing_activation_atr_mult = 3.0
    p.trailing_offset_atr_mult = 0.5
    return p


def run_one(ticker: str, tf: str, params: StrategyParams, label: str) -> dict:
    df = load_csv(DATA_DIR / f"{ticker}_{tf}.csv")
    daily_df = load_csv(DATA_DIR / f"{ticker}_1d.csv") if tf != "1d" else df
    sig = compute_signals(df, params, daily_df=daily_df)
    res = run_backtest(df, sig, params)
    m = compute_metrics(res)
    return {
        "label": label, "ticker": ticker, "tf": tf,
        "trades": m.n_trades,
        "winrate%": round(m.win_rate_pct, 1),
        "PF": round(m.profit_factor, 2) if m.profit_factor != float("inf") else "inf",
        "ret%": round(m.total_return_pct, 1),
        "CAGR%": round(m.cagr_pct, 2),
        "Sharpe": round(m.sharpe, 2),
        "MaxDD%": round(m.max_drawdown_pct, 1),
        "BH%": round(buy_and_hold_return(df), 1),
    }


def main() -> None:
    rows = []
    for tk in TICKERS:
        for tf in TF_LABELS:
            rows.append(run_one(tk, tf, baseline_params(), "v6.4_fixed%"))
            rows.append(run_one(tk, tf, optimized_params(), "ATR_optimized"))

    df = pd.DataFrame(rows)
    df.to_csv(REPORTS / "comparison.csv", index=False)

    # Pretty print: pivot per metric
    print("=" * 130)
    print("COMPARISON — v6.4 (fixed %) vs ATR-optimized (sl=2.0, tp=1.5/5/8 ATR, trail @ 3.0 ATR)")
    print("=" * 130)
    print(df.to_string(index=False))

    print()
    print("=== DELTA (optimized - baseline) ===")
    pivot = df.pivot_table(index=["ticker", "tf"], columns="label",
                           values=["PF", "ret%", "CAGR%", "Sharpe", "MaxDD%", "trades"], aggfunc="first")
    print(pivot.to_string())


if __name__ == "__main__":
    main()
