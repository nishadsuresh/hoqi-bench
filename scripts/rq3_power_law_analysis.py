"""
Day 30: characterizes whether mean displacement error scales as a power
law of injected distortion magnitude, per RQ3 and Lehmann et al. 2025's
Section III.C finding ("residual nonlinearity follows a power-law trend,
close to power of 3").

Per Day 13's confirmed scope decision (`power_law.py`'s own module
docstring): this does NOT inject a new forward-model mechanism. It fits
`hoqi_bench.power_law.fit_power_law_exponent` against the ALREADY-RUN main
campaign's per-condition mean error, across the four axes with a
monotonic, zero-anchored distortion magnitude: `amplitude_ratio` (as
`ratio - 1.0`, since 1.0 is the axis's own zero-distortion point),
`quadrature_error_rad`, `dc_offset`, and `hysteresis_magnitude`.

IMPORTANT NAMING NOTE on the last of these four (Weeks 5-6, Day 29,
`docs/PREREGISTRATION.md` deviation D5): the preregistered
`hysteresis_magnitude` axis measures direction-INDEPENDENT radial
inflation, not path-dependent hysteresis -- every campaign waveform is
monotonic. It is still a real, monotonic distortion magnitude, so it is a
legitimate power-law characterization target; every output here labels it
"radial inflation (preregistered as hysteresis_magnitude; see D5)",
never bare "hysteresis", so this script cannot misrepresent what the
axis actually measured.

Pipeline position: reads `results/main_campaign_summary.csv` (the
contract-aware, already-aggregated table -- never re-derives a mean from
the raw per-seed table, matching `scripts/aggregate_campaign.py`'s own
stated rationale for why that aggregation step exists at all) and
`configs/main_campaign.toml` (for the exact swept values, programmatically,
never hand-copied). Writes `results/rq3_power_law.csv`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from hoqi_bench._types import FloatArray
from hoqi_bench.aggregate import MAX_UNUSABLE_RATE_FOR_RANKING
from hoqi_bench.config import load_sweep_config
from hoqi_bench.power_law import fit_power_law_exponent

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "main_campaign.toml"
SUMMARY_PATH = REPO_ROOT / "results" / "main_campaign_summary.csv"
OUTPUT_PATH = REPO_ROOT / "results" / "rq3_power_law.csv"

# ---- 1. The four monotonic-distortion-magnitude axes, and how to derive
# "magnitude" from each one's own swept value ---------------------------
#
# amplitude_ratio's zero-distortion point is 1.0 (a perfect, undistorted
# circle), not 0.0 -- so its magnitude is `ratio - 1.0`. The other three
# axes are already zero-anchored in their own units.
_AXIS_MAGNITUDE_TRANSFORM: dict[str, Callable[[float], float]] = {
    "amplitude_ratio": lambda v: v - 1.0,
    "quadrature_error_rad": lambda v: v,
    "dc_offset": lambda v: v,
    "hysteresis_magnitude": lambda v: v,  # see module docstring: radial inflation, not hysteresis
}

_AXIS_DISPLAY_NAME = {
    "amplitude_ratio": "amplitude_ratio",
    "quadrature_error_rad": "quadrature_error_rad",
    "dc_offset": "dc_offset",
    "hysteresis_magnitude": "radial_inflation (preregistered as hysteresis_magnitude; see D5)",
}

# ---- 2. The r^2 honesty gate, pre-committed BEFORE this script was run
# against real campaign numbers (Day 30, 2026-07-28 calibration) --------
#
# Per power_law.py's own documented fallback: a low r^2 here (no clean
# power-law relationship in this project's own data) is itself the
# trigger to fall back to modeling power-law as an injected transform
# instead -- NOT something this script chooses silently. It is reported
# and escalated to Nishi, per docs/WEEK5-6_EXECUTION_PLAN.md Task 2's
# decision-point list.
#
# Calibrated via two synthetic experiments run BEFORE looking at any real
# result (see docs/journal/day30.md for the full numbers): a genuinely
# FLAT relationship (no power-law at all), fit with the same 7-10-point
# grids and Monte-Carlo-realistic 5/15/30% relative noise, produces
# r^2 <= 0.890 across 3,000 trials at every noise level tested (mean
# ~0.13, p99 ~0.64). A genuine n=3 power law, at the SAME noise levels,
# produces r^2 >= 0.990 in every trial. R_SQUARED_FLOOR sits in the gap
# between those two distributions -- above the null's observed worst
# case, comfortably below a real relationship's worst case -- rather
# than being a round number chosen by taste.
R_SQUARED_FLOOR = 0.90

# Lehmann et al. 2025, Section III.C: residual nonlinearity vs. motion
# range follows a power-law trend "close to power of 3". Reported here
# as a reference value to compare against, per this script's own honesty
# rule: recovering ~3 is a finding; NOT recovering it is equally a
# finding (Lehmann's exponent is an observed residual-noise SCALING
# relationship on THEIR axis -- motion range -- not a value this
# project's DIFFERENT axes -- distortion magnitude -- are expected to
# reproduce; a mismatch is not evidence of anything being wrong here).
LEHMANN_REFERENCE_EXPONENT = 3.0


def _method_error_series(
    summary: pd.DataFrame, axis: str, method: str, swept_values: list[float]
) -> tuple[FloatArray, FloatArray, int]:
    """(magnitudes, errors, n_excluded_unrankable) for one (axis, method),
    already zero-point-excluded and unusable-rate-filtered.

    Design decision: a grid point is excluded from a method's OWN fit if
    that method's `unusable_rate` there exceeds
    `aggregate.MAX_UNUSABLE_RATE_FOR_RANKING` (0.20) -- the same threshold
    `aggregate.is_rankable` already uses project-wide, applied per-point
    here rather than requiring all 7 methods to agree a point is usable
    (a single method being unusable at one grid point should not exclude
    that point from every OTHER method's fit).
    """
    transform = _AXIS_MAGNITUDE_TRANSFORM[axis]
    magnitudes = []
    errors = []
    n_excluded = 0
    for value in swept_values:
        magnitude = transform(value)
        if magnitude <= 0.0:
            continue  # the axis's own zero-distortion point; log-log fit cannot use it
        row = summary[
            (summary["condition_name"] == f"axis:{axis}={value}")
            & (summary["method_name"] == method)
        ]
        if row.empty:
            continue
        unusable_rate = float(row["unusable_rate"].iloc[0])
        error = row["displacement_rmse_mean_m"].iloc[0]
        if unusable_rate > MAX_UNUSABLE_RATE_FOR_RANKING or pd.isna(error) or error <= 0.0:
            n_excluded += 1
            continue
        magnitudes.append(magnitude)
        errors.append(float(error))
    return np.array(magnitudes), np.array(errors), n_excluded


def build_rq3_power_law_table() -> pd.DataFrame:
    config = load_sweep_config(CONFIG_PATH)
    summary = pd.read_csv(SUMMARY_PATH)
    methods = config.methods

    rows = []
    for axis in _AXIS_MAGNITUDE_TRANSFORM:
        swept_values = config.axes[axis]
        for method in methods:
            magnitudes, errors, n_excluded = _method_error_series(
                summary, axis, method, swept_values
            )
            n_points = len(magnitudes)
            if n_points < 3:
                # Not enough surviving points for a meaningful log-log fit
                # (2 points fit ANY line at r^2=1.0, which is not evidence
                # of a power law -- report as insufficient data, not as a
                # spuriously perfect fit).
                rows.append(
                    {
                        "axis": _AXIS_DISPLAY_NAME[axis],
                        "method": method,
                        "n_points_used": n_points,
                        "n_points_excluded_unrankable": n_excluded,
                        "exponent": np.nan,
                        "coefficient": np.nan,
                        "r_squared": np.nan,
                        "meets_r_squared_floor": False,
                        "matches_lehmann_exponent": False,
                        "status": "insufficient_usable_data",
                    }
                )
                continue

            exponent, coefficient, r_squared = fit_power_law_exponent(magnitudes, errors)
            meets_floor = r_squared >= R_SQUARED_FLOOR
            # "Matches Lehmann" is reported only when the fit itself is
            # trustworthy (meets_floor) -- an exponent from a poor fit is
            # not a meaningful number to compare against anything.
            matches_lehmann = meets_floor and abs(exponent - LEHMANN_REFERENCE_EXPONENT) <= 0.5
            rows.append(
                {
                    "axis": _AXIS_DISPLAY_NAME[axis],
                    "method": method,
                    "n_points_used": n_points,
                    "n_points_excluded_unrankable": n_excluded,
                    "exponent": exponent,
                    "coefficient": coefficient,
                    "r_squared": r_squared,
                    "meets_r_squared_floor": meets_floor,
                    "matches_lehmann_exponent": matches_lehmann,
                    "status": "fit" if meets_floor else "no_clean_power_law",
                }
            )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    table = build_rq3_power_law_table()
    table.to_csv(OUTPUT_PATH, index=False)

    n_clean = int(table["meets_r_squared_floor"].sum())
    n_total = len(table)
    print(f"{n_clean}/{n_total} (axis, method) fits meet the R^2 >= {R_SQUARED_FLOOR} floor")
    print(f"Wrote {OUTPUT_PATH}")

    if n_clean == 0:
        print(
            "\nNo (axis, method) pair produced a clean power-law fit. Per power_law.py's "
            "documented fallback and docs/WEEK5-6_EXECUTION_PLAN.md Task 2's decision-point "
            "list, this is NOT this script's call to resolve -- escalate to Nishi rather than "
            "silently switching to an injected power-law transform."
        )
