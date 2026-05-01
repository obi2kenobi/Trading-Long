"""TEMA-ST-WT LONG v6.4 — Python port of the Pine strategy.

Computes all indicators and entry/exit signals as boolean / numeric Series
aligned to the input dataframe index. Position management (TP1/TP2/TP3, SL,
trailing, cooldown) lives in backtest_engine.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from . import pine_ta as ta


@dataclass
class StrategyParams:
    # Core indicators
    tema_len_in: int = 36
    tema_len_out: int = 38
    st_period_in: int = 10
    st_factor_in: float = 2.6
    st_period_out: int = 10
    st_factor_out: float = 3.4
    wt_n1_in: int = 10
    wt_n2_in: int = 15
    wt_n1_out: int = 10
    wt_n2_out: int = 21
    max_dist_atr: float = 2.2

    # Lateralità
    lateral_lookback: int = 10
    lateral_threshold: float = 0.015  # 1.5%
    flat_slope_ratio: float = 0.008

    # Filters
    use_advanced_filters: bool = True
    min_filters_required: int = 2
    enable_rsi: bool = True
    rsi_len: int = 14
    rsi_overbought: float = 75.0
    enable_volume: bool = True
    vol_ma_len: int = 20
    vol_multiplier: float = 1.0
    enable_adx: bool = True
    adx_len: int = 14
    adx_threshold: float = 20.0
    enable_gap: bool = True
    gap_threshold: float = 0.008  # 0.8%

    # Hard blocks
    enable_htf_bear_block: bool = True
    htf_ema_len: int = 21
    enable_high_vol_block: bool = True

    # Volatility regime
    atr_ma_len: int = 50
    high_vol_multiplier: float = 1.5
    low_vol_threshold: float = 0.7

    # Risk
    slippage_perc: float = 0.0005  # 0.05%
    use_fixed_sl: bool = True
    fixed_sl_perc: float = 0.015
    use_atr_sl: bool = False
    atr_sl_multiplier: float = 1.5

    enable_cooldown: bool = True
    cooldown_bars: int = 5

    enable_trailing: bool = True
    trailing_activation_perc: float = 0.025
    trailing_offset_perc: float = 0.005

    use_take_profit: bool = True
    tp1_perc: float = 0.025
    tp1_qty: float = 30.0  # % of position
    tp2_perc: float = 0.05
    tp2_qty: float = 30.0
    tp3_perc: float = 0.08

    # Commission (one-way), as fraction
    commission_perc: float = 0.0001  # 0.01%


@dataclass
class StrategySignals:
    """All series the engine needs, aligned to the trading dataframe index."""
    # Reference for prices — engine uses these for entry/SL/TP fills
    close: pd.Series
    high: pd.Series
    low: pd.Series
    open_: pd.Series
    atr_in: pd.Series  # for ATR-based SL

    # Entry
    long_ok: pd.Series  # bool: all conditions met for new long
    # Exit
    exit_signal: pd.Series  # bool: 3/3 exit signals confirmed

    # Diagnostics for reporting
    base_conditions: pd.Series
    filters_ok: pd.Series
    htf_bear_block: pd.Series
    high_vol_block: pd.Series
    is_lateral: pd.Series
    passed_filters: pd.Series
    active_filters: pd.Series


def _align_daily_to_intraday(daily: pd.DataFrame, intra_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Replicate Pine's request.security default (no lookahead): for each intraday
    bar, the daily value used is the most recent CLOSED daily bar's value.

    Daily index is assumed naive (date-only). Intraday index can be tz-aware.
    """
    daily = daily.copy()
    if daily.index.tz is not None:
        daily.index = daily.index.tz_localize(None)
    # Shift one day forward: the daily bar of date D is only "closed" once D ends,
    # so it's available from D+1 onwards.
    daily.index = daily.index + pd.Timedelta(days=1)
    intra_naive = intra_index.tz_convert(None) if intra_index.tz is not None else intra_index
    aligned = daily.reindex(intra_naive, method="ffill")
    aligned.index = intra_index
    return aligned


def compute_signals(df: pd.DataFrame, p: StrategyParams, daily_df: pd.DataFrame | None = None) -> StrategySignals:
    """df: OHLCV at trading TF. daily_df: OHLCV at daily TF for HTF filter (may be None).

    If df is already daily, daily_df can be the same df (HTF filter becomes self-referential
    on the daily timeframe, matching what Pine would do running on a daily chart).
    """
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    # Core indicators
    tema_in = ta.tema(c, p.tema_len_in)
    tema_out = ta.tema(c, p.tema_len_out)
    atr10 = ta.atr(h, l, c, p.st_period_in)  # st_period_out is the same (10)
    atr14 = ta.atr(h, l, c, 14)

    trend_in, up_in, dn_in = ta.supertrend(h, l, c, p.st_period_in, p.st_factor_in)
    trend_out, _, _ = ta.supertrend(h, l, c, p.st_period_out, p.st_factor_out)

    wt1_in, wt2_in = ta.wavetrend(h, l, c, p.wt_n1_in, p.wt_n2_in)
    wt1_out, wt2_out = ta.wavetrend(h, l, c, p.wt_n1_out, p.wt_n2_out)
    wt_up = wt1_in > wt2_in
    wt_down = ta.crossunder(wt1_out, wt2_out)

    dist_atr = (c - tema_in) / atr10

    # Filters
    rsi = ta.rsi(c, p.rsi_len)
    rsi_ok = rsi < p.rsi_overbought

    vol_ma = ta.sma(v, p.vol_ma_len)
    volume_ok = v > vol_ma * p.vol_multiplier

    _, _, adx = ta.dmi(h, l, c, p.adx_len, p.adx_len)
    trend_strong = adx > p.adx_threshold

    gap = (o - c.shift(1)).abs()
    gap_size = gap / c.shift(1)
    has_gap = gap_size > p.gap_threshold

    # Volatility regime
    atr_ma = ta.sma(atr14, p.atr_ma_len)
    vol_regime = atr14 / atr_ma
    is_high_vol = vol_regime > p.high_vol_multiplier
    is_low_vol = vol_regime < p.low_vol_threshold

    # HTF Bear filter (Daily EMA)
    if daily_df is not None and daily_df is not df:
        daily_close = daily_df["close"]
        daily_ema = ta.ema(daily_close, p.htf_ema_len)
        aligned = _align_daily_to_intraday(
            pd.DataFrame({"close_d": daily_close, "ema_d": daily_ema}),
            df.index,
        )
        htf_bearish = aligned["close_d"] < aligned["ema_d"]
    else:
        # daily backtest: HTF Daily filter compares close to its own EMA(21)
        htf_bearish = c < ta.ema(c, p.htf_ema_len)

    htf_bear_block = p.enable_htf_bear_block & htf_bearish.fillna(False)
    high_vol_block = p.enable_high_vol_block & is_high_vol.fillna(False)

    # Lateralità
    tema_slope = tema_in - tema_in.shift(1)
    slope_ratio = tema_slope.abs() / atr10
    is_flat = slope_ratio < p.flat_slope_ratio
    range_high = ta.highest(h, p.lateral_lookback)
    range_low = ta.lowest(l, p.lateral_lookback)
    range_pct = (range_high - range_low) / c
    range_cond = range_pct < p.lateral_threshold
    is_lateral = is_flat | range_cond

    # Base conditions (hard requirements + hard blocks)
    base_conditions = (
        (trend_in == 1)
        & wt_up.fillna(False)
        & (dist_atr <= p.max_dist_atr)
        & ~is_lateral.fillna(False)
        & ~htf_bear_block
        & ~high_vol_block
    )

    # Filter scoring
    rsi_pass = (rsi_ok.fillna(False)).astype(int) * (1 if p.enable_rsi else 0)
    vol_pass = (volume_ok.fillna(False)).astype(int) * (1 if p.enable_volume else 0)
    adx_pass = (trend_strong.fillna(False)).astype(int) * (1 if p.enable_adx else 0)
    gap_pass = (~has_gap.fillna(False)).astype(int) * (1 if p.enable_gap else 0)

    active_count = int(p.enable_rsi) + int(p.enable_volume) + int(p.enable_adx) + int(p.enable_gap)
    passed = rsi_pass + vol_pass + adx_pass + gap_pass
    eff_min = min(p.min_filters_required, active_count)

    if not p.use_advanced_filters or active_count == 0:
        filters_ok = pd.Series(True, index=df.index)
    else:
        filters_ok = passed >= eff_min

    long_ok = base_conditions & filters_ok

    # Exit signal: ALL 3 confirmed (>= 3 of 3)
    exit_wt = wt_down.fillna(False)
    exit_st = trend_out == -1
    exit_tema = c < tema_out
    exit_count = exit_wt.astype(int) + exit_st.astype(int) + exit_tema.astype(int)
    exit_signal = exit_count >= 3

    return StrategySignals(
        close=c,
        high=h,
        low=l,
        open_=o,
        atr_in=atr10,
        long_ok=long_ok.fillna(False),
        exit_signal=exit_signal.fillna(False),
        base_conditions=base_conditions.fillna(False),
        filters_ok=filters_ok.fillna(False),
        htf_bear_block=htf_bear_block,
        high_vol_block=high_vol_block,
        is_lateral=is_lateral.fillna(False),
        passed_filters=passed,
        active_filters=pd.Series(active_count, index=df.index),
    )
