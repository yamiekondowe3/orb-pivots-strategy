# orb-pivots-strategy

Opening Range Breakout + Daily/Weekly Pivot Points strategy. Companion repo
to `vwap-rsi-strategy`, sharing the same `common/` friction model, metrics,
Monte Carlo, and walk-forward-optimization harness.

## Real-data result (headline finding): catastrophic FAIL

## Real-data result: net-negative, after correcting a major cost-model bug

**Important correction:** earlier versions of this README declared a
"definitive" negative result. Those conclusions came from a broken
`common/costs.py` that invented commission/spread constants instead of
using the broker's real terms — on XAUUSD it charged **68% of the per-trade
risk budget in fabricated costs**, which would bury any strategy. That is
fixed (real per-bar MT5 spread; commission defaults to zero for Deriv's
spread-only CFDs; exit-side spread now charged too), and all results were
re-run. See `reports/rr_sweep_finding.md` for the full correction.

Under the corrected model, on the full 15.67-year real XAUUSD M5 history,
the best configuration found is a **2:1.5 stop:target (2.0xATR stop,
1.5xATR target): Sharpe -2.07, win rate 54.0% against a 57.1% breakeven**
— a 3.1-point shortfall. The cost fix roughly halved the damage across
every variant, but **none is profitable**: all finish 3–7 points short of
their own breakeven and still draw down heavily over 15 years.

Honest status: **the ORB signal on XAUUSD M5 is much closer to viable than
the broken model implied, but remains net-negative.** The main untested
lever is selectivity — every variant so far takes ~2 trades/day on
essentially every trading day (no filtering at all), whereas the research
docs' strongest documented ORB result depended on extreme
abnormal-volume selectivity. See `reports/rr_sweep_finding.md` for that
analysis and the walk-forward discipline any such test should follow.

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
