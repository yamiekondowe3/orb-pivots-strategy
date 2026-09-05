# Final verdict: ORB(+Pivots) on XAUUSD — not profitable out-of-sample

This is the conclusion of the investigation, after correcting a major
cost-model bug and running a disciplined walk-forward optimization over
the one lever with genuine research backing (selectivity).

## Method

- **Data:** real MT5/Deriv-Demo XAUUSD M5, 2011-01-02 → 2026-09-04,
  1,094,386 bars (15.67 years), with the broker's **real per-bar spread**.
- **Costs:** corrected model — zero commission (Deriv prices these CFDs
  spread-only), real recorded spread charged on **both** entry and exit,
  ATR-scaled slippage. The earlier model's fabricated costs consumed 68%
  of the per-trade risk budget and invalidated all results produced under it.
- **Payoff:** fixed at 2.0:1.5 ATR stop:target — the best R:R found under
  corrected costs — so the search tested *one* coherent idea rather than
  everything at once.
- **Search space (selectivity):** `volume_mult` ∈ {1.0, 1.5, 2.0, 3.0} ×
  `min_or_range_atr` ∈ {0.0, 0.5} = 8 combinations.
- **Protocol:** 13 rolling windows, 2 years in-sample → 1 year
  out-of-sample. Parameters chosen on in-sample data **only**, by
  normalized per-trade edge, then applied unchanged to the next year.
  Minimum 30 in-sample trades required for a combo to be selectable.

## Normalization (why the numbers here differ from earlier reports)

Earlier reports compared strategies by **dollar** expectancy and a Sharpe
annualized with a hardcoded 252. Both were misleading:

- **Dollar expectancy is path-contaminated.** When an account is driven to
  near-zero, `mean(pnl)` is forced to `-starting_equity / n_trades`
  regardless of the strategy — which is exactly why four very different
  R:R settings all reported an identical -1.248 (an artifact previously,
  and wrongly, described here as evidence of "zero information content").
- **Sharpe was mis-annualized.** These strategies take ~500 trades/year,
  not 252, so per-trade Sharpe was scaled by `sqrt(252)` instead of
  `sqrt(actual trades/year)`.

Both are fixed. The headline measure is now **expectancy in R units**
(`pnl / dollars risked on that trade`) — independent of position size,
account size, and the compounding path — plus an R-normalized Sharpe
annualized by the true trade rate.

## Results

| OOS year | Chosen filter | IS E[R] | OOS E[R] | OOS trades | OOS win rate |
|---|---|---|---|---|---|
| 2013 | vol≥2.0×, OR≥0.5×ATR | -0.094 | **-0.173** | 42 | 50.0% |
| 2014 | vol≥2.0×, OR≥0.0×ATR | -0.123 | **-0.167** | 30 | 53.3% |
| 2015 | vol≥1.5×, OR≥0.0×ATR | -0.077 | **-0.297** | 121 | 45.5% |
| 2016 | vol≥1.0×, OR≥0.5×ATR | -0.179 | **-0.231** | 334 | 48.8% |
| 2017 | vol≥1.0×, OR≥0.5×ATR | -0.202 | **-0.262** | 309 | 48.9% |
| 2018 | vol≥2.0×, OR≥0.0×ATR | -0.114 | **-0.006** | 26 | 61.5% |
| 2019 | vol≥2.0×, OR≥0.5×ATR | -0.064 | **+0.032** | 54 | 61.1% |
| 2020 | vol≥2.0×, OR≥0.5×ATR | +0.045 | **+0.081** | 62 | 62.9% |
| 2021 | vol≥2.0×, OR≥0.5×ATR | +0.099 | **-0.576** | 12 | 25.0% |
| 2022 | vol≥2.0×, OR≥0.0×ATR | +0.040 | **-0.071** | 30 | 53.3% |
| 2023 | vol≥1.5×, OR≥0.5×ATR | +0.030 | **-0.078** | 116 | 54.3% |
| 2024 | vol≥1.5×, OR≥0.5×ATR | -0.022 | **-0.091** | 110 | 52.7% |
| 2025 | vol≥1.0×, OR≥0.0×ATR | -0.069 | **-0.060** | 370 | 54.3% |

**Aggregate out-of-sample (1,616 trades):**
- Windows with positive OOS edge: **2 / 13**
- Mean OOS expectancy: **-0.146 R per trade**
- Mean OOS win rate: 51.7%
- Mean OOS R-normalized Sharpe: **-1.693**

## Reading of the result

1. **Selectivity did not rescue the strategy.** It genuinely helped —
   the selective configs (vol≥2.0×, OR≥0.5×ATR) produced the only positive
   windows (2019, 2020) and much better win rates (61–63% vs ~49%) — but
   not enough, and not durably.
2. **The in-sample→out-of-sample decay is systematic, which is the real
   tell.** In every window where the search found a positive in-sample
   edge (2020, 2021, 2022, 2023), three of the four decayed to negative
   out-of-sample. Window 2021 is the textbook case: the strongest
   in-sample result of the whole study (+0.099R) collapsed to -0.576R
   out-of-sample. That is the signature of the search fitting noise, not
   discovering structure — precisely the failure mode the source research
   documents warn about.
3. **Selective configurations are sample-starved.** The strict filters
   leave 12–62 trades per out-of-sample year. Even the positive years rest
   on samples far too small to distinguish edge from luck.
4. **-0.146R per trade is not marginal.** At 0.5% risk per trade that is
   roughly -0.073% of equity per trade, ~500 trades/year — a decisive,
   not borderline, negative expectancy.

## Cross-strategy diagnostic: in-sample selection predicts nothing

Testing whether choosing parameters in-sample carries **any** information
about out-of-sample performance, across both strategies' walk-forwards:

| Strategy | IS→OOS correlation | Mean OOS when IS>0 | Mean OOS when IS≤0 |
|---|---|---|---|
| ORB+Pivots | r = **-0.033** (p=0.91) | -0.1609 R (n=4) | -0.1394 R (n=9) |
| VWAP+RSI | r = **+0.109** (p=0.72) | -0.1214 R (n=7) | -0.1214 R (n=6) |

The correlation is statistically indistinguishable from zero in both. For
VWAP+RSI the conditional means are identical to four decimals — windows
where the optimizer found a positive in-sample edge did exactly as badly
out-of-sample as windows where it found a negative one.

This is stronger evidence than any single negative backtest, and it is
what rules out the obvious next move: a **larger** parameter search would
produce better in-sample numbers and the same out-of-sample expectation,
because the in-sample differences being selected on are noise.

## Conclusion

**Every lever the source research documents recommended has now been
tested on real data with a correct cost model and honest walk-forward
validation: pivot bias filter, abnormal-volume filter, opening-range width
filter, and the payoff ratio itself. None produces a positive
out-of-sample edge on XAUUSD M5.**

The strategy is not profitable on this instrument and timeframe. Further
parameter search would be fitting noise — the 2021 window shows exactly
what that produces. This is reported as a negative result rather than
tuned until a favourable number appeared.

What would constitute a genuinely *new* test (rather than more of the
same search): a different instrument or timeframe, an intraday session
anchor other than 08:00 UTC, or a fundamentally different signal. Those
are new hypotheses, not refinements of this one.

Raw data: `reports/xauusd_selectivity_wfo_results.json`,
`reports/selectivity_wfo_log.txt`.
