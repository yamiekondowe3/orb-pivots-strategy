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

Per the plan's explicit go/no-go instruction ("if the plain ORB has no
positive out-of-sample expectancy after costs, do not proceed — pivots
will not rescue it"), and given the pivot filter check already ran and
made no material difference, **stopping here rather than running a full
walk-forward grid search** (which took ~44 minutes for VWAP+RSI and would
be a similar investment for a result this decisively negative). A WFO
pass is still a legitimate follow-up if the parameter space is
re-designed (tighter targets given the low win rate, and/or the
abnormal-volume filter), but re-tuning stop/target multiples on the
*current* rule shape is unlikely to close a 26%-vs-33%+ win-rate gap this
wide.

Full result JSON: `reports/xauusd_orb_pivots_real_data_results.json`.

## Not done yet

- Abnormal opening-volume filter (the research docs' single
  highest-value documented ORB enhancement — not yet implemented).
- Walk-forward optimization / Monte Carlo VaR on a re-designed parameter
  space.
- Replication to XAGUSD / USOIL / BTCUSD / ETHUSD.
- MQL5 EA Strategy Tester validation.
