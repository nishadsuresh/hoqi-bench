"""
Day 31: measures the preregistered `cost` metric (wall-clock time per fit,
mean and std across seeds, plus iteration count for iterative methods) via
a SERIAL, single-worker pass over a small, structurally pre-selected
subset of the main campaign's own preregistered conditions -- completing
`docs/PREREGISTRATION.md`'s Metrics section commitment, which
`docs/WEEK5_PREFLIGHT_AUDIT.md` finding P3 found 100% unmeasured (the
sweep runner never called `methods.base.timed_fit` before Day 31's fix,
`src/hoqi_bench/runner.py`).

WHY SERIAL, NOT THE PARALLEL MAIN CAMPAIGN'S OWN NUMBERS: the main
campaign runs under `ProcessPoolExecutor`. Per-fit wall-clock measured
inside contending parallel workers reflects scheduler contention as much
as algorithm cost, and does not honor the preregistration's "same
hardware" wording in any stable sense. This script calls `run_condition`
directly (bypassing `run_campaign`'s pool entirely -- there is no worker
pool to bypass, `run_condition` itself is single-process), so every fit in
this pass runs alone on this machine with BLAS pinned to 1 thread (same
`runner.py` import-time pin every other process in this project uses).

WHY A SUBSET, NOT THE FULL 359 CONDITIONS: `results/raw/` (the
preregistered main campaign) is immutable per
`docs/WEEK5-6_EXECUTION_PLAN.md`'s Global Constraints -- this script
writes to `results/supplementary/cost_measurement/`, a physically separate
tree, and does not touch or replace anything under `results/raw/`. A
smaller pass is also simply sufficient: cost is a property of the
ALGORITHM and the INPUT SIZE (`samples_per_fit`), not of which specific
distortion magnitude is injected, so a representative subset spanning
every axis's extreme, plus the shared baseline, covers the input
conditions that plausibly affect runtime without re-running all 359.

THE SUBSET, chosen on STRUCTURAL grounds ONLY, before looking at any
accuracy or cost result (the same discipline
`docs/WEEK5-6_EXECUTION_PLAN.md` Task 3.2 requires, to avoid handing this
analysis a second free parameter): the one condition where EVERY axis
sits at its own baseline value (`axis:amplitude_ratio=1.1` -- 1.1 is both
`amplitude_ratio`'s baseline AND a value that axis actually sweeps, so
this condition IS the pure baseline, not a distortion-axis point in
disguise), plus the LAST configured value of each of the 8 OFAT axes
(`configs/main_campaign.toml`'s own list order, read programmatically,
never re-ordered or cherry-picked by this script). 9 conditions total.

Pipeline position: reads `configs/main_campaign.toml`, calls
`runner.run_condition` directly (not `run_campaign`, which is built for
the parallel/resumable/incremental campaign this is deliberately NOT).
Writes `results/supplementary/cost_measurement/*.parquet` (raw, per-seed,
matching `runner.RESULT_COLUMNS`) and `results/rq1_cost_analysis.csv`
(the aggregated mean/std/iteration-count table this analysis reports).
"""

from __future__ import annotations

import os

# Must precede any transitive numpy import -- same reasoning as runner.py's
# own import-time pin (conftest.py's docstring; Day 20's runtime probe).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402

from hoqi_bench.config import SweepConfig, load_sweep_config  # noqa: E402
from hoqi_bench.resolve import ResolvedCondition, iter_conditions  # noqa: E402
from hoqi_bench.runner import condition_filename, run_condition  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "main_campaign.toml"
OUTPUT_DIR = REPO_ROOT / "results" / "supplementary" / "cost_measurement"
ANALYSIS_OUTPUT = REPO_ROOT / "results" / "rq1_cost_analysis.csv"

# The one condition equal to the full baseline on every axis simultaneously
# -- amplitude_ratio=1.1 IS the baseline (see module docstring).
BASELINE_CONDITION_NAME = "axis:amplitude_ratio=1.1"


def select_cost_measurement_conditions(config: SweepConfig) -> list[ResolvedCondition]:
    """Baseline + the last configured value of every OFAT axis -- see
    module docstring for why this selection is structural, not
    accuracy-informed."""
    all_conditions = {c.name: c for c in iter_conditions(config)}
    selected = [all_conditions[BASELINE_CONDITION_NAME]]
    for axis, values in config.axes.items():
        extreme_name = f"axis:{axis}={values[-1]}"
        if extreme_name == BASELINE_CONDITION_NAME:
            continue  # do not double-count if an axis's last value IS baseline
        selected.append(all_conditions[extreme_name])
    return selected


def run_cost_measurement_pass(config: SweepConfig) -> None:
    """Runs every selected condition SERIALLY (no ProcessPoolExecutor --
    `run_condition` is called directly, in-process, one at a time), writing
    one Parquet file per condition, matching `runner.py`'s own atomic-write
    convention so a partial run cannot be mistaken for a complete one.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for condition in select_cost_measurement_conditions(config):
        frame = run_condition(condition, list(config.methods), config.n_seeds)
        final_path = OUTPUT_DIR / condition_filename(condition.name)
        temp_path = final_path.with_suffix(".parquet.tmp")
        frame.to_parquet(temp_path, index=False)
        os.replace(temp_path, final_path)


def build_cost_analysis_table() -> pd.DataFrame:
    """Per (condition, method): mean and std runtime_s across seeds (the
    preregistered cost definition, `docs/PREREGISTRATION.md`'s Metrics
    section), plus mean iteration count for Koning (the only iterative
    method -- every other method's n_iter is null by design, per
    `FitResult`'s own docstring, so its mean is reported as NaN, not
    silently coerced to 0)."""
    paths = sorted(OUTPUT_DIR.glob("*.parquet"))
    if not paths:
        raise FileNotFoundError(
            f"no results in {OUTPUT_DIR} -- run run_cost_measurement_pass() first"
        )
    raw = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)

    grouped = raw.groupby(["condition_name", "method_name"], as_index=False).agg(
        runtime_s_mean=("runtime_s", "mean"),
        runtime_s_std=("runtime_s", "std"),
        n_iter_mean=("n_iter", "mean"),
        n_seeds=("runtime_s", "count"),
    )
    return grouped


if __name__ == "__main__":
    sweep_config = load_sweep_config(CONFIG_PATH)
    run_cost_measurement_pass(sweep_config)
    table = build_cost_analysis_table()
    table.to_csv(ANALYSIS_OUTPUT, index=False)
    print(f"Wrote {len(table)} (condition, method) rows to {ANALYSIS_OUTPUT}")
