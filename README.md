# orb-pivots-strategy

Opening Range Breakout + Daily/Weekly Pivot Points strategy. Companion repo
to `vwap-rsi-strategy`, sharing the same `common/` friction model, metrics,
Monte Carlo, and walk-forward-optimization harness.

## Status: scaffolding only

This repo is currently structural — directories and the vendored `common/`
package are in place, but the ORB+Pivots strategy logic itself has not been
implemented yet. Per the project's staged plan, `vwap-rsi-strategy` on
XAUUSD is being built and validated as the proof-of-concept first; this
repo's strategy code is Phase 4 (replicate the validated pattern here,
staged as the research doc recommends: plain ATR-buffered ORB baseline →
go/no-go gate → add the pivot bias filter only → re-test → optionally add
pivot targets/stops → drop confluence/Camarilla overlays unless they
independently survive walk-forward testing).

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
