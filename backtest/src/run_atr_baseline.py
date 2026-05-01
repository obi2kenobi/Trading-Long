"""Baseline with ATR-adaptive SL/TP (fixed multipliers, same across all instruments).

This shows whether ATR-adaptive targets alone improve the strategy on the more
volatile instruments (IWM, QQQ-4h) vs the v6.4 fixed-% baseline.

Defaults (R:R is symmetric across instruments because ATR scales):
  SL  : 1.5 x ATR
  TP1 : 1.5 x ATR  (R:R 1:1, closes 30%)
  TP2 : 3.0 x ATR  (R:R 1:2, closes 30% of remaining)
  TP3 : 5.0 x ATR  (R:R 1:3.3, closes the rest)
  Trail arm at +2.0 x ATR profit -> stop moves to entry + 0.5 x ATR
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
TICKERS = ["SPY", "QQQ", "IWM"]
TF_LABELS = ["240m", "1d"]


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df[["open", "high", "low", "close", "volume"]].dropna()


def make_atr_params() -> StrategyParams:
    p = StrategyParams()
    p.use_atr_targets = True
    p.sl_atr_mult = 1.5
    p.tp1_atr_mult = 1.5
    p.tp2_atr_mult = 3.0
    p.tp3_atr_mult = 5.0
    p.trailing_activation_atr_mult = 2.0
    p.trailing_offset_atr_mult = 0.5
    return p


def run_one(ticker: str, tf: str, p: StrategyParams) -> dict:
    df = load_csv(DATA_DIR / f"{ticker}_{tf}.csv")
    daily_df = load_csv(DATA_DIR / f"{ticker}_1d.csv") if tf != "1d" else df
    sig = compute_signals(df, p, daily_df=daily_df)
    res = run_backtest(df, sig, p)
    m = compute_metrics(res)
    return {
        "ticker": ticker, "tf": tf, "trades": m.n_trades,
        "winrate%": round(m.win_rate_pct, 1),
        "avg_trade%": round(m.avg_trade_pct, 2),
        "PF": round(m.profit_factor, 2) if m.profit_factor != float("inf") else "inf",
        "total_ret%": round(m.total_return_pct, 1),
        "CAGR%": round(m.cagr_pct, 2),
        "Sharpe": round(m.sharpe, 2),
        "MaxDD%": round(m.max_drawdown_pct, 1),
        "BH%": round(buy_and_hold_return(df), 1),
        "avg_bars": round(m.avg_bars_held, 1),
    }


def main() -> None:
    p = make_atr_params()
    rows = []
    for tk in TICKERS:
        for tf in TF_LABELS:
            print(f"  running {tk} {tf}...", flush=True)
            rows.append(run_one(tk, tf, p))
    out = pd.DataFrame(rows)
    print()
    print("=" * 110)
    print("ATR-ADAPTIVE — SL=1.5xATR, TP=1.5/3/5xATR, trail arm @ 2xATR")
    print("=" * 110)
    print(out.to_string(index=False))
    save_to = Path(__file__).resolve().parent.parent / "reports" / "atr_baseline.csv"
    out.to_csv(save_to, index=False)
    print(f"\nsaved: {save_to}")


if __name__ == "__main__":
    main()
