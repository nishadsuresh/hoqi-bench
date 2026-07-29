"""
Week 5 Task 4, Day 32: runs the RQ3 supplementary bidirectional-waveform
experiment specified in `docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 1
(committed BEFORE this script existed, per
`docs/WEEK5-6_EXECUTION_PLAN.md` §0.6), and compares it against the
preregistered monotonic-waveform results at matched
`hysteresis_magnitude` and method.

Pipeline position: reads `configs/supplementary_hysteresis.toml`, calls
`runner.run_condition` with `waveform_fn=waveforms.build_bidirectional_ramp`
(the one thing that differs from the preregistered campaign), writes raw
per-seed Parquet to `results/supplementary/hysteresis_bidirectional/`
(gitignored, like `results/raw/`, per this project's regenerable-raw-data
convention), aggregates via the SAME `scripts.aggregate_campaign` function
Day 27 already uses (never a second, independently-reconstructed
aggregation path), then joins against
`results/main_campaign_summary.csv` (the preregistered, immutable table)
to build the comparison. Writes `results/rq3_hysteresis_bidirectional.csv`
-- every row explicitly labeled by its two separately-named RMSE columns
(`_monotonic` / `_bidirectional`), per this project's
supplementary/preregistered separation rule.

Run as `python -m scripts.rq3_hysteresis_bidirectional` from the repo
root, NOT `python scripts/rq3_hysteresis_bidirectional.py` -- this is the
first script in `scripts/` to import from a SIBLING script
(`scripts.aggregate_campaign`), which requires the repo root on
`sys.path`; `-m` invocation provides that automatically (the same
mechanism pytest's own rootdir-insertion already relies on for
`tests/test_robustness_matrix.py`'s `scripts.robustness_matrix` import),
a bare file invocation does not.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402

from hoqi_bench.config import load_sweep_config  # noqa: E402
from hoqi_bench.resolve import iter_conditions  # noqa: E402
from hoqi_bench.runner import condition_filename, run_condition  # noqa: E402
from hoqi_bench.waveforms import build_bidirectional_ramp  # noqa: E402
from scripts.aggregate_campaign import aggregate_campaign  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "supplementary_hysteresis.toml"
RAW_OUTPUT_DIR = REPO_ROOT / "results" / "supplementary" / "hysteresis_bidirectional"
MAIN_CAMPAIGN_SUMMARY = REPO_ROOT / "results" / "main_campaign_summary.csv"
COMPARISON_OUTPUT = REPO_ROOT / "results" / "rq3_hysteresis_bidirectional.csv"


def run_bidirectional_campaign() -> None:
    """Runs every condition in the supplementary config SERIALLY (no
    ProcessPoolExecutor -- `run_condition` called directly, same pattern
    as `scripts/rq1_cost_measurement.py`; 2,800 fits is well under a
    second, so parallelism buys nothing here), with
    `waveform_fn=build_bidirectional_ramp`."""
    config = load_sweep_config(CONFIG_PATH)
    RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for condition in iter_conditions(config):
        frame = run_condition(
            condition, list(config.methods), config.n_seeds, waveform_fn=build_bidirectional_ramp
        )
        final_path = RAW_OUTPUT_DIR / condition_filename(condition.name)
        temp_path = final_path.with_suffix(".parquet.tmp")
        frame.to_parquet(temp_path, index=False)
        os.replace(temp_path, final_path)


def build_comparison_table() -> pd.DataFrame:
    """Joins the supplementary (bidirectional) summary against the
    preregistered (monotonic) summary at matched `hysteresis_magnitude`
    and method, and applies Protocol 1's pre-specified criterion.

    Every row carries which side of the join it came from via two
    explicitly-suffixed columns (`displacement_rmse_mean_m_monotonic`,
    `displacement_rmse_mean_m_bidirectional`) rather than a single stacked
    column with a provenance flag -- a stacked table risks exactly the
    "blended without an explicit label" mistake this project's Global
    Constraints warn against; two clearly-named columns cannot be
    accidentally averaged together by a later `groupby`.
    """
    bidirectional = aggregate_campaign(RAW_OUTPUT_DIR)
    monotonic_all = pd.read_csv(MAIN_CAMPAIGN_SUMMARY)
    monotonic = monotonic_all[
        monotonic_all["condition_name"].str.startswith("axis:hysteresis_magnitude=")
    ].copy()

    merged = bidirectional.merge(
        monotonic,
        on=["condition_name", "method_name"],
        suffixes=("_bidirectional", "_monotonic"),
        how="inner",
    )
    assert len(merged) == len(bidirectional), (
        "not every supplementary condition/method has a matching preregistered row -- "
        "the two configs' hysteresis_magnitude grids have diverged"
    )

    merged["rmse_difference_m"] = (
        merged["displacement_rmse_mean_m_bidirectional"]
        - merged["displacement_rmse_mean_m_monotonic"]
    )
    # Protocol 1's pre-specified criterion: direction-dependence is
    # demonstrated if the difference exceeds 1 SD of the MONOTONIC run's
    # own seed-to-seed noise -- a difference smaller than the run's own
    # measurement noise is not evidence of anything.
    merged["exceeds_monotonic_noise_floor"] = merged["rmse_difference_m"].abs() > merged[
        "displacement_rmse_std_m_monotonic"
    ].fillna(0.0)

    # A SEPARATE, EQUALLY REPORTABLE finding the RMSE criterion above
    # cannot see: a method that goes fully unusable under the
    # bidirectional waveform has `displacement_rmse_mean_m_bidirectional
    # = NaN` (aggregate.summarize's own documented behavior when zero
    # seeds succeed), which makes `exceeds_monotonic_noise_floor` silently
    # False (a NaN comparison is always False) -- reporting "no
    # difference detected" for the single most dramatic possible
    # difference. Caught by inspecting the actual per-row output, not by
    # trusting the summary count: this project's R1 finding
    # (docs/WEEK3_REVIEW.md) already established that failure/reliability
    # rates must ALWAYS be reported alongside accuracy, never folded into
    # or hidden behind it -- this is the same shape of omission, one
    # script later. `unusable_rate_difference` and
    # `bidirectional_became_unusable` make this a THIRD, independent,
    # always-visible column, never merely implied by a NaN.
    merged["unusable_rate_difference"] = (
        merged["unusable_rate_bidirectional"] - merged["unusable_rate_monotonic"]
    )
    merged["bidirectional_became_unusable"] = (merged["unusable_rate_monotonic"] < 1.0) & (
        merged["unusable_rate_bidirectional"] >= 1.0
    )

    output_columns = [
        "condition_name",
        "method_name",
        "displacement_rmse_mean_m_monotonic",
        "displacement_rmse_std_m_monotonic",
        "displacement_rmse_mean_m_bidirectional",
        "displacement_rmse_std_m_bidirectional",
        "rmse_difference_m",
        "exceeds_monotonic_noise_floor",
        "unusable_rate_monotonic",
        "unusable_rate_bidirectional",
        "unusable_rate_difference",
        "bidirectional_became_unusable",
    ]
    return merged[output_columns].sort_values(["condition_name", "method_name"])


if __name__ == "__main__":
    run_bidirectional_campaign()
    table = build_comparison_table()
    table.to_csv(COMPARISON_OUTPUT, index=False)

    n_exceeds = int(table["exceeds_monotonic_noise_floor"].sum())
    n_became_unusable = int(table["bidirectional_became_unusable"].sum())
    n_total = len(table)
    print(f"{n_exceeds}/{n_total} (condition, method) pairs exceed the RMSE noise-floor criterion")
    print(
        f"{n_became_unusable}/{n_total} (condition, method) pairs went from usable (monotonic) "
        f"to fully unusable (bidirectional) -- NOT counted in the RMSE criterion above, since a "
        f"NaN comparison is always False; reported separately so it cannot be missed"
    )
    print(f"Wrote {COMPARISON_OUTPUT}")
