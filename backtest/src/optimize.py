"""Grid-search optimization on ATR multipliers, train/test split per (ticker, tf).

For each (ticker, tf):
  1. Split data 70/30 chronologically (train, test)
  2. Run all combos on train
  3. Filter: PF>=1.2, n_trades>=10, MaxDD>=-25 (configurable)
  4. Pick best by Sharpe on train
  5. Validate winner on test set
  6. Report both train and test metrics
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import sys
from typing import List
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.strategy import StrategyParams, compute_signals
from src.backtest_engine import run_backtest
from src.metrics import compute_metrics, buy_and_hold_return


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS = Path(__file__).resolve().parent.parent / "reports"


SEARCH_SPACE = {
    "sl_atr_mult": [1.0, 1.5, 2.0, 2.5],
    "tp1_atr_mult": [1.0, 1.5, 2.0],
    "tp2_atr_mult": [2.5, 3.5, 5.0],
    "tp3_atr_mult": [4.5, 6.0, 8.0],
    "trailing_activation_atr_mult": [2.0, 3.0],
}

# Eligibility filters (applied to train metrics)
MIN_PF = 1.2
MIN_TRADES = 10
MAX_ABS_DD = 25.0  # percent


def _valid_combo(c: dict) -> bool:
    return (c["tp1_atr_mult"] < c["tp2_atr_mult"] < c["tp3_atr_mult"]
            and c["sl_atr_mult"] <= c["trailing_activation_atr_mult"])


def _all_combos() -> list[dict]:
    keys = list(SEARCH_SPACE.keys())
    out = []
    for vals in product(*[SEARCH_SPACE[k] for k in keys]):
        c = dict(zip(keys, vals))
        if _valid_combo(c):
            out.append(c)
    return out


def _make_params(combo: dict) -> StrategyParams:
    p = StrategyParams()
    p.use_atr_targets = True
    for k, v in combo.items():
        setattr(p, k, v)
    return p


def _evaluate(df: pd.DataFrame, daily_df: pd.DataFrame, params: StrategyParams) -> dict:
    sig = compute_signals(df, params, daily_df=daily_df)
    res = run_backtest(df, sig, params)
    m = compute_metrics(res)
    return {
        "n_trades": m.n_trades,
        "winrate": m.win_rate_pct,
        "PF": m.profit_factor,
        "total_ret": m.total_return_pct,
        "CAGR": m.cagr_pct,
        "Sharpe": m.sharpe,
        "Sortino": m.sortino,
        "MaxDD": m.max_drawdown_pct,
        "avg_bars": m.avg_bars_held,
    }


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df[["open", "high", "low", "close", "volume"]].dropna()


def split_train_test(df: pd.DataFrame, train_frac: float = 0.7):
    n = len(df)
    cut = int(n * train_frac)
    return df.iloc[:cut], df.iloc[cut:]


def optimize_one(ticker: str, tf: str, top_n: int = 5) -> dict:
    df = load_csv(DATA_DIR / f"{ticker}_{tf}.csv")
    daily_df = load_csv(DATA_DIR / f"{ticker}_1d.csv") if tf != "1d" else df
    train, test = split_train_test(df)
    train_end = train.index[-1]
    if daily_df.index.tz is None and train_end.tzinfo is not None:
        train_end_naive = train_end.tz_convert(None)
    else:
        train_end_naive = train_end
    daily_train = daily_df.loc[:train_end_naive]
    daily_test = daily_df  # full history; alignment is no-look-ahead

    combos = _all_combos()
    print(f"  {ticker} {tf}: {len(combos)} combos, train rows={len(train)} test rows={len(test)}")

    rows = []
    for combo in combos:
        params = _make_params(combo)
        try:
            tr = _evaluate(train, daily_train, params)
        except Exception as e:
            continue
        row = dict(combo)
        row.update({f"tr_{k}": v for k, v in tr.items()})
        rows.append(row)

    df_combos = pd.DataFrame(rows)

    # Eligibility filter on train
    eligible = df_combos[
        (df_combos["tr_PF"] >= MIN_PF)
        & (df_combos["tr_n_trades"] >= MIN_TRADES)
        & (df_combos["tr_MaxDD"] >= -MAX_ABS_DD)
    ].copy()

    if eligible.empty:
        print(f"    {ticker} {tf}: NO eligible combo (PF>={MIN_PF}, trades>={MIN_TRADES}, DD>=-{MAX_ABS_DD}%)")
        return None

    eligible = eligible.sort_values("tr_Sharpe", ascending=False)
    top = eligible.head(top_n).copy()

    # Validate top-N on test set
    test_metrics_list = []
    for _, row in top.iterrows():
        combo = {k: row[k] for k in SEARCH_SPACE.keys()}
        params = _make_params(combo)
        ts = _evaluate(test, daily_test, params)
        test_metrics_list.append(ts)
    top_with_test = top.reset_index(drop=True)
    for k in test_metrics_list[0].keys():
        top_with_test[f"te_{k}"] = [m[k] for m in test_metrics_list]

    # Save full sweep + top-N
    df_combos.to_csv(REPORTS / f"sweep_{ticker}_{tf}.csv", index=False)
    top_with_test.to_csv(REPORTS / f"top_{ticker}_{tf}.csv", index=False)

    best = top_with_test.iloc[0].to_dict()
    print(f"    BEST {ticker} {tf}: tr_Sharpe={best['tr_Sharpe']:.2f} te_Sharpe={best['te_Sharpe']:.2f} "
          f"tr_PF={best['tr_PF']:.2f} te_PF={best['te_PF']:.2f} "
          f"tr_DD={best['tr_MaxDD']:.1f}% te_DD={best['te_MaxDD']:.1f}%")
    return best


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    summary = []
    for ticker in ["SPY", "QQQ", "IWM"]:
        for tf in ["240m", "1d"]:
            best = optimize_one(ticker, tf)
            if best is None:
                continue
            summary.append({
                "ticker": ticker, "tf": tf,
                **{k: best[k] for k in SEARCH_SPACE.keys()},
                "tr_Sharpe": round(best["tr_Sharpe"], 2),
                "te_Sharpe": round(best["te_Sharpe"], 2),
                "tr_PF": round(best["tr_PF"], 2),
                "te_PF": round(best["te_PF"], 2),
                "tr_ret%": round(best["tr_total_ret"], 1),
                "te_ret%": round(best["te_total_ret"], 1),
                "tr_DD%": round(best["tr_MaxDD"], 1),
                "te_DD%": round(best["te_MaxDD"], 1),
                "tr_trades": int(best["tr_n_trades"]),
                "te_trades": int(best["te_n_trades"]),
            })
    summary_df = pd.DataFrame(summary)
    print()
    print("=" * 130)
    print("BEST PARAMS PER (ticker, tf) — train/test 70/30")
    print("=" * 130)
    if not summary_df.empty:
        print(summary_df.to_string(index=False))
        summary_df.to_csv(REPORTS / "optimization_summary.csv", index=False)


if __name__ == "__main__":
    main()
