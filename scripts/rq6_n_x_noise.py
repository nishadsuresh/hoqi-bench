"""
Week 5 Task 6, Day 34: RQ6 supplementary design chart -- for a given
noise level, what samples-per-fit N is needed to reach the preregistered
displacement-error tolerance? Implements
`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 3 (committed before this
script existed, per §0.6).

Unlike Task 4's bidirectional-waveform experiment, this uses the
STANDARD preregistered pipeline unmodified (`runner.run_campaign`,
default `arc.build_arc_ramp` waveform) -- the only thing new is the
config's `[grids.n_x_noise]` interaction, which
`configs/main_campaign.toml` never had (docs/PREREGISTRATION.md
deviation D6).

Pipeline position: runs `configs/supplementary_n_x_noise.toml` via the
normal `run_campaign`/`aggregate_campaign` path, writing to
`results/supplementary/n_x_noise/` (raw, gitignored) and
`results/rq6_n_x_noise_summary.csv` (aggregated, committed). Then builds
the design chart via `statistics.breakdown_threshold`, passing
`samples_per_fit` in DESCENDING order -- see Protocol 3 for why ascending
(the only existing precedent's convention) would be backwards here.
Writes `results/rq6_design_chart.csv`.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402

from hoqi_bench.config import load_sweep_config  # noqa: E402
from hoqi_bench.reference_scale import PREREGISTERED_TOLERANCE_M  # noqa: E402
from hoqi_bench.runner import run_campaign  # noqa: E402
from hoqi_bench.statistics import breakdown_threshold  # noqa: E402
from scripts.aggregate_campaign import aggregate_campaign  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "supplementary_n_x_noise.toml"
RAW_OUTPUT_DIR = REPO_ROOT / "results" / "supplementary" / "n_x_noise"
SUMMARY_OUTPUT = REPO_ROOT / "results" / "rq6_n_x_noise_summary.csv"
DESIGN_CHART_OUTPUT = REPO_ROOT / "results" / "rq6_design_chart.csv"

# DESCENDING -- larger N is EASIER (lower error), the opposite of
# amplitude_ratio/arc_fraction's own ascending-is-harder convention
# (scripts/rq1_rq2_analysis.py), per Protocol 3's explicit note that this
# must not be silently inferred wrong from that precedent.
SAMPLES_PER_FIT_SCAN_ORDER = [1000, 500, 200, 100, 60, 40, 20]


def run_n_x_noise_campaign() -> None:
    """Runs SERIALLY (`n_workers=1`), not the default `ProcessPoolExecutor`
    path -- found by direct execution, not assumed: the default parallel
    path segfaulted on this machine (`docs/journal/day34.md`), while a
    serial run of the identical config completed cleanly. 24,500 fits
    costs nothing to run single-threaded (the full 125,650-fit
    preregistered campaign itself runs in ~14s), so parallelism buys
    negligible wall-clock time here in exchange for a real crash risk --
    the same "isolation buys little for a fast job" reasoning
    `scripts/rq1_cost_measurement.py` and
    `scripts/rq3_hysteresis_bidirectional.py` already use for their own
    supplementary runs, applied here for a different reason (crash
    avoidance rather than clean-timing measurement).
    """
    config = load_sweep_config(CONFIG_PATH)
    run_campaign(config, RAW_OUTPUT_DIR, n_workers=1, resume=True)


def build_design_chart(summary: pd.DataFrame) -> pd.DataFrame:
    """For each method and each noise_std value: the smallest N (via
    `statistics.breakdown_threshold`, scanning N from 1000 down to 20)
    that keeps mean displacement RMSE at or below
    `reference_scale.PREREGISTERED_TOLERANCE_M`.
    """
    grid_rows = summary[summary["condition_name"].str.startswith("grid:n_x_noise:")].copy()
    grid_rows["noise_std"] = (
        grid_rows["condition_name"].str.extract(r"noise_std=([\d.]+)")[0].astype(float)
    )
    grid_rows["samples_per_fit"] = (
        grid_rows["condition_name"].str.extract(r"samples_per_fit=(\d+)")[0].astype(int)
    )

    rows = []
    for method_name in sorted(grid_rows["method_name"].unique()):
        method_rows = grid_rows[grid_rows["method_name"] == method_name]
        for noise_std in sorted(method_rows["noise_std"].unique()):
            at_noise = method_rows[method_rows["noise_std"] == noise_std].set_index(
                "samples_per_fit"
            )
            # Reorder to the pre-specified DESCENDING scan (Protocol 3),
            # not whatever order groupby happens to return.
            ordered = at_noise.loc[SAMPLES_PER_FIT_SCAN_ORDER]
            result = breakdown_threshold(
                SAMPLES_PER_FIT_SCAN_ORDER,
                list(ordered["displacement_rmse_mean_m"]),
                PREREGISTERED_TOLERANCE_M,
                log_scale=False,
            )
            rows.append(
                {
                    "method_name": method_name,
                    "noise_std": noise_std,
                    "min_samples_per_fit_status": result.status,
                    "min_samples_per_fit": result.value,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    run_n_x_noise_campaign()
    summary = aggregate_campaign(RAW_OUTPUT_DIR)
    summary.to_csv(SUMMARY_OUTPUT, index=False)

    chart = build_design_chart(summary)
    chart.to_csv(DESIGN_CHART_OUTPUT, index=False)

    status_counts = chart["min_samples_per_fit_status"].value_counts()
    print(f"Design chart: {len(chart)} (method, noise_std) rows")
    print(status_counts.to_string())
    print(f"Wrote {SUMMARY_OUTPUT} and {DESIGN_CHART_OUTPUT}")
