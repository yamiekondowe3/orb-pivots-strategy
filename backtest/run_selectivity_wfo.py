"""FINAL OPTIMIZATION TEST: walk-forward selectivity search for ORB on XAUUSD.

Rationale: under the corrected cost model the best fixed configuration
(2:1.5 stop:target) reaches a 54.0% win rate against a 57.1% breakeven --
close, but still negative. Every configuration tested so far takes ~2
trades/day on essentially every trading day, i.e. no selectivity at all,
whereas the research docs' strongest documented ORB result depended on
extreme selectivity (unfiltered breakouts returned 29% over 8 years vs
1,637% when restricted to the top-20 names by abnormal opening volume).

So this searches the SELECTIVITY space, not the payoff space:
  * volume_mult      -- how abnormal the opening volume must be
  * min_or_range_atr -- how wide the opening range must be (skip flat opens)
holding the R:R fixed at the best value already found (2.0 : 1.5), so the
search is over one coherent idea rather than everything at once.

Discipline: parameters are chosen on IN-SAMPLE data only, by normalized
per-trade edge (expectancy in R units -- immune to position size and to
the compounding path), then applied unchanged to the following
OUT-OF-SAMPLE year. The verdict is the OOS aggregate, never the best
in-sample number. Windows with too few trades are not eligible for
selection, so the search cannot "win" by finding a handful of lucky trades.
"""
import sys
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.data_fetch import load_parquet
from common.metrics import full_report
from common.wfo import build_windows
from backtest.engine import run_backtest, ORBPivotParams

SHARED_DATA_ROOT = Path(__file__).resolve().parents[2] / "data_cache"

# Selectivity grid. volume_mult=1.0 is the near-no-op already tested (~69%
# of days pass); 1.5/2.0/3.0 are genuinely selective.
VOLUME_MULTS = [1.0, 1.5, 2.0, 3.0]
MIN_OR_RANGE_ATRS = [0.0, 0.5]
BEST_STOP, BEST_TARGET = 2.0, 1.5      # best R:R found under corrected costs
MIN_TRADES_IS = 30                      # selection eligibility floor


def make_params(volume_mult, min_or_range_atr):
    return ORBPivotParams(
        stop_atr_mult=BEST_STOP, target_atr_mult=BEST_TARGET,
        use_volume_filter=True, volume_mult=volume_mult,
        min_or_range_atr=min_or_range_atr,
    )


def evaluate(data, params):
    r = run_backtest(data, params, symbol="XAUUSD")
    t = r["trades"]
    if len(t) == 0:
        return None, 0
    rep = full_report(t["pnl"], t["return"], r_multiples=t["r_multiple"], entry_ts=t["entry_ts"])
    return rep, len(t)


def main():
    df = load_parquet("XAUUSD", "M5", root=SHARED_DATA_ROOT)
    print(f"Data: {df.index.min()} .. {df.index.max()} ({len(df)} bars)", flush=True)

    windows = build_windows(df.index.min(), df.index.max(), is_years=2, oos_years=1, step_years=1)
    grid = [(v, o) for v in VOLUME_MULTS for o in MIN_OR_RANGE_ATRS]
    print(f"{len(windows)} walk-forward windows x {len(grid)} selectivity combos", flush=True)
    print(f"Fixed R:R = {BEST_STOP}:{BEST_TARGET} (best found under corrected costs)\n", flush=True)

    rows = []
    t_start = time.time()
    for wi, w in enumerate(windows, 1):
        is_data = df.loc[w.is_start:w.is_end]
        oos_data = df.loc[w.oos_start:w.oos_end]
        if is_data.empty or oos_data.empty:
            continue

        # --- select on IN-SAMPLE only, by normalized per-trade edge ---
        best = None
        for volume_mult, min_or in grid:
            rep, n = evaluate(is_data, make_params(volume_mult, min_or))
            if rep is None or n < MIN_TRADES_IS:
                continue
            score = rep.get("expectancy_r", -np.inf)
            if best is None or score > best["score"]:
                best = {"score": score, "volume_mult": volume_mult, "min_or_range_atr": min_or,
                        "is_expectancy_r": score, "is_n_trades": n, "is_win_rate": rep["win_rate"]}
        if best is None:
            print(f"[{wi}/{len(windows)}] {w.oos_start.date()}: no eligible IS combo", flush=True)
            continue

        # --- apply unchanged to OUT-OF-SAMPLE ---
        oos_rep, oos_n = evaluate(oos_data, make_params(best["volume_mult"], best["min_or_range_atr"]))
        row = {
            "oos_year": str(w.oos_start.date()),
            "chosen_volume_mult": best["volume_mult"],
            "chosen_min_or_range_atr": best["min_or_range_atr"],
            "is_expectancy_r": round(best["is_expectancy_r"], 4),
            "is_n_trades": best["is_n_trades"],
            "oos_n_trades": oos_n,
            "oos_expectancy_r": round(oos_rep.get("expectancy_r", 0.0), 4) if oos_rep else 0.0,
            "oos_win_rate": round(oos_rep["win_rate"], 4) if oos_rep else 0.0,
            "oos_sharpe_r": round(oos_rep.get("sharpe_r", 0.0), 3) if oos_rep else 0.0,
            "oos_total_return_pct": round(oos_rep["total_return_pct"], 4) if oos_rep else 0.0,
        }
        rows.append(row)
        print(f"[{wi}/{len(windows)}] OOS {row['oos_year']}: "
              f"chose vol>={row['chosen_volume_mult']}x, OR>={row['chosen_min_or_range_atr']}xATR | "
              f"IS E[R]={row['is_expectancy_r']:+.4f} -> OOS E[R]={row['oos_expectancy_r']:+.4f} "
              f"({row['oos_n_trades']} trades, WR {row['oos_win_rate']:.1%})", flush=True)

    result = pd.DataFrame(rows)
    print(f"\nTotal walk-forward time: {time.time()-t_start:.0f}s")
    if result.empty:
        print("No windows produced results.")
        return

    print("\n" + "=" * 70)
    print("FINAL OUT-OF-SAMPLE VERDICT (normalized, per-trade edge in R units)")
    print("=" * 70)
    mean_oos_r = result["oos_expectancy_r"].mean()
    total_oos_trades = int(result["oos_n_trades"].sum())
    pos_windows = int((result["oos_expectancy_r"] > 0).sum())
    print(result.to_string(index=False))
    print(f"\nWindows with positive OOS edge : {pos_windows} / {len(result)}")
    print(f"Mean OOS expectancy            : {mean_oos_r:+.4f} R per trade")
    print(f"Total OOS trades               : {total_oos_trades}")
    print(f"Mean OOS win rate              : {result['oos_win_rate'].mean():.1%}")
    print(f"Mean OOS Sharpe (R-normalized) : {result['oos_sharpe_r'].mean():+.3f}")
    verdict = "PROFITABLE out-of-sample" if mean_oos_r > 0 else "NOT profitable out-of-sample"
    print(f"\nVERDICT: {verdict}")

    out_path = Path(__file__).resolve().parents[1] / "reports" / "xauusd_selectivity_wfo_results.json"
    out_path.write_text(json.dumps({
        "grid": {"volume_mults": VOLUME_MULTS, "min_or_range_atrs": MIN_OR_RANGE_ATRS,
                 "fixed_stop_atr": BEST_STOP, "fixed_target_atr": BEST_TARGET},
        "windows": rows,
        "summary": {"mean_oos_expectancy_r": mean_oos_r, "positive_windows": pos_windows,
                    "total_windows": len(result), "total_oos_trades": total_oos_trades,
                    "mean_oos_win_rate": float(result["oos_win_rate"].mean()),
                    "verdict": verdict},
    }, indent=2, default=str))
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
