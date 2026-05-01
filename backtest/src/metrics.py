"""Performance metrics for backtest results."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import math
import numpy as np
import pandas as pd

from .backtest_engine import BacktestResult, Trade


@dataclass
class Metrics:
    total_return_pct: float
    cagr_pct: float
    sharpe: float
    sortino: float
    max_drawdown_pct: float
    profit_factor: float
    win_rate_pct: float
    n_trades: int
    avg_trade_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    avg_bars_held: float
    longest_dd_bars: int
    final_equity: float

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def _bars_per_year(idx: pd.DatetimeIndex) -> float:
    if len(idx) < 2:
        return 252.0
    span = (idx[-1] - idx[0]).total_seconds()
    if span <= 0:
        return 252.0
    bars_per_sec = (len(idx) - 1) / span
    return bars_per_sec * 365.25 * 24 * 3600


def compute_metrics(result: BacktestResult) -> Metrics:
    eq = result.equity_curve
    rets = eq.pct_change().fillna(0.0)

    total_return = (result.final_equity / result.initial_capital - 1.0) * 100.0
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 24 * 3600)
    cagr = ((result.final_equity / result.initial_capital) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0

    bpy = _bars_per_year(eq.index)
    mu = rets.mean() * bpy
    sigma = rets.std() * math.sqrt(bpy)
    sharpe = mu / sigma if sigma > 0 else 0.0

    downside = rets[rets < 0].std() * math.sqrt(bpy)
    sortino = mu / downside if downside > 0 else 0.0

    # Drawdown
    peak = eq.cummax()
    dd = (eq - peak) / peak
    max_dd = dd.min() * 100.0  # negative
    # Longest drawdown duration (bars under water)
    in_dd = (eq < peak).astype(int)
    longest_dd = 0
    cur = 0
    for v in in_dd.values:
        if v:
            cur += 1
            longest_dd = max(longest_dd, cur)
        else:
            cur = 0

    # Trade-based metrics
    trades: List[Trade] = result.trades
    n = len(trades)
    if n == 0:
        return Metrics(
            total_return_pct=total_return, cagr_pct=cagr, sharpe=sharpe, sortino=sortino,
            max_drawdown_pct=max_dd, profit_factor=0.0, win_rate_pct=0.0,
            n_trades=0, avg_trade_pct=0.0, avg_win_pct=0.0, avg_loss_pct=0.0,
            avg_bars_held=0.0, longest_dd_bars=longest_dd, final_equity=result.final_equity,
        )

    pnls = np.array([t.pnl_perc for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    gross_profit = wins.sum() if len(wins) else 0.0
    gross_loss = -losses.sum() if len(losses) else 0.0
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)
    win_rate = (len(wins) / n) * 100.0
    avg_trade = float(pnls.mean())
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0
    avg_bars = float(np.mean([t.bars_held for t in trades]))

    return Metrics(
        total_return_pct=total_return, cagr_pct=cagr, sharpe=sharpe, sortino=sortino,
        max_drawdown_pct=max_dd, profit_factor=pf, win_rate_pct=win_rate,
        n_trades=n, avg_trade_pct=avg_trade, avg_win_pct=avg_win, avg_loss_pct=avg_loss,
        avg_bars_held=avg_bars, longest_dd_bars=longest_dd, final_equity=result.final_equity,
    )


def buy_and_hold_return(df: pd.DataFrame) -> float:
    return (df["close"].iloc[-1] / df["close"].iloc[0] - 1.0) * 100.0
