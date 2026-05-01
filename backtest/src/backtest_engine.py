"""Bar-by-bar backtest engine for the TEMA-ST-WT LONG strategy.

Execution model (matches Pine default behavior):
  - Signal long_ok evaluated at close of bar i
  - Entry fills at OPEN of bar i+1 (with slippage)
  - SL/TP exit orders become active starting bar i+2 (entry_bar+1 in code)
  - SL priority over TP when both touched in same bar (conservative worst-case)
  - exit_signal at close of bar i fills at OPEN of bar i+1

TP partial exits (matches Pine qty_percent semantics: % of CURRENT position):
  - TP1: 30% of position remaining
  - TP2: 30% of position remaining (after TP1)
  - TP3: 100% of position remaining (after TP2)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import numpy as np
import pandas as pd

from .strategy import StrategyParams, StrategySignals


@dataclass
class TradeFill:
    timestamp: pd.Timestamp
    kind: str
    price: float
    qty: float
    cash_delta: float


@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    initial_qty: float
    fills: List[TradeFill] = field(default_factory=list)
    exit_time: pd.Timestamp | None = None
    pnl_abs: float = 0.0
    pnl_perc: float = 0.0
    bars_held: int = 0
    exit_reason: str = ""
    was_loss: bool = False


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity_curve: pd.Series
    fills: List[TradeFill]
    initial_capital: float
    final_equity: float


def _commission(notional: float, rate: float) -> float:
    return abs(notional) * rate


def _compute_sl(entry_price: float, atr_val: float, p: StrategyParams) -> float:
    if p.use_fixed_sl:
        return entry_price * (1.0 - p.fixed_sl_perc - p.slippage_perc)
    if p.use_atr_sl:
        return entry_price - atr_val * p.atr_sl_multiplier
    return entry_price * (1.0 - p.fixed_sl_perc - p.slippage_perc)


def _finalize(trade: Trade, bars_held: int) -> None:
    invested = sum(f.cash_delta for f in trade.fills if f.kind == "ENTRY")  # negative
    realized = sum(f.cash_delta for f in trade.fills if f.kind != "ENTRY")
    trade.pnl_abs = realized + invested
    trade.pnl_perc = (trade.pnl_abs / -invested) * 100.0 if invested != 0 else 0.0
    trade.bars_held = bars_held


def run_backtest(
    df: pd.DataFrame,
    sig: StrategySignals,
    p: StrategyParams,
    initial_capital: float = 100_000.0,
) -> BacktestResult:
    n = len(df)
    if n < 2:
        raise ValueError("dataframe too short")

    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    idx = df.index

    long_ok = sig.long_ok.values
    exit_signal = sig.exit_signal.values
    atr_in = sig.atr_in.values

    cash = initial_capital
    qty = 0.0
    entry_price = 0.0
    entry_bar = -1
    tp1_done = False
    tp2_done = False
    trailing_activated = False
    last_exit_bar = -10**9
    last_exit_was_loss = False

    pending_entry = False
    pending_exit_signal = False

    trades: List[Trade] = []
    fills: List[TradeFill] = []
    cur: Trade | None = None
    equity = np.full(n, initial_capital, dtype=float)

    def cooldown_active(i: int) -> bool:
        if not p.enable_cooldown or not last_exit_was_loss:
            return False
        return (i - last_exit_bar) < p.cooldown_bars

    for i in range(n):
        # ── 1) OPEN of bar i: pending entry / pending signal-exit fills ────────
        if pending_entry and qty <= 1e-9:
            fill_price = o[i] * (1.0 + p.slippage_perc)
            buy_notional = cash
            commission = _commission(buy_notional, p.commission_perc)
            buy_qty = (cash - commission) / fill_price
            cash = cash - buy_qty * fill_price - commission
            qty = buy_qty
            entry_price = fill_price
            entry_bar = i
            tp1_done = False
            tp2_done = False
            trailing_activated = False
            cur = Trade(entry_time=idx[i], entry_price=fill_price, initial_qty=qty)
            f = TradeFill(idx[i], "ENTRY", fill_price, qty, -(qty * fill_price + commission))
            fills.append(f); cur.fills.append(f)
        pending_entry = False

        if pending_exit_signal and qty > 1e-9:
            fill_price = o[i] * (1.0 - p.slippage_perc)
            sell_notional = qty * fill_price
            commission = _commission(sell_notional, p.commission_perc)
            cash += sell_notional - commission
            f = TradeFill(idx[i], "EXIT_SIG", fill_price, qty, sell_notional - commission)
            fills.append(f)
            if cur is not None:
                cur.fills.append(f)
                cur.exit_time = idx[i]
                cur.exit_reason = "EXIT_SIG"
                cur.was_loss = fill_price < entry_price
                _finalize(cur, i - entry_bar)
                trades.append(cur); cur = None
            last_exit_bar = i
            last_exit_was_loss = fill_price < entry_price
            qty = 0.0
        pending_exit_signal = False

        # ── 2) Intra-bar SL/TP (only from entry_bar+1 onward) ─────────────────
        if qty > 1e-9 and i > entry_bar:
            atr_val = atr_in[i] if not np.isnan(atr_in[i]) else 0.0
            sl_price = _compute_sl(entry_price, atr_val, p)
            if trailing_activated:
                sl_price = entry_price * (1.0 + p.trailing_offset_perc)

            tp1 = entry_price * (1.0 + p.tp1_perc) if p.use_take_profit else np.inf
            tp2 = entry_price * (1.0 + p.tp2_perc) if p.use_take_profit else np.inf
            tp3 = entry_price * (1.0 + p.tp3_perc) if p.use_take_profit else np.inf

            bar_open, bar_high, bar_low = o[i], h[i], l[i]
            sl_triggered = False

            # Gap-down through SL → fill at open
            if bar_open <= sl_price:
                fill_price = bar_open
                sell_notional = qty * fill_price
                commission = _commission(sell_notional, p.commission_perc)
                cash += sell_notional - commission
                f = TradeFill(idx[i], "SL_GAP", fill_price, qty, sell_notional - commission)
                fills.append(f)
                if cur is not None:
                    cur.fills.append(f); cur.exit_time = idx[i]
                    cur.exit_reason = "SL_GAP"; cur.was_loss = fill_price < entry_price
                    _finalize(cur, i - entry_bar); trades.append(cur); cur = None
                last_exit_bar = i; last_exit_was_loss = fill_price < entry_price
                qty = 0.0
                sl_triggered = True

            elif bar_low <= sl_price:
                fill_price = sl_price
                sell_notional = qty * fill_price
                commission = _commission(sell_notional, p.commission_perc)
                cash += sell_notional - commission
                f = TradeFill(idx[i], "SL", fill_price, qty, sell_notional - commission)
                fills.append(f)
                if cur is not None:
                    cur.fills.append(f); cur.exit_time = idx[i]
                    cur.exit_reason = "SL"; cur.was_loss = fill_price < entry_price
                    _finalize(cur, i - entry_bar); trades.append(cur); cur = None
                last_exit_bar = i; last_exit_was_loss = fill_price < entry_price
                qty = 0.0
                sl_triggered = True

            # TPs (only if SL didn't fire this bar)
            if not sl_triggered and qty > 1e-9 and p.use_take_profit:
                if (not tp1_done) and bar_high >= tp1:
                    partial = qty * 0.30
                    sell_notional = partial * tp1
                    commission = _commission(sell_notional, p.commission_perc)
                    cash += sell_notional - commission
                    qty -= partial
                    tp1_done = True
                    f = TradeFill(idx[i], "TP1", tp1, partial, sell_notional - commission)
                    fills.append(f)
                    if cur is not None: cur.fills.append(f)

                if tp1_done and (not tp2_done) and bar_high >= tp2:
                    partial = qty * 0.30
                    sell_notional = partial * tp2
                    commission = _commission(sell_notional, p.commission_perc)
                    cash += sell_notional - commission
                    qty -= partial
                    tp2_done = True
                    f = TradeFill(idx[i], "TP2", tp2, partial, sell_notional - commission)
                    fills.append(f)
                    if cur is not None: cur.fills.append(f)

                if tp2_done and bar_high >= tp3 and qty > 1e-9:
                    sell_notional = qty * tp3
                    commission = _commission(sell_notional, p.commission_perc)
                    cash += sell_notional - commission
                    f = TradeFill(idx[i], "TP3", tp3, qty, sell_notional - commission)
                    fills.append(f)
                    if cur is not None:
                        cur.fills.append(f); cur.exit_time = idx[i]
                        cur.exit_reason = "TP3"; cur.was_loss = False
                        _finalize(cur, i - entry_bar); trades.append(cur); cur = None
                    last_exit_bar = i; last_exit_was_loss = False
                    qty = 0.0

        # ── 3) End-of-bar: trailing arm + queue entry/exit for next bar ───────
        if qty > 1e-9:
            current_profit = (c[i] - entry_price) / entry_price
            if p.enable_trailing and current_profit >= p.trailing_activation_perc:
                trailing_activated = True
            if exit_signal[i]:
                pending_exit_signal = True
        else:
            if long_ok[i] and not cooldown_active(i):
                pending_entry = True

        equity[i] = cash + qty * c[i]

    eq = pd.Series(equity, index=idx, name="equity")
    return BacktestResult(
        trades=trades,
        equity_curve=eq,
        fills=fills,
        initial_capital=initial_capital,
        final_equity=float(eq.iloc[-1]),
    )
