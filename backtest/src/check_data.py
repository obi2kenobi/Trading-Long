"""Sanity checks on downloaded OHLCV: duplicates, gaps, NaN, zero volume, OHLC integrity."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def check_one(path: Path) -> dict:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    issues = []

    if df.index.has_duplicates:
        issues.append(f"duplicates={df.index.duplicated().sum()}")

    nans = df[["open", "high", "low", "close", "volume"]].isna().sum().sum()
    if nans:
        issues.append(f"NaN={nans}")

    zero_vol = (df["volume"] == 0).sum()
    if zero_vol:
        issues.append(f"zero_volume={zero_vol}")

    bad_ohlc = (
        (df["high"] < df["low"]).sum()
        + (df["high"] < df["open"]).sum()
        + (df["high"] < df["close"]).sum()
        + (df["low"] > df["open"]).sum()
        + (df["low"] > df["close"]).sum()
    )
    if bad_ohlc:
        issues.append(f"OHLC_inconsistent={bad_ohlc}")

    deltas = df.index.to_series().diff().dropna()
    median_delta = deltas.median()
    big_gaps = (deltas > median_delta * 5).sum()

    return {
        "file": path.name,
        "rows": len(df),
        "first": str(df.index[0]),
        "last": str(df.index[-1]),
        "median_delta": str(median_delta),
        "big_gaps_>5x": int(big_gaps),
        "min_close": round(float(df["close"].min()), 2),
        "max_close": round(float(df["close"].max()), 2),
        "issues": "; ".join(issues) if issues else "OK",
    }


def main() -> None:
    files = sorted(DATA_DIR.glob("*.csv"))
    rows = [check_one(p) for p in files]
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
