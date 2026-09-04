"""Real-data go/no-go check: plain ATR-buffered ORB baseline (NO pivot
overlay yet) on XAUUSD, full achieved MT5 history. Per the plan's staged
approach: if this baseline has no positive expectancy after realistic
costs, do not proceed to the pivot bias filter -- pivots will not rescue a
dead baseline.
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


def run_variant(df, params: ORBPivotParams, label: str) -> dict:
    print(f"\n=== {label} ===")
    t0 = time.time()
    result = run_backtest(df, params, symbol="XAUUSD")
    trades = result["trades"]
    print(f"Backtest took {time.time()-t0:.1f}s, trades={len(trades)}")
    if len(trades) < 10:
        print("Too few trades for meaningful stats.")
        return {"n_trades": len(trades)}
    report = full_report(trades["pnl"], trades["return"])
    print(json.dumps(report, indent=2, default=str))
    mc = run_monte_carlo(trades["return"], n_iterations=5000, method="bootstrap", seed=1)
    print(f"Monte Carlo ruin probability: {mc['ruin_probability']}")
    return {"report": report, "monte_carlo": mc}


def main():
    df = load_parquet("XAUUSD", "M5", root=SHARED_DATA_ROOT)
    cov = report_coverage(df, "XAUUSD-M5")
    print("--- Data coverage ---")
    print(json.dumps(cov, indent=2, default=str))

    baseline = run_variant(df, ORBPivotParams(use_pivot_filter=False, use_pivot_stop_target=False), "Plain ATR-buffered ORB baseline (no pivots)")
    pivot_filtered = run_variant(df, ORBPivotParams(use_pivot_filter=True, use_pivot_stop_target=False), "ORB + pivot bias filter")

    out = {"coverage": cov, "baseline": baseline, "pivot_filtered": pivot_filtered}
    out_path = Path(__file__).resolve().parents[1] / "reports" / "xauusd_orb_pivots_real_data_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
