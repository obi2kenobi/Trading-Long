"""Walk-forward optimization on ATR multipliers.

Design:
  - Indicator signals are computed ONCE per (ticker, tf) using defaults.
    Only ATR multipliers (which are used inside the engine) vary per combo,
    so signals do not need to be recomputed per combo.
  - K anchored test windows of equal length, starting at 50% of the data
    (ensures every test window has a sane warmup of indicators).
  - For each combo: run engine on each test window; aggregate metrics.
  - Eligibility: mean PF >= 1.2, min(Sharpe across folds) > 0, mean DD >= -25%.
  - Best combo: highest mean Sharpe among eligible.

Output: per-(ticker, tf) best combo with mean/std/min metrics across folds.
"""
from __future__ import annotations
from itertools import product
from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.strategy import StrategyParams, compute_signals, StrategySignals
from src.backtest_engine import run_backtest
from src.metrics import compute_metrics


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS = Path(__file__).resolve().parent.parent / "reports"

SEARCH_SPACE = {
    "sl_atr_mult": [1.0, 1.5, 2.0, 2.5],
    "tp1_atr_mult": [1.0, 1.5, 2.0],
    "tp2_atr_mult": [2.5, 3.5, 5.0],
    "tp3_atr_mult": [4.5, 6.0, 8.0],
    "trailing_activation_atr_mult": [2.0, 3.0],
}

MIN_PF = 1.2
MAX_ABS_DD = 25.0


def _valid(c: dict) -> bool:
    return (c["tp1_atr_mult"] < c["tp2_atr_mult"] < c["tp3_atr_mult"]
            and c["sl_atr_mult"] <= c["trailing_activation_atr_mult"])


def _all_combos() -> list[dict]:
    keys = list(SEARCH_SPACE.keys())
    out = []
    for vals in product(*[SEARCH_SPACE[k] for k in keys]):
        c = dict(zip(keys, vals))
        if _valid(c):
            out.append(c)
    return out


def _make_params(combo: dict) -> StrategyParams:
    p = StrategyParams()
    p.use_atr_targets = True
    for k, v in combo.items():
        setattr(p, k, v)
    return p


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df[["open", "high", "low", "close", "volume"]].dropna()


def _slice_signals(sig: StrategySignals, mask) -> StrategySignals:
    """Return a new StrategySignals with all member series sliced by mask/index."""
    return StrategySignals(
        close=sig.close.loc[mask],
        high=sig.high.loc[mask],
        low=sig.low.loc[mask],
        open_=sig.open_.loc[mask],
        atr_in=sig.atr_in.loc[mask],
        long_ok=sig.long_ok.loc[mask],
        exit_signal=sig.exit_signal.loc[mask],
        base_conditions=sig.base_conditions.loc[mask],
        filters_ok=sig.filters_ok.loc[mask],
        htf_bear_block=sig.htf_bear_block.loc[mask],
        high_vol_block=sig.high_vol_block.loc[mask],
        is_lateral=sig.is_lateral.loc[mask],
        passed_filters=sig.passed_filters.loc[mask],
        active_filters=sig.active_filters.loc[mask],
    )


def _make_folds(n: int, n_folds: int, start_frac: float = 0.5):
    """Return list of (start_idx, end_idx) for each test window."""
    start = int(n * start_frac)
    span = n - start
    fold_len = span // n_folds
    folds = []
    for i in range(n_folds):
        s = start + i * fold_len
        e = s + fold_len if i < n_folds - 1 else n
        folds.append((s, e))
    return folds


def evaluate_combo_on_folds(df: pd.DataFrame, sig: StrategySignals, folds, combo: dict) -> dict:
    p = _make_params(combo)
    fold_metrics = []
    for s, e in folds:
        sub_df = df.iloc[s:e]
        sub_sig = _slice_signals(sig, sub_df.index)
        if len(sub_df) < 30:
            continue
        try:
            res = run_backtest(sub_df, sub_sig, p)
            m = compute_metrics(res)
        except Exception:
            continue
        # Replace inf PF with NaN so it doesn't dominate aggregation
        pf = m.profit_factor if np.isfinite(m.profit_factor) else np.nan
        fold_metrics.append({
            "Sharpe": m.sharpe, "PF": pf, "MaxDD": m.max_drawdown_pct,
            "Ret": m.total_return_pct, "Trades": m.n_trades, "WinR": m.win_rate_pct,
        })
    if not fold_metrics:
        return None
    fm = pd.DataFrame(fold_metrics)
    out = dict(combo)
    out["mean_Sharpe"] = float(fm["Sharpe"].mean())
    out["std_Sharpe"] = float(fm["Sharpe"].std())
    out["min_Sharpe"] = float(fm["Sharpe"].min())
    out["mean_PF"] = float(fm["PF"].mean(skipna=True))
    out["mean_DD"] = float(fm["MaxDD"].mean())
    out["worst_DD"] = float(fm["MaxDD"].min())
    out["mean_Ret"] = float(fm["Ret"].mean())
    out["mean_Trades"] = float(fm["Trades"].mean())
    out["mean_WinR"] = float(fm["WinR"].mean())
    out["n_folds"] = len(fold_metrics)
    return out


def optimize_walkforward(ticker: str, tf: str, n_folds: int) -> dict:
    df = load_csv(DATA_DIR / f"{ticker}_{tf}.csv")
    daily_df = load_csv(DATA_DIR / f"{ticker}_1d.csv") if tf != "1d" else df
    sig = compute_signals(df, StrategyParams(), daily_df=daily_df)

    n = len(df)
    folds = _make_folds(n, n_folds)
    print(f"  {ticker} {tf}: n={n} folds={n_folds} fold_lens={[e - s for s, e in folds]}")

    combos = _all_combos()
    rows = []
    for combo in combos:
        r = evaluate_combo_on_folds(df, sig, folds, combo)
        if r is not None:
            rows.append(r)
    df_all = pd.DataFrame(rows)

    # Eligibility
    elig = df_all[
        (df_all["mean_PF"] >= MIN_PF)
        & (df_all["min_Sharpe"] > 0.0)
        & (df_all["mean_DD"] >= -MAX_ABS_DD)
    ].copy()

    df_all.to_csv(REPORTS / f"wf_sweep_{ticker}_{tf}.csv", index=False)

    if elig.empty:
        # Fallback: relax min_Sharpe to mean_Sharpe > 0
        elig = df_all[(df_all["mean_PF"] >= 1.0) & (df_all["mean_Sharpe"] > 0)].copy()
        if elig.empty:
            print(f"    {ticker} {tf}: NO eligible (even with fallback)")
            return None

    elig = elig.sort_values("mean_Sharpe", ascending=False)
    top = elig.head(10).copy()
    top.to_csv(REPORTS / f"wf_top_{ticker}_{tf}.csv", index=False)

    best = top.iloc[0].to_dict()
    print(f"    BEST {ticker} {tf}: meanSh={best['mean_Sharpe']:.2f}±{best['std_Sharpe']:.2f} "
          f"minSh={best['min_Sharpe']:.2f} meanPF={best['mean_PF']:.2f} "
          f"meanDD={best['mean_DD']:.1f}% worstDD={best['worst_DD']:.1f}%  "
          f"sl={best['sl_atr_mult']} tp1/2/3={best['tp1_atr_mult']}/{best['tp2_atr_mult']}/{best['tp3_atr_mult']} trail@{best['trailing_activation_atr_mult']}")
    return best


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    summary = []
    for ticker in ["SPY", "QQQ", "IWM"]:
        for tf, k in [("240m", 3), ("1d", 5)]:
            best = optimize_walkforward(ticker, tf, k)
            if best is None:
                continue
            summary.append({
                "ticker": ticker, "tf": tf,
                "sl": best["sl_atr_mult"],
                "tp1": best["tp1_atr_mult"],
                "tp2": best["tp2_atr_mult"],
                "tp3": best["tp3_atr_mult"],
                "trail_arm": best["trailing_activation_atr_mult"],
                "mean_Sh": round(best["mean_Sharpe"], 2),
                "std_Sh": round(best["std_Sharpe"], 2),
                "min_Sh": round(best["min_Sharpe"], 2),
                "mean_PF": round(best["mean_PF"], 2),
                "mean_DD%": round(best["mean_DD"], 1),
                "worst_DD%": round(best["worst_DD"], 1),
                "mean_Ret%": round(best["mean_Ret"], 1),
                "mean_Trades": round(best["mean_Trades"], 1),
            })
    out = pd.DataFrame(summary)
    print()
    print("=" * 140)
    print("WALK-FORWARD BEST PARAMS")
    print("=" * 140)
    if not out.empty:
        print(out.to_string(index=False))
        out.to_csv(REPORTS / "wf_summary.csv", index=False)


if __name__ == "__main__":
    main()
