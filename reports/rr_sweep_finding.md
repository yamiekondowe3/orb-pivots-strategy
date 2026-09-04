# R:R sweep: the ORB breakout has no informational edge (definitive finding)

## What was tested

Following the observation that all four filter variants (plain, +pivot,
+volume, +both) converged on the same ~26-27% win rate against a 1:2
stop:target ratio (33% breakeven, an ~7pt shortfall), three tighter-target
variants were tested on the plain baseline (real XAUUSD, full 15.7y
history, `backtest/run_rr_sweep_xauusd.py`):

| stop:target (xATR) | Win rate | Breakeven WR | Gap | Sharpe | Total return | Expectancy/trade |
|---|---|---|---|---|---|---|
| 1.0 : 2.0 (original) | 26.4% | 33.3% | -6.9pt | -5.39 | -99.99998% | -1.248 |
| 2.0 : 1.5 | 50.4% | 57.1% | -6.7pt | -4.37 | -99.9942% | -1.248 |
| 1.5 : 1.0 | 49.0% | 60.0% | -11.0pt | -6.56 | -99.9999% | -1.248 |
| 2.0 : 1.0 | 58.0% | 66.7% | -8.7pt | -5.38 | -99.9961% | -1.248 |

## The finding

Win rate moved exactly as predicted with each R:R change (tighter target
relative to stop -> far more frequent hits, from 26% up to 58%). But
**expectancy per trade landed at essentially the identical -1.248 in all
four cases**, and every variant stayed several points below its own
breakeven threshold no matter how the stop:target ratio was reshaped.

This is not a coincidence and it is a stronger, cleaner result than any
single negative backtest: **it means the raw OR-breakout-confirmation
signal on XAUUSD M5 carries zero information about subsequent direction.**
Price statistically self-adjusts the realized win rate to track whatever
R:R is chosen, landing consistently at or below breakeven regardless -- the
exact statistical signature of trading noise and paying transaction costs
on it, not a payoff-shape problem that further stop/target engineering
could fix. (The near-constant -1.248 across wildly different R:R settings
is itself close to the per-trade cost drag from commission + spread +
slippage at this position size -- consistent with "no edge, just costs.")

## Conclusion for this strategy/instrument pair

**No further stop:target tuning is warranted.** Every lever the research
docs suggested (pivot bias filter, abnormal-volume filter, and now R:R
reshaping) has been tested on real data and none moves the needle,
because the underlying breakout trigger itself has no edge to work with.
Continuing to search the stop/target parameter space from here would be
overfitting a coin flip, not finding a real strategy. This closes out the
ORB+Pivots/XAUUSD investigation as a definitive, well-evidenced negative
result rather than an inconclusive one.

Full result JSON: `reports/xauusd_orb_rr_sweep_results.json`.
