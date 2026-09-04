# Data coverage status

Same MT5 connection, symbol map, and cached data as `vwap-rsi-strategy`
(see its `reports/data_coverage.md` for the full story) — real M5 OHLCV for
all 5 assets at `../data_cache/`. XAUUSD/XAGUSD ~15.7y, BTCUSD ~15.4y,
ETHUSD ~11.1y, USOIL only ~2.6y (broker symbol `US Oil`).

## Real-data ORB+Pivots result on XAUUSD (go/no-go check)

Full achieved history (2011-01-02 to 2026-09-03, 1,094,283 M5 bars), real
friction model, default parameters (`or_window_bars=3` i.e. 15min, anchor
08:00 UTC ~London open, `k_buffer_atr=0.10`, `stop_atr_mult=1.0`,
`target_atr_mult=2.0`, max 2 trades/day):

| | Plain baseline (no pivots) | + Pivot bias filter |
|---|---|---|
| Trades | 8,015 | 7,759 |
| Total return | -99.99998% | -99.99997% |
| Sharpe | -5.39 | -5.33 |
| Win rate | 26.4% | 26.3% |
| Profit factor | 0.61 | 0.61 |
| Monte Carlo ruin probability (5,000 iter) | 100% | 100% |

**Verdict: catastrophic FAIL, worse than VWAP+RSI's result on the same
instrument.** Both variants wipe out the account (fixed-fractional
position sizing compounding a persistently negative-expectancy sequence
over 8,000 trades). The pivot bias filter changed almost nothing (~3%
fewer trades, same performance profile) — a direct confirmation of the
research docs' warning that fusing two weak edges mostly adds
overfitting risk rather than rescuing either one.

**Root cause (mechanical, not just bad luck):** win rate (~26%) sits well
below the ~33% breakeven implied by the 1:2 stop:target ratio
(`stop_atr_mult=1.0` / `target_atr_mult=2.0`). The 15-min opening range +
0.10xATR breakout confirmation is producing far more false breakouts than
genuine follow-through on this instrument at this timeframe — consistent
with the research docs' finding that the plain ORB is a weak signal on its
own (the documented strongest ORB enhancement, an abnormal-opening-volume
filter, was NOT implemented here and remains the most promising untested
lever per the docs' Recommendation #5).

## Follow-up: abnormal opening-volume filter (research docs' Recommendation #5)

Implemented (`use_volume_filter` in `ORBPivotParams`; today's OR-window
volume must be >= `volume_mult` x the trailing `volume_lookback_days`-day
average of PRIOR days' OR volume, `shift(1)`'d so today never contributes
to its own baseline) and tested on the same full real XAUUSD history,
`volume_mult=1.0`, `volume_lookback_days=14`:

| | + Volume filter | + Volume filter + pivot filter |
|---|---|---|
| Trades | 5,517 | 5,335 |
| Total return | -99.9994% | -99.9989% |
| Sharpe | -5.14 | -5.04 |
| Win rate | 26.7% | 26.7% |
| Monte Carlo ruin probability | 100% | 100% |

**All four variants tested (plain, +pivot filter, +volume filter,
+both) converge on the same ~26-27% win rate**, regardless of which
signal-quality filter is applied. This is now a well-established
structural finding, not noise from one run: **the problem is the
stop:target ratio (1.0:2.0 ATR, needing ~33% win rate to break even), not
signal quality.** No combination of entry filters can fix a payoff
structure whose realized win rate sits consistently ~6-7 points below its
own breakeven threshold — filters change WHICH breakouts get traded, not
the ATR-multiple payoff shape that determines the breakeven bar itself.

**Stopping the filter-search here per the plan's overfitting warning.**
The one lever that could plausibly help is re-designing the payoff shape
itself (e.g. a larger `target_atr_mult`, which lowers the required
breakeven win rate below the ~26% actually observed) — but that is a
parameter-tuning search over the exact thing this project's go/no-go gate
exists to guard against chasing without an out-of-sample check. If pursued,
it should go through the same real walk-forward grid-search discipline
used for `vwap-rsi-strategy` (`backtest/run_wfo_xauusd.py` there is the
template), not a hand-picked multiplier evaluated once on the full
history.

Full result JSONs: `reports/xauusd_orb_pivots_real_data_results.json`,
`reports/xauusd_orb_volume_filter_results.json`.

## Not done yet

- Walk-forward optimization over the stop:target ATR-multiple space (the
  one remaining plausible lever, per the analysis above) — not run this
  session; would need the same WFO discipline as `vwap-rsi-strategy`.
- Replication to XAGUSD / USOIL / BTCUSD / ETHUSD.
- MQL5 EA Strategy Tester validation (the EA now mirrors the volume filter
  too, but is untested in the Strategy Tester).
