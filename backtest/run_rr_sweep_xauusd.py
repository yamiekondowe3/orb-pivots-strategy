"""Test tighter-than-stop targets (RR < 1) on the plain ORB baseline, real
XAUUSD data. Motivation: all filter variants converged on ~26-27% win rate
against a 1:2 stop:target ratio (33% breakeven) -- a mismatch. A smaller
target relative to stop should be hit far more often (raising the actual
win rate), even though it also raises the breakeven bar itself. Testing
empirically rather than assuming either effect dominates.

No new entry filters -- isolates the R:R effect on the plain baseline
(use_pivot_filter=False, use_volume_filter=False) for a clean comparison.
"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.data_fetch import load_parquet, report_coverage
from common.metrics import full_report
from common.monte_carlo import run_monte_carlo
from backtest.engine import run_backtest, ORBPivotParams

SHARED_DATA_ROOT = Path(__file__).resolve().parents[2] / "data_cache"

# (stop_atr_mult, target_atr_mult, label). Includes the original 1:2 for a
# like-for-like comparison under the CORRECTED cost model (the previous run
# of this sweep used a cost model that charged ~68% of the risk budget per
# trade in fabricated commission/spread -- see common/costs.py).
VARIANTS = [
    (2.0, 1.5, "2:1.5"),
    (1.5, 1.0, "1.5:1"),
    (2.0, 1.0, "2:1"),
    (1.0, 2.0, "1:2 (original, for comparison)"),
]


def run_variant(df, stop_mult, target_mult, label):
    breakeven_wr = stop_mult / (stop_mult + target_mult)
    print(f"\n=== RR {label} (stop={stop_mult}xATR, target={target_mult}xATR, breakeven win rate={breakeven_wr:.1%}) ===")
    params = ORBPivotParams(stop_atr_mult=stop_mult, target_atr_mult=target_mult,
                             use_pivot_filter=False, use_volume_filter=False)
    t0 = time.time()
    result = run_backtest(df, params, symbol="XAUUSD")
    trades = result["trades"]
    print(f"Backtest took {time.time()-t0:.1f}s, trades={len(trades)}")
    if len(trades) < 10:
        print("Too few trades.")
        return {"n_trades": len(trades), "breakeven_win_rate": breakeven_wr}
    report = full_report(trades["pnl"], trades["return"])
    print(json.dumps(report, indent=2, default=str))
    mc = run_monte_carlo(trades["return"], n_iterations=5000, method="bootstrap", seed=1)
    print(f"Monte Carlo ruin probability: {mc['ruin_probability']}")
    return {"breakeven_win_rate": breakeven_wr, "report": report, "monte_carlo": mc}


def main():
    df = load_parquet("XAUUSD", "M5", root=SHARED_DATA_ROOT)
    cov = report_coverage(df, "XAUUSD-M5")
    print(json.dumps(cov, indent=2, default=str))

    out = {"coverage": cov, "variants": {}}
    for stop_mult, target_mult, label in VARIANTS:
        out["variants"][label] = run_variant(df, stop_mult, target_mult, label)

    out_path = Path(__file__).resolve().parents[1] / "reports" / "xauusd_orb_rr_sweep_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
