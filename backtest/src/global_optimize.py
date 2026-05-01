"""Global optimization: find ONE ATR-multiplier set that maximizes aggregate
performance across all (ticker, tf) combinations.

This produces a single, robust parameter set we can ship in the Pine script.
"""
from __future__ import annotations
from itertools import product
from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.strategy import StrategyParams, compute_signals
from src.backtest_engine import run_backtest
from src.metrics import compute_metrics
from src.walk_forward import (
    SEARCH_SPACE, _all_combos, _make_params, load_csv, _slice_signals, _make_folds,
)


REPORTS = Path(__file__).resolve().parent.parent / "reports"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

INSTRUMENTS = [
    ("SPY", "240m", 3),
    ("SPY", "1d", 5),
    ("QQQ", "240m", 3),
    ("QQQ", "1d", 5),
    ("IWM", "240m", 3),
    ("IWM", "1d", 5),
]


def _precompute(ticker: str, tf: str, n_folds: int):
    df = load_csv(DATA_DIR / f"{ticker}_{tf}.csv")
    daily_df = load_csv(DATA_DIR / f"{ticker}_1d.csv") if tf != "1d" else df
    sig = compute_signals(df, StrategyParams(), daily_df=daily_df)
    folds = _make_folds(len(df), n_folds)
    return df, sig, folds


def evaluate_combo_global(combo: dict, datasets) -> dict:
    p = _make_params(combo)
    sharpes = []
    pfs = []
    dds = []
    rets = []
    n_trades_total = 0
    fold_count = 0
    for ticker, tf, df, sig, folds in datasets:
        for s, e in folds:
            sub_df = df.iloc[s:e]
            if len(sub_df) < 30:
                continue
            sub_sig = _slice_signals(sig, sub_df.index)
            try:
                res = run_backtest(sub_df, sub_sig, p)
                m = compute_metrics(res)
            except Exception:
                continue
            sharpes.append(m.sharpe)
            pf = m.profit_factor if np.isfinite(m.profit_factor) else np.nan
            pfs.append(pf)
            dds.append(m.max_drawdown_pct)
            rets.append(m.total_return_pct)
            n_trades_total += m.n_trades
            fold_count += 1
    if not sharpes:
        return None
    s_arr = np.array(sharpes, dtype=float)
    return {
        **combo,
        "mean_Sh": float(s_arr.mean()),
        "std_Sh": float(s_arr.std()),
        "min_Sh": float(s_arr.min()),
        "mean_PF": float(np.nanmean(pfs)),
        "mean_DD": float(np.mean(dds)),
        "worst_DD": float(np.min(dds)),
        "mean_Ret": float(np.mean(rets)),
        "n_trades": n_trades_total,
        "n_folds": fold_count,
    }


def main() -> None:
    print("Pre-computing signals on all instruments...")
    datasets = []
    for ticker, tf, n_folds in INSTRUMENTS:
        df, sig, folds = _precompute(ticker, tf, n_folds)
        datasets.append((ticker, tf, df, sig, folds))
        print(f"  {ticker} {tf}: n={len(df)} folds={n_folds}")

    combos = _all_combos()
    print(f"\nEvaluating {len(combos)} combos across {sum(f[2] for f in INSTRUMENTS)} folds each...\n")
    rows = []
    for i, combo in enumerate(combos, 1):
        r = evaluate_combo_global(combo, datasets)
        if r is not None:
            rows.append(r)
        if i % 20 == 0:
            print(f"  ...{i}/{len(combos)}", flush=True)

    df_all = pd.DataFrame(rows)

    # Eligibility: mean PF >= 1.2, min Sharpe across all (ticker,tf,fold) > -0.5
    elig = df_all[
        (df_all["mean_PF"] >= 1.2)
        & (df_all["min_Sh"] > -0.5)
        & (df_all["mean_DD"] >= -15.0)
    ].copy()

    df_all.to_csv(REPORTS / "global_sweep.csv", index=False)

    if elig.empty:
        print("No combo passed strict eligibility; relaxing.")
        elig = df_all[(df_all["mean_PF"] >= 1.0) & (df_all["mean_Sh"] > 0)].copy()

    elig = elig.sort_values("mean_Sh", ascending=False)
    top = elig.head(15)
    top.to_csv(REPORTS / "global_top.csv", index=False)

    print()
    print("=" * 140)
    print("GLOBAL TOP-15 (single param set across all 6 instruments)")
    print("=" * 140)
    cols = list(SEARCH_SPACE.keys()) + ["mean_Sh", "std_Sh", "min_Sh", "mean_PF", "mean_DD", "worst_DD", "mean_Ret", "n_trades"]
    print(top[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
