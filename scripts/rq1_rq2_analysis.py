"""
Day 28: computes the RQ1 (comparative ranking) and RQ2 (breakdown
threshold) tables over the main campaign's raw results, using ONLY the
already-built, already-tested tools -- `aggregate.summarize`,
`statistics.bootstrap_ci`, `statistics.breakdown_threshold`,
`statistics.pairwise_comparisons`, `harmonics` (via the raw table's
cyclic_* columns), `reference_scale.PREREGISTERED_TOLERANCE_M`.

Not part of the pytest suite -- a one-shot analysis step, like
`scripts/aggregate_campaign.py`, run once against a completed campaign to
produce the tables the RQ1/RQ2 writeup (docs/journal/day28.md,
docs/RQ1_RQ2_ANALYSIS.md) reports.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from hoqi_bench.aggregate import MAX_UNUSABLE_RATE_FOR_RANKING
from hoqi_bench.config import SweepConfig, load_sweep_config
from hoqi_bench.reference_scale import PREREGISTERED_TOLERANCE_M
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.runner import load_results
from hoqi_bench.statistics import bootstrap_ci, breakdown_threshold, pairwise_comparisons

RAW_DIR = Path(__file__).parent.parent / "results" / "raw"
CONFIG_PATH = Path(__file__).parent.parent / "configs" / "main_campaign.toml"
OUTPUT_DIR = Path(__file__).parent.parent / "results"

CLASSIC_AXES = ("amplitude_ratio", "quadrature_error_rad", "dc_offset")
OPEN_AXES = ("arc_fraction", "noise_std", "samples_per_fit", "hysteresis_magnitude", "photon_scale")
BREAKDOWN_AXES = {"amplitude_ratio": False, "arc_fraction": True}  # value: log_scale


def _add_reliability_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["gross"] = (~frame["failed"]) & (frame["phase_rmse_rad"] > 0.5)
    frame["unusable"] = frame["failed"] | frame["gross"]
    return frame


def _axis_conditions(config: SweepConfig, axis: str) -> list[tuple[str, float]]:
    """(condition_name, swept_value) pairs for one OFAT axis, in the order
    the config lists them -- easiest to hardest for every axis in this
    campaign (verified: amplitude_ratio ascends from 1.0, arc_fraction
    descends from 1.0, both starting at the undistorted/full-coverage
    baseline)."""
    values = config.axes[axis]
    return [(f"axis:{axis}={v}", v) for v in values]


def build_rq1_table(frame: pd.DataFrame, config: SweepConfig) -> pd.DataFrame:
    """Per (axis, method): mean displacement RMSE + 95% bootstrap CI at
    the BASELINE (easiest) and WORST (hardest, i.e. last swept) grid
    point, failure/gross/unusable rates, mean runtime, and whether the
    method is rankable at the worst point (per
    docs/WEEK3_METHOD_CONTRACT.md sec2.1's MAX_UNUSABLE_RATE_FOR_RANKING).
    """
    rows = []
    for axis in CLASSIC_AXES + OPEN_AXES:
        conditions = _axis_conditions(config, axis)
        baseline_name, baseline_value = conditions[0]
        worst_name, worst_value = conditions[-1]

        for condition_name, swept_value, position in (
            (baseline_name, baseline_value, "baseline"),
            (worst_name, worst_value, "worst"),
        ):
            sub = frame[frame["condition_name"] == condition_name]
            for method_name, group in sub.groupby("method_name", sort=False):
                usable = group[~group["unusable"]]
                if len(usable) >= 2:
                    low, high = bootstrap_ci(usable["displacement_rmse_m"].to_numpy(), seed=0)
                else:
                    low = high = float("nan")
                rows.append(
                    {
                        "axis": axis,
                        "position": position,
                        "swept_value": swept_value,
                        "method_name": method_name,
                        "n_seeds": len(group),
                        "failure_rate": float(group["failed"].mean()),
                        "gross_error_rate": float(group["gross"].mean()),
                        "unusable_rate": float(group["unusable"].mean()),
                        "displacement_rmse_mean_m": float(usable["displacement_rmse_m"].mean())
                        if len(usable)
                        else float("nan"),
                        "displacement_rmse_ci_low_m": low,
                        "displacement_rmse_ci_high_m": high,
                        "mean_runtime_s": float(group["runtime_s"].mean()),
                        "rankable": float(group["unusable"].mean())
                        <= MAX_UNUSABLE_RATE_FOR_RANKING,
                    }
                )
    return pd.DataFrame(rows)


def build_pairwise_significance(frame: pd.DataFrame, config: SweepConfig) -> pd.DataFrame:
    """Pairwise significance (Bonferroni-corrected paired t-test) among
    all 7 methods, at the WORST grid point of every axis -- the condition
    where real differences, if any survive at all, are most likely to be
    statistically distinguishable rather than lost in overlapping CIs."""
    rows = []
    for axis in CLASSIC_AXES + OPEN_AXES:
        conditions = _axis_conditions(config, axis)
        worst_name, worst_value = conditions[-1]
        sub = frame[frame["condition_name"] == worst_name]
        errors_by_method = {
            str(m): g.sort_values("seed_index")["displacement_rmse_m"].to_numpy()
            for m, g in sub.groupby("method_name", sort=False)
        }
        for comparison in pairwise_comparisons(errors_by_method):
            rows.append(
                {
                    "axis": axis,
                    "swept_value": worst_value,
                    "method_a": comparison.method_a,
                    "method_b": comparison.method_b,
                    "mean_difference_m": comparison.mean_difference,
                    "p_value": comparison.p_value,
                    "significant": comparison.significant,
                }
            )
    return pd.DataFrame(rows)


def build_rq2_table(frame: pd.DataFrame, config: SweepConfig) -> pd.DataFrame:
    """Breakdown threshold per method, for the two preregistered axes
    (amplitude_ratio: linear scale; arc_fraction: log scale), using ONLY
    usable-fit means at each grid point and the fixed physical tolerance
    (D3's resolution)."""
    rows = []
    for axis, log_scale in BREAKDOWN_AXES.items():
        conditions = _axis_conditions(config, axis)
        values = [v for _, v in conditions]
        method_names = sorted(frame["method_name"].unique())
        for method_name in method_names:
            means = []
            for condition_name, _ in conditions:
                sub = frame[
                    (frame["condition_name"] == condition_name)
                    & (frame["method_name"] == method_name)
                ]
                usable = sub[~sub["unusable"]]
                means.append(
                    float(usable["displacement_rmse_m"].mean()) if len(usable) else float("nan")
                )
            result = breakdown_threshold(
                values, means, PREREGISTERED_TOLERANCE_M, log_scale=log_scale
            )
            rows.append(
                {
                    "axis": axis,
                    "method_name": method_name,
                    "breakdown_status": result.status,
                    "breakdown_value": result.value,
                }
            )
    return pd.DataFrame(rows)


def build_cyclic_error_table(frame: pd.DataFrame, config: SweepConfig) -> pd.DataFrame:
    """Mean cyclic-error amplitudes at the baseline of the classic axes,
    filtered to well_conditioned AND NOT failed (D2's aggregation caveat)."""
    rows = []
    for axis in CLASSIC_AXES:
        conditions = _axis_conditions(config, axis)
        baseline_name, baseline_value = conditions[0]
        sub = frame[frame["condition_name"] == baseline_name]
        for method_name, group in sub.groupby("method_name", sort=False):
            valid = group[group["cyclic_well_conditioned"] & (~group["failed"])]
            rows.append(
                {
                    "axis": axis,
                    "swept_value": baseline_value,
                    "method_name": method_name,
                    "n_valid": len(valid),
                    "cyclic_first_order_mean_rad": float(valid["cyclic_first_order_rad"].mean())
                    if len(valid)
                    else float("nan"),
                    "cyclic_second_order_mean_rad": float(valid["cyclic_second_order_rad"].mean())
                    if len(valid)
                    else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    config = load_sweep_config(CONFIG_PATH)
    iter_conditions(config)  # validates the grid resolves cleanly
    frame = _add_reliability_columns(load_results(RAW_DIR))

    rq1 = build_rq1_table(frame, config)
    rq1.to_csv(OUTPUT_DIR / "rq1_ranking.csv", index=False)

    significance = build_pairwise_significance(frame, config)
    significance.to_csv(OUTPUT_DIR / "rq1_pairwise_significance.csv", index=False)

    rq2 = build_rq2_table(frame, config)
    rq2.to_csv(OUTPUT_DIR / "rq2_breakdown_thresholds.csv", index=False)

    cyclic = build_cyclic_error_table(frame, config)
    cyclic.to_csv(OUTPUT_DIR / "rq1_cyclic_error.csv", index=False)

    print("RQ1 ranking rows:", len(rq1))
    print("Pairwise significance rows:", len(significance))
    print("RQ2 breakdown threshold rows:", len(rq2))
    print("Cyclic error rows:", len(cyclic))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
