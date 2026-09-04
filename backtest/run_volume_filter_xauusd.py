"""Test the research docs' single highest-value documented ORB enhancement
(abnormal opening-volume filter) on real XAUUSD data, on top of the plain
baseline. Compares against the already-recorded baseline result rather
than re-running it.
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
    print(json.dumps(cov, indent=2, default=str))

    # volume_mult=1.0 (today's OR volume >= trailing 14-day average) --
    # the mechanical "abnormal opening volume" definition per the docs.
    volume_only = run_variant(
        df, ORBPivotParams(use_volume_filter=True, volume_mult=1.0, volume_lookback_days=14),
        "ORB + volume filter only (no pivots)",
    )
    volume_and_pivot = run_variant(
        df, ORBPivotParams(use_volume_filter=True, volume_mult=1.0, volume_lookback_days=14, use_pivot_filter=True),
        "ORB + volume filter + pivot bias filter",
    )

    out = {"coverage": cov, "volume_only": volume_only, "volume_and_pivot": volume_and_pivot}
    out_path = Path(__file__).resolve().parents[1] / "reports" / "xauusd_orb_volume_filter_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
