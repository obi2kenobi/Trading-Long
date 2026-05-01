"""Download OHLCV data from Yahoo Finance for SPY, QQQ, IWM at 240m and 1d."""
from __future__ import annotations
import sys
from pathlib import Path
import yfinance as yf
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TICKERS = ["SPY", "QQQ", "IWM"]

JOBS = [
    {"interval": "4h",  "period": "729d", "label": "240m"},
    {"interval": "1d",  "period": "10y",  "label": "1d"},
]


def fetch_one(ticker: str, interval: str, period: str) -> pd.DataFrame:
    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
        prepost=False,
    )
    if df.empty:
        raise RuntimeError(f"empty data: {ticker} {interval} {period}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    keep = ["open", "high", "low", "close", "volume"]
    df = df[keep].dropna()
    df.index.name = "datetime"
    return df


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for tk in TICKERS:
        for job in JOBS:
            df = fetch_one(tk, job["interval"], job["period"])
            out = DATA_DIR / f"{tk}_{job['label']}.csv"
            df.to_csv(out)
            summary.append({
                "ticker": tk,
                "tf": job["label"],
                "rows": len(df),
                "first": str(df.index[0]),
                "last": str(df.index[-1]),
            })
            print(f"saved {out.name}: {len(df)} rows  [{df.index[0]} -> {df.index[-1]}]")

    print("\n=== Summary ===")
    print(pd.DataFrame(summary).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
