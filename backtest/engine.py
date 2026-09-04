"""Bar-by-bar backtest engine for Opening Range Breakout + Pivot Points.

Staged per the research docs' recommendation: `use_pivot_filter` and
`use_pivot_stop_target` are OFF by default, giving the plain ATR-buffered
ORB baseline. Turn them on only after the baseline clears its own go/no-go
gate -- stacking the pivot overlay onto a dead baseline just adds
overfitting risk for no reason.

Look-ahead discipline: the opening range is frozen exactly at window end;
pivots use only the fully-closed prior FX/trading day (see
common.indicators.daily_prior_hlc); breakout confirmation requires a
CLOSED bar's close beyond the trigger; fills execute at the next bar's
open.
"""
from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.costs import FrictionModel
from common.indicators import atr, standard_pivots, daily_prior_hlc


@dataclass
class ORBPivotParams:
    or_window_bars: int = 3          # 15 min of M5 bars
    anchor_hour_utc: int = 8         # ~London open
    k_buffer_atr: float = 0.10       # breakout confirmation buffer, x ATR
    atr_period: int = 14
    stop_atr_mult: float = 1.0       # floor on stop distance, x ATR
    target_atr_mult: float = 2.0     # plain-baseline fixed-R target (used when use_pivot_stop_target=False)
    day_boundary_hour_utc: int = 22  # ~17:00 ET FX day rollover, for pivot prior-day boundary
    max_trades_per_day: int = 2
    cutoff_hour_utc: int = 18        # no new entries after this UTC hour
    risk_pct: float = 0.005
    use_pivot_filter: bool = False       # bias filter: only trade with pivot-implied direction
    use_pivot_stop_target: bool = False  # stop = tighter-of(OR side, opposing pivot) floored by ATR; target = next pivot
    use_volume_filter: bool = False      # per research docs' Recommendation #5: trade only on abnormal opening volume
    volume_mult: float = 1.0             # today's OR-window volume must be >= this x the trailing average
    volume_lookback_days: int = 14
    # Selectivity: skip flat/rangebound openings whose OR is too narrow to
    # represent a real balance being established. 0.0 disables.
    min_or_range_atr: float = 0.0        # require (or_high - or_low) >= this x ATR


def prepare_signals(df: pd.DataFrame, p: ORBPivotParams) -> pd.DataFrame:
    out = df.copy()
    out["atr"] = atr(out, p.atr_period)

    prior = daily_prior_hlc(out, day_boundary_hour_utc=p.day_boundary_hour_utc)
    pivots = prior.apply(
        lambda row: standard_pivots(row["prior_high"], row["prior_low"], row["prior_close"])
        if row.notna().all() else pd.Series({k: np.nan for k in ["P", "R1", "R2", "R3", "S1", "S2", "S3"]}),
        axis=1, result_type="expand",
    )
    out = out.join(pivots)

    # Opening range: identify each day's anchor window and freeze OR_high/OR_low at window end.
    is_anchor_hour = out.index.hour == p.anchor_hour_utc
    day_key = out.index.floor("D")
    # bars_since_anchor_start: position within the OR window for anchor-hour bars, else NaN
    anchor_start_idx = out.index.to_series().where(is_anchor_hour).groupby(day_key).transform("first")
    minutes_since_anchor = (out.index.to_series() - anchor_start_idx).dt.total_seconds() / 60.0
    bar_minutes = (out.index.to_series().diff().dt.total_seconds() / 60.0).median()
    in_or_window = (minutes_since_anchor >= 0) & (minutes_since_anchor < p.or_window_bars * bar_minutes)

    or_high = out["high"].where(in_or_window).groupby(day_key).cummax()
    or_low = out["low"].where(in_or_window).groupby(day_key).cummin()
    # Freeze at the last value observed during the window, forward-filled for the rest of the day.
    or_high_frozen = or_high.groupby(day_key).ffill()
    or_low_frozen = or_low.groupby(day_key).ffill()
    out["or_high"] = or_high_frozen
    out["or_low"] = or_low_frozen
    out["or_window_closed"] = ~in_or_window & out["or_high"].notna()

    long_trigger = out["or_high"] + p.k_buffer_atr * out["atr"]
    short_trigger = out["or_low"] - p.k_buffer_atr * out["atr"]
    out["long_trigger"] = long_trigger
    out["short_trigger"] = short_trigger

    active_hours = (out.index.hour >= p.anchor_hour_utc) & (out.index.hour < p.cutoff_hour_utc)
    out["active"] = active_hours & out["or_window_closed"]

    # Abnormal opening-volume filter (research docs' Recommendation #5, the
    # single strongest documented ORB enhancement): today's OR-window volume
    # vs. the trailing average of PRIOR days' OR-window volume only (shift(1)
    # -- today never contributes to its own baseline, no look-ahead).
    daily_or_vol = out["volume"].where(in_or_window, 0.0).groupby(day_key).sum()
    trailing_avg_vol = daily_or_vol.rolling(p.volume_lookback_days, min_periods=3).mean().shift(1)
    out["or_volume_today"] = day_key.map(daily_or_vol)
    out["or_volume_trailing_avg"] = day_key.map(trailing_avg_vol)
    volume_ok = out["or_volume_today"] >= p.volume_mult * out["or_volume_trailing_avg"]

    long_signal = out["active"] & (out["close"] > long_trigger)
    short_signal = out["active"] & (out["close"] < short_trigger)
    if p.use_volume_filter:
        long_signal &= volume_ok.fillna(False)
        short_signal &= volume_ok.fillna(False)
    if p.min_or_range_atr > 0:
        or_wide_enough = (out["or_high"] - out["or_low"]) >= p.min_or_range_atr * out["atr"]
        long_signal &= or_wide_enough.fillna(False)
        short_signal &= or_wide_enough.fillna(False)
    if p.use_pivot_filter:
        long_signal &= out["close"] > out["P"]
        short_signal &= out["close"] < out["P"]

    out["long_signal"] = long_signal.fillna(False)
    out["short_signal"] = short_signal.fillna(False)
    return out


def run_backtest(df: pd.DataFrame, params: ORBPivotParams, symbol: str, starting_equity: float = 10_000.0) -> dict:
    sig = prepare_signals(df, params)
    friction = FrictionModel(symbol=symbol)

    equity = starting_equity
    position = None
    trades = []
    trades_today = 0
    current_day = None

    idx = sig.index
    for i in range(len(idx) - 1):
        row = sig.iloc[i]
        next_row = sig.iloc[i + 1]
        ts_next = idx[i + 1]

        day = idx[i].floor("D")
        if day != current_day:
            current_day = day
            trades_today = 0

        if position is not None:
            hit_stop = (position["side"] == 1 and next_row["low"] <= position["stop"]) or \
                       (position["side"] == -1 and next_row["high"] >= position["stop"])
            hit_target = (position["side"] == 1 and next_row["high"] >= position["target"]) or \
                         (position["side"] == -1 and next_row["low"] <= position["target"])
            if hit_stop or hit_target:
                # Conservative: assume stop fills first if both touched in one bar.
                level = position["stop"] if hit_stop else position["target"]
                # Exit crosses the spread against us too (this was missing before).
                exit_price = level - position["side"] * friction.half_spread(
                    ts_next, level, next_row.get("spread")
                )
                pnl = position["side"] * (exit_price - position["entry_price"]) * position["size"]
                pnl -= friction.commission(abs(position["size"] * exit_price))
                equity += pnl
                trades.append({
                    "entry_ts": position["entry_ts"], "exit_ts": ts_next,
                    "side": position["side"], "entry_price": position["entry_price"],
                    "exit_price": exit_price, "size": position["size"],
                    "pnl": pnl, "return": pnl / position["equity_at_entry"],
                    # Normalized edge: pnl per unit of capital actually risked.
                    "risk_amount": position["risk_amount"],
                    "r_multiple": pnl / position["risk_amount"] if position["risk_amount"] > 0 else np.nan,
                })
                position = None
            continue

        if trades_today >= params.max_trades_per_day:
            continue
        if not np.isfinite(row.get("atr", np.nan)) or row["atr"] <= 0:
            continue

        side = 1 if row["long_signal"] else (-1 if row["short_signal"] else 0)
        if side == 0:
            continue

        entry_price = friction.apply_fill(ts_next, next_row["open"], row["atr"], side,
                                          bar_spread=next_row.get("spread"))

        if params.use_pivot_stop_target and np.isfinite(row.get("S1", np.nan)) and np.isfinite(row.get("R1", np.nan)):
            if side == 1:
                candidate = min(row["or_low"], row["S1"])
                dist = entry_price - candidate
                stop = candidate if dist >= params.stop_atr_mult * row["atr"] else entry_price - params.stop_atr_mult * row["atr"]
                target = row["R1"]
            else:
                candidate = max(row["or_high"], row["R1"])
                dist = candidate - entry_price
                stop = candidate if dist >= params.stop_atr_mult * row["atr"] else entry_price + params.stop_atr_mult * row["atr"]
                target = row["S1"]
        else:
            stop = entry_price - side * params.stop_atr_mult * row["atr"]
            target = entry_price + side * params.target_atr_mult * row["atr"]

        risk_per_unit = abs(entry_price - stop)
        if risk_per_unit <= 0 or not np.isfinite(target):
            continue
        size = (params.risk_pct * equity) / risk_per_unit

        position = {
            "side": side, "entry_price": entry_price, "stop": stop, "target": target,
            "size": size, "entry_ts": ts_next, "equity_at_entry": equity,
            "risk_amount": params.risk_pct * equity,
        }
        trades_today += 1

    trades_df = pd.DataFrame(trades)
    return {"trades": trades_df, "final_equity": equity, "params": params.__dict__}
