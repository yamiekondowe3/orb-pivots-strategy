# orb-pivots-strategy

Opening Range Breakout + Daily/Weekly Pivot Points strategy. Companion repo
to `vwap-rsi-strategy`, sharing the same `common/` friction model, metrics,
Monte Carlo, and walk-forward-optimization harness.

## Real-data result (headline finding): catastrophic FAIL

Seven variants tested on the full 15.7-year real XAUUSD history
(1,094,283 M5 bars, connected MT5 demo account): plain baseline, +pivot
bias filter, +abnormal-volume filter (the research docs' highest-value
documented ORB enhancement), +both, and three tighter-target R:R
reshapes (2:1.5, 1.5:1, 2:1). **All seven wipe out the account** (100%
Monte Carlo ruin probability every time). The R:R sweep is the
decisive result: win rate moved exactly as predicted with each R:R change
(26% up to 58%), but **expectancy per trade landed at the identical
-1.248 in all four R:R settings tested** — meaning the raw breakout
signal has zero information content; price statistically self-adjusts the
win rate to track the R:R chosen, landing at/below breakeven regardless.
See `reports/rr_sweep_finding.md` for the full analysis and
`reports/data_coverage.md` for the filter-variant writeup. This closes out
ORB+Pivots/XAUUSD as a definitive negative result, not an inconclusive
one — reported as-is, not smoothed over.

## Honesty notice

Independent evidence on plain ORB strategies is weak (Brusco's replication
of the closest published system shows the edge dying at ~2.2c/share of
slippage, with 76% of filtered PnL from a single volatile year), and pivot
points have weak standalone predictive support academically. **The go/no-go
gate for the plain ORB baseline must pass on out-of-sample data with
realistic costs before any pivot overlay is added** — see the design
rationale in the project's research documents.

## Real data now available

MT5 connectivity is confirmed working (see `vwap-rsi-strategy`'s
`reports/data_coverage.md` for the full story). Real M5 OHLCV for all 5
assets is cached at `../data_cache/` — confirmed depth: XAUUSD/XAGUSD
~15.7y, BTCUSD ~15.4y, ETHUSD ~11.1y, but **USOIL only ~2.6y** (broker
symbol `US Oil`, not `USOIL`) — any USOIL result here inherits that same
shallow-history caveat. `vwap-rsi-strategy/common/data_fetch.py`'s
`BROKER_SYMBOL_MAP` has the confirmed broker symbol names; sync it here
before building the ORB+Pivots data pipeline rather than re-deriving it.

VWAP+RSI's own real-data XAUUSD result was strongly negative with default
parameters (-71.8% return, Sharpe -4.07, ~100% Monte Carlo ruin
probability) — a live example of the "go/no-go gate" this repo's plan
refers to. Worth keeping in mind when the ORB+Pivots baseline is built:
don't assume it'll fare differently just because the mechanism is
different — the research docs flag both edges as weak/fragile.

## Layout

- `common/` — vendored shared math/cost/metrics/Monte-Carlo/WFO modules
  (canonical source: sibling `trading-systems/common/`).
- `backtest/`, `mql5_ea/`, `optimization/`, `reports/`, `live_monitor/`,
  `tests/`, `data/` — mirrors `vwap-rsi-strategy`'s structure; populated in
  Phase 4.
