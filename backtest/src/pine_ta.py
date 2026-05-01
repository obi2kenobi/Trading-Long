"""Pine Script-equivalent technical analysis primitives.

Each function mirrors Pine's behavior exactly:
- ema: standard EMA, seeded with first value
- rma: Wilder's smoothing (used by rsi/atr/adx), seeded with SMA at index length-1
- supertrend: matches the Pine custom implementation in the .pine file
- wavetrend: matches the LazyBear / WT formulation used in the .pine file
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def ema(src: pd.Series, length: int) -> pd.Series:
    """Pine's ta.ema: alpha=2/(length+1), seeded with first non-NaN value."""
    alpha = 2.0 / (length + 1.0)
    return src.ewm(alpha=alpha, adjust=False).mean()


def sma(src: pd.Series, length: int) -> pd.Series:
    return src.rolling(length, min_periods=length).mean()


def rma(src: pd.Series, length: int) -> pd.Series:
    """Pine's ta.rma (Wilder's): alpha=1/length, seeded with SMA at index length-1."""
    out = pd.Series(np.nan, index=src.index, dtype="float64")
    if len(src) < length:
        return out
    seed = src.iloc[:length].mean()
    out.iloc[length - 1] = seed
    alpha = 1.0 / length
    prev = seed
    vals = src.values
    for i in range(length, len(src)):
        v = vals[i]
        if np.isnan(v):
            out.iloc[i] = prev
            continue
        prev = alpha * v + (1.0 - alpha) * prev
        out.iloc[i] = prev
    return out


def rsi(src: pd.Series, length: int) -> pd.Series:
    """Pine's ta.rsi using Wilder's smoothing on gains/losses."""
    delta = src.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    avg_up = rma(up, length)
    avg_down = rma(down, length)
    rs = avg_up / avg_down.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    out = out.where(avg_down != 0.0, 100.0)
    return out


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    return rma(true_range(high, low, close), length)


def dmi(high: pd.Series, low: pd.Series, close: pd.Series, di_len: int, adx_len: int):
    """Pine's ta.dmi(diLen, adxLen) -> (+DI, -DI, ADX)."""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)
    tr = true_range(high, low, close)
    sm_tr = rma(tr, di_len)
    plus_di = 100.0 * rma(plus_dm, di_len) / sm_tr
    minus_di = 100.0 * rma(minus_dm, di_len) / sm_tr
    sum_di = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / sum_di
    adx = rma(dx, adx_len)
    return plus_di, minus_di, adx


def highest(src: pd.Series, length: int) -> pd.Series:
    return src.rolling(length, min_periods=length).max()


def lowest(src: pd.Series, length: int) -> pd.Series:
    return src.rolling(length, min_periods=length).min()


def crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a.shift(1) >= b.shift(1)) & (a < b)


def tema(src: pd.Series, length: int) -> pd.Series:
    e1 = ema(src, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    return 3.0 * e1 - 3.0 * e2 + e3


def supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int,
    factor: float,
):
    """Replicates the Pine Supertrend from TEMA-ST-WT LONG OPT.pine.

    Returns (trend, up_band, down_band) where trend is +1 / -1 / 0 (initial).
    """
    hl2 = (high + low) / 2.0
    a = atr(high, low, close, period)
    upc = hl2 - factor * a
    dnc = hl2 + factor * a
    n = len(close)
    up = np.full(n, np.nan)
    dn = np.full(n, np.nan)
    trend = np.zeros(n, dtype=np.int8)
    cls = close.values
    upc_v = upc.values
    dnc_v = dnc.values
    for i in range(n):
        if i == 0 or np.isnan(upc_v[i]) or np.isnan(dnc_v[i]):
            up[i] = upc_v[i]
            dn[i] = dnc_v[i]
            trend[i] = 0
            continue
        prev_up = up[i - 1] if not np.isnan(up[i - 1]) else upc_v[i]
        prev_dn = dn[i - 1] if not np.isnan(dn[i - 1]) else dnc_v[i]
        prev_close = cls[i - 1]
        up[i] = max(upc_v[i], prev_up) if prev_close > prev_up else upc_v[i]
        dn[i] = min(dnc_v[i], prev_dn) if prev_close < prev_dn else dnc_v[i]
        if cls[i] > prev_dn:
            trend[i] = 1
        elif cls[i] < prev_up:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]
    return (
        pd.Series(trend, index=close.index, name="trend"),
        pd.Series(up, index=close.index, name="up"),
        pd.Series(dn, index=close.index, name="dn"),
    )


def wavetrend(high: pd.Series, low: pd.Series, close: pd.Series, n1: int, n2: int):
    """Returns (wt1, wt2) per the WaveTrend formulation in the Pine script."""
    hlc3 = (high + low + close) / 3.0
    esa = ema(hlc3, n1)
    d = ema((hlc3 - esa).abs(), n1)
    ci = (hlc3 - esa) / (0.015 * d.replace(0.0, np.nan))
    wt1 = ema(ci, n2)
    wt2 = sma(wt1, 4)
    return wt1, wt2
