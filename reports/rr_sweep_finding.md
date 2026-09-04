# R:R sweep on XAUUSD — results, and a major cost-model correction

## READ THIS FIRST: an earlier version of this document was wrong

The first version of this file claimed the R:R sweep proved the ORB signal
has "zero information content," on the grounds that expectancy per trade
came out at an identical -1.248 across every R:R setting. **That reasoning
was wrong, twice over:**

1. **The identical -1.248 was arithmetic, not a finding.** In every run the
   account lost essentially the full $10,000 over essentially the same
   ~8,015 trades, so `mean(pnl) = -10000/8015 = -1.2477` by construction.
   It could not have come out any other way and said nothing about signal
   quality.
2. **Every result it was based on came from a broken cost model.** The
   original `common/costs.py` invented plausible-sounding basis-point
   constants instead of using the broker's actual terms. On XAUUSD those
   fabricated numbers charged **~$34 per round trip against a $50 risk
   budget — 68% of the amount risked per trade**:

   | Component | Fabricated model | Broker reality (Deriv) |
   |---|---|---|
   | Commission | $16.14/round trip | **$0** (spread-only CFD pricing) |
   | Spread | $0.483 half / $12.91 RT | $0.075 half (~$0.15 real recorded spread) |
   | **Total** | **$34.05 (68% of risk)** | **~$0.30–0.50 (<1% of risk)** |

   No strategy of any quality survives a 68% drag on risked capital. Every
   "no edge" conclusion drawn under that model was an artifact of the model.

**The fix:** `common/costs.py` now takes costs from the broker's own terms —
commission defaults to zero (overridable per broker) and spread comes from
the **real per-bar spread MT5 records in its rate data**, now preserved
through `common/data_fetch.py` into the cached Parquet. Exit-side spread,
previously not charged at all, is now charged too.

## Results under the CORRECTED cost model

Plain ORB baseline (no pivot or volume filter), real XAUUSD M5, full
15.67-year history, 8,014–8,015 trades per variant:

| stop:target (xATR) | Breakeven WR | Actual WR | Gap | Sharpe | Prior Sharpe (broken costs) |
|---|---|---|---|---|---|
| 2.0 : 1.5 | 57.1% | 54.0% | **-3.1pt** | **-2.07** | -4.37 |
| 1.5 : 1.0 | 60.0% | 53.1% | -6.9pt | -3.66 | -6.56 |
| 2.0 : 1.0 | 66.7% | 61.5% | -5.2pt | -2.95 | -5.38 |
| 1.0 : 2.0 (original) | 33.3% | 29.6% | -3.7pt | -2.64 | -5.39 |

**What this does show:** the cost correction roughly halved the damage
across the board, and confirms a real effect from the R:R choice — wider
stops (2.0xATR) beat tighter ones (1.5xATR), and **2:1.5 is the best
configuration found so far**. Win rate responds to the R:R exactly as
theory predicts (29.6% at 1:2, up to 61.5% at 2:1).

**What it does NOT show:** profitability. Every variant still finishes
3–7 percentage points short of its own breakeven win rate, and all still
draw down to near-total loss over 15 years of compounding. The honest
summary is: **the ORB signal on XAUUSD M5 is much closer to viable than
the broken cost model suggested, but is still net-negative.**

## The remaining untested lever: selectivity

Every variant above took **8,015 trades over 15.67 years — ~2 per day,
hitting the `max_trades_per_day=2` cap on essentially every single trading
day.** That is a strategy with no selectivity at all: it trades every
breakout, in both directions, including obvious whipsaw days.

This matters because the research docs' single strongest documented ORB
result was built on *extreme* selectivity — Zarattini/Barbon/Aziz's
unfiltered breakout returned just 29% over 8 years, while restricting to
the **top 20 stocks per day by abnormal opening relative volume** produced
1,637%. The volume filter tested here used `volume_mult=1.0` (today's OR
volume merely >= the trailing average), which passed ~69% of days — barely
a filter at all.

**Next step, if pursued:** test genuinely selective thresholds
(`volume_mult` of 1.5 / 2.0 / 3.0, and/or a minimum OR-range-vs-ATR
requirement so flat, rangebound openings are skipped) — and validate them
**walk-forward** using the harness in
`../vwap-rsi-strategy/backtest/run_wfo_xauusd.py`, not by picking the best
full-history number. A threshold chosen because it looked best on all 15
years is curve-fitting; one that holds up across rolling out-of-sample
windows is evidence.

Full result JSON: `reports/xauusd_orb_rr_sweep_results.json`.
