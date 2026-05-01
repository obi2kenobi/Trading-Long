"""Run baseline backtest (v6.4 default params) across SPY/QQQ/IWM, 4h and 1d."""
from __future__ import annotations
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.strategy import StrategyParams, compute_signals
from src.backtest_engine import run_backtest
from src.metrics import compute_metrics, buy_and_hold_return


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TICKERS = ["SPY", "QQQ", "IWM"]
TF_LABELS = ["240m", "1d"]


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    return df


def run_one(ticker: str, tf: str, params: StrategyParams) -> dict:
    df = load_csv(DATA_DIR / f"{ticker}_{tf}.csv")
    daily_df = load_csv(DATA_DIR / f"{ticker}_1d.csv") if tf != "1d" else df
    sig = compute_signals(df, params, daily_df=daily_df)
    res = run_backtest(df, sig, params)
    m = compute_metrics(res)
    return {
        "ticker": ticker,
        "tf": tf,
        "trades": m.n_trades,
        "winrate%": round(m.win_rate_pct, 1),
        "avg_trade%": round(m.avg_trade_pct, 2),
        "PF": round(m.profit_factor, 2) if m.profit_factor != float("inf") else "inf",
        "total_ret%": round(m.total_return_pct, 1),
        "CAGR%": round(m.cagr_pct, 2),
        "Sharpe": round(m.sharpe, 2),
        "Sortino": round(m.sortino, 2),
        "MaxDD%": round(m.max_drawdown_pct, 1),
        "DD_bars": m.longest_dd_bars,
        "BH%": round(buy_and_hold_return(df), 1),
        "avg_bars": round(m.avg_bars_held, 1),
    }


def main() -> None:
    p = StrategyParams()
    rows = []
    for tk in TICKERS:
        for tf in TF_LABELS:
            print(f"  running {tk} {tf}...", flush=True)
            rows.append(run_one(tk, tf, p))
    df = pd.DataFrame(rows)
    print()
    print("=" * 120)
    print("BASELINE — TEMA-ST-WT v6.4 default parameters")
    print("=" * 120)
    print(df.to_string(index=False))
    out = Path(__file__).resolve().parent.parent / "reports" / "baseline.csv"
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()
