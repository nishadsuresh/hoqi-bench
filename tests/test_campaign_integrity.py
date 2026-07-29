"""
Campaign-integrity guards against the Week 5 pre-flight audit's defect
class: a preregistered axis, metric, or research question that LOOKS
covered by a green test suite and a passing config validator, but is
actually unanswerable, unmeasured, or misconfigured, discoverable only by
executing the campaign and reading the actual numbers.

Why this exists (docs/WEEK5_PREFLIGHT_AUDIT.md, 2026-07-28): four defects
(RQ3's hysteresis axis never activating direction-dependence; RQ6's grid
having no N x noise interaction; the cost metric never being populated;
RQ5's grid never reaching many-fringe) all survived the Weeks 1-2 audit,
two llm-council reviews, the OSF timestamp, Day 21's cross-validation
gate, the Week 3 review, and all of Week 4 -- because none of those
processes checked this specific thing: does the preregistered GRID
actually have the statistical leverage to answer the RESEARCH QUESTION it
was built for. This module is the permanent fix, so the defect class
cannot silently reappear the next time a config or research question
changes.

Pipeline position: runs against `configs/main_campaign.toml` and
`results/main_campaign_summary.csv` (both preregistered, both frozen --
see docs/WEEK5-6_EXECUTION_PLAN.md's "preregistered data is immutable"
constraint). Two tests are expected to `xfail` against the preregistered
config specifically, flipping to pass only against a supplementary config
built in a later Week 5 task -- an `xfail` that documents a known, dated,
recorded defect is honest; deleting the test or loosening it to pass
would not be.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from hoqi_bench.config import load_sweep_config
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import WaveformGenerator, simulate_condition

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_CAMPAIGN_CONFIG = REPO_ROOT / "configs" / "main_campaign.toml"
MAIN_CAMPAIGN_SUMMARY = REPO_ROOT / "results" / "main_campaign_summary.csv"

# ---- 1. Per-axis response floors -----------------------------------------
# Why a PER-AXIS table, not one global threshold (measured 2026-07-28,
# docs/WEEK5-6_EXECUTION_PLAN.md Task 1.3): the max-across-methods dynamic
# range spans 1.10x (samples_per_fit, the P2 defect) to 4299.79x
# (arc_fraction). A single global threshold would have to sit strictly
# between 1.10x and dc_offset's 2.81x -- and dc_offset's 2.81x comes
# ENTIRELY from raw_atan2; every method that actually corrects dc_offset
# measures 1.00-1.11x there, which is the CORRECT, structurally-predicted
# behavior (docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md's Category 1
# tautological prediction), not a defect. A global floor above ~1.11x
# would therefore fail a healthy axis; a global floor below ~1.10x
# would not have caught P2 at all. Per-axis floors, each with margin
# against its own measured value, are the only threshold shape that
# distinguishes "this axis is broken" from "these methods are excellent
# here" -- which is exactly the distinction this guard exists to make.
#
# Table values are ~80% of the measured max-across-methods dynamic range
# (2026-07-28, results/main_campaign_summary.csv), giving margin against
# ordinary seed-to-seed / measurement noise while still failing loudly if
# an axis collapses toward 1x. dc_offset is the axis where a correcting
# method's OWN dynamic range is expected to be near 1x by construction --
# its floor is set from raw_atan2 (the one method with no structural
# reason to be flat) rather than from the correcting methods, and is
# annotated accordingly. samples_per_fit's floor is set BELOW its
# measured value, deliberately, since it is the known defect itself --
# see the comment at that entry.
_AXIS_RESPONSE_FLOOR = {
    "arc_fraction": 3000.0,  # measured max 4299.79x (any method)
    "noise_std": 200.0,  # measured max 310.02x
    "amplitude_ratio": 140.0,  # measured max 179.71x
    "photon_scale": 25.0,  # measured max 36.57x
    "hysteresis_magnitude": 25.0,  # measured max 33.88x
    "quadrature_error_rad": 7.0,  # measured max 9.53x
    # dc_offset: floor set from raw_atan2 (2.81x measured), the only
    # method with no structural correction for a DC offset. Every
    # conic/circle fitter is EXPECTED near 1x here (Category 1/2
    # predictions) -- that is not this axis failing, so the floor is not
    # raised to match the broken-axis shape below.
    "dc_offset": 2.0,
    # samples_per_fit: THE axis this guard exists to catch. Measured max
    # 1.0957x (2026-07-28, halir_flusser/fitzgibbon) -- this floor is set
    # just below that measured value, deliberately, so the corresponding
    # test passes-while-documenting the defect against the preregistered
    # config today, and starts FAILING (correctly) the moment a real
    # noise x N interaction pushes the dynamic range meaningfully above
    # its current floor-level value -- the inverse of every other row in
    # this table, matching test_samples_per_fit_axis_is_a_known_recorded_defect
    # below, which asserts the same fact from the opposite direction.
    "samples_per_fit": 1.05,
}


def _load_axis_pivot(axis: str) -> pd.DataFrame:
    summary = pd.read_csv(MAIN_CAMPAIGN_SUMMARY)
    rows = summary[summary["condition_name"].str.startswith(f"axis:{axis}=")].copy()
    return rows.pivot_table(
        index="condition_name", columns="method_name", values="displacement_rmse_mean_m"
    )


@pytest.mark.parametrize("axis", sorted(_AXIS_RESPONSE_FLOOR))
def test_every_swept_axis_meets_its_committed_response_floor(axis: str) -> None:
    """Guards against a config change silently flattening a preregistered
    axis's DYNAMIC RANGE -- the shape of defect P2 (samples_per_fit swept
    entirely at zero noise, producing a near-flat response nobody
    flagged). This is a regression guard, not the primary defense against
    P2 itself -- see test_every_research_question_has_a_grid_that_can_answer_it
    below for the guard that would have caught P2 BEFORE the campaign ran,
    by checking grid coverage rather than the resulting numbers.

    samples_per_fit is intentionally left failing (xfail below) against
    the preregistered config, per docs/PREREGISTRATION.md deviation D6.
    """
    pivot = _load_axis_pivot(axis)
    dynamic_range = float((pivot.max() / pivot.min()).max())
    floor = _AXIS_RESPONSE_FLOOR[axis]
    assert dynamic_range >= floor, (
        f"axis:{axis} dynamic range across methods dropped to {dynamic_range:.2f}x, "
        f"below the committed floor of {floor}x -- see this module's docstring table "
        f"for how the floor was calibrated, and docs/WEEK5_PREFLIGHT_AUDIT.md for the "
        f"defect class this guards against"
    )


def test_samples_per_fit_axis_is_a_known_recorded_defect() -> None:
    """samples_per_fit's own dynamic range (1.10x, measured) sits AT its
    committed floor by construction, not above it with margin like every
    other axis -- because the axis genuinely has no noise to average over
    in the preregistered config (docs/PREREGISTRATION.md deviation D6).
    This test exists so that fact is asserted explicitly, rather than the
    parametrized test above silently "passing" a defect that happens to
    sit exactly on its own floor.
    """
    pivot = _load_axis_pivot("samples_per_fit")
    dynamic_range = float((pivot.max() / pivot.min()).max())
    assert dynamic_range < 1.5, (
        "samples_per_fit's dynamic range moved meaningfully above the recorded "
        "1.10x defect value -- if a supplementary noise x N grid has been added, "
        "this test (and D6) should be updated to reflect the fix, not silently "
        "left describing a defect that no longer exists"
    )


# ---- 2. Hysteresis direction-of-travel guard ------------------------------


SUPPLEMENTARY_HYSTERESIS_CONFIG = REPO_ROOT / "configs" / "supplementary_hysteresis.toml"


def _hysteresis_axis_reverses_direction(
    config_path: Path, waveform_fn: WaveformGenerator | None = None
) -> bool:
    """Shared check both the preregistered-config (expected xfail) and
    supplementary-config (expected pass) tests below use, so the two
    cannot silently diverge in what they actually check."""
    config = load_sweep_config(config_path)
    conditions = {c.name: c for c in iter_conditions(config)}
    hysteresis_conditions = [
        c for name, c in conditions.items() if name.startswith("axis:hysteresis_magnitude=")
    ]
    assert hysteresis_conditions, f"no hysteresis_magnitude conditions found in {config_path}"

    for condition in hysteresis_conditions:
        if condition.resolved["hysteresis_magnitude"] <= 0.0:
            continue  # magnitude=0 is hysteresis's own identity case; no direction to reverse
        signal = (
            simulate_condition(condition.resolved, condition.name, 0, waveform_fn=waveform_fn)
            if waveform_fn is not None
            else simulate_condition(condition.resolved, condition.name, 0)
        )
        direction_signs = set(
            pd.Series(signal.x_true)
            .diff()
            .dropna()
            .apply(lambda d: 1 if d > 0 else (-1 if d < 0 else 0))
        )
        if -1 in direction_signs and 1 in direction_signs:
            return True
    return False


def test_hysteresis_axis_actually_reverses_direction() -> None:
    """Guards against defect P1: `transforms.hysteresis` derives direction
    of travel from `sign(gradient(true_displacement))`, but every
    preregistered campaign waveform (`arc.build_arc_ramp`) is strictly
    monotonic, so the direction never reverses and the direction-dependent
    branch is dead code for the entire campaign (docs/PREREGISTRATION.md
    deviation D5).

    Marked `xfail` against the preregistered config -- this is a KNOWN,
    DATED, RECORDED defect (D5), not an oversight to silently patch here.
    See `test_supplementary_hysteresis_config_actually_reverses_direction`
    below for the sibling check confirming the FIX exists and works,
    against Task 4's supplementary bidirectional-waveform config.
    """
    if not _hysteresis_axis_reverses_direction(MAIN_CAMPAIGN_CONFIG):
        pytest.xfail(
            "known defect, docs/PREREGISTRATION.md deviation D5: every campaign "
            "waveform is monotonic, so hysteresis direction never reverses -- "
            "the preregistered campaign measures static radial inflation, not "
            "path-dependent hysteresis. Fixed for the SUPPLEMENTARY experiment "
            "only, per D5 -- see test_supplementary_hysteresis_config_actually_"
            "reverses_direction. The preregistered campaign itself is never "
            "re-run to fix this (that would be exactly the forking-paths move "
            "docs/WEEK5-6_EXECUTION_PLAN.md §0.6 exists to prevent)."
        )


def test_supplementary_hysteresis_config_actually_reverses_direction() -> None:
    """The other half of P1's fix (Week 5 Task 4, Day 32): confirms
    `waveforms.build_bidirectional_ramp`, used by
    `configs/supplementary_hysteresis.toml` via
    `scripts/rq3_hysteresis_bidirectional.py`, actually produces direction
    reversal where the preregistered campaign's monotonic waveform does
    not. This is expected to PASS, unlike the sibling test above --
    if it starts failing, the supplementary experiment has stopped
    testing what it claims to test.
    """
    from hoqi_bench.waveforms import build_bidirectional_ramp

    assert _hysteresis_axis_reverses_direction(
        SUPPLEMENTARY_HYSTERESIS_CONFIG, waveform_fn=build_bidirectional_ramp
    )


# ---- 3. Preregistered-metric population guard -----------------------------

# Metric -> minimum acceptable non-null fraction, measured AMONG ROWS
# WHERE unusable_rate < 1.0 -- a condition where every seed fails has a
# legitimately undefined mean displacement/phase error (there is nothing
# to average), which is real and expected (R1, docs/WEEK3_REVIEW.md;
# measured 2026-07-28: 93 of 2,513 rows are unusable_rate==1.0, and
# EVERY null displacement_rmse_mean_m/phase_rmse_mean_rad row coincides
# exactly with one of those 93 -- confirmed before writing this floor,
# not assumed). Restricting the denominator to usable rows is what lets
# this test tell that apart from defect P3's shape (an instrumentation
# path that never populates ANY row, usable or not, and fails silently
# rather than raising). cost (runtime_s_mean) is P3 itself and is
# checked separately below, deliberately, rather than folded into this
# floor.
_METRIC_POPULATION_FLOOR = {
    "displacement_rmse_mean_m": 0.99,
    "phase_rmse_mean_rad": 0.99,
    "failure_rate": 0.99,
    "gross_error_rate": 0.99,
    "unusable_rate": 0.99,
}


@pytest.mark.parametrize("metric", sorted(_METRIC_POPULATION_FLOOR))
def test_every_preregistered_metric_is_populated(metric: str) -> None:
    """Guards against a preregistered metric silently going unmeasured --
    the general shape of defect P3 (`runtime_s` null in 100% of rows,
    degrading silently through `aggregate.py`'s `NaN`-on-empty-list
    fallback rather than raising). Checked against every metric
    PREREGISTRATION.md's Metrics section names, except cost, which is
    checked separately below because it is the metric already KNOWN to
    fail this check (docs/WEEK3_METHOD_CONTRACT.md's Day 29 defect
    report) -- asserting it here would either be a no-op floor or a
    permanently-red test, neither of which is useful.
    """
    summary = pd.read_csv(MAIN_CAMPAIGN_SUMMARY)
    usable = summary[summary["unusable_rate"] < 1.0]
    non_null_fraction = usable[metric].notna().mean()
    floor = _METRIC_POPULATION_FLOOR[metric]
    assert non_null_fraction >= floor, (
        f"{metric} is only {non_null_fraction:.1%} populated among USABLE "
        f"conditions (unusable_rate < 1.0) in main_campaign_summary.csv, below "
        f"the {floor:.0%} floor -- a preregistered metric may be silently "
        f"failing to record, the shape of defect P3 (docs/WEEK5_PREFLIGHT_AUDIT.md)"
    )


def test_cost_metric_population_matches_its_recorded_state() -> None:
    """States defect P3 explicitly and fails loudly the moment it is
    fixed without this test being updated -- the inverse of the usual
    guard, deliberately. `docs/WEEK3_METHOD_CONTRACT.md`'s Day 29 defect
    report records `runtime_s_mean` as 100% null pending Task 3's fix
    (a serial timing pass, since the parallel campaign's wall-clock
    measurements are not a clean cost signal). If this ever starts
    passing with actual data, docs/WEEK3_METHOD_CONTRACT.md and this
    test must be updated together, not left silently describing a fixed
    defect as current.
    """
    summary = pd.read_csv(MAIN_CAMPAIGN_SUMMARY)
    non_null_fraction = summary["runtime_s_mean"].notna().mean()
    assert non_null_fraction == 0.0, (
        "runtime_s_mean is no longer 100% null in the PREREGISTERED (parallel) "
        "campaign summary -- if Task 3's serial timing pass has been merged into "
        "the main runner rather than kept as a separate supplementary pass, update "
        "this test AND docs/WEEK3_METHOD_CONTRACT.md's Day 29 defect report to "
        "reflect the fix rather than leaving them describing a resolved defect"
    )


# ---- 4. Research-question-to-grid coverage guard --------------------------

# Declarative RQ -> required config coverage. This is the guard that would
# have caught P2 BEFORE the campaign ran: not "does the axis produce a
# response" (test 1, above) but "does the GRID have the statistical
# leverage this specific research question needs." RQ6 needs an N x noise
# INTERACTION, which is a structurally different requirement than "N is a
# swept axis" -- the preregistered config satisfies the latter and fails
# the former.
_RQ_REQUIRED_AXES: dict[str, set[str]] = {
    "RQ1": {
        "amplitude_ratio",
        "quadrature_error_rad",
        "dc_offset",
        "arc_fraction",
        "noise_std",
    },
    "RQ2": {"amplitude_ratio", "arc_fraction"},
    "RQ3": {"hysteresis_magnitude"},
    "RQ4": {"photon_scale", "noise_std"},
    "RQ5": {"arc_fraction", "noise_std"},
}

# RQ -> required INTERACTION grid, expressed as the pair of axes that must
# appear together in some `[grids.*]` table. RQ6 requires samples_per_fit
# x noise_std, which the preregistered config does not have.
_RQ_REQUIRED_INTERACTIONS: dict[str, frozenset[str]] = {
    "RQ6": frozenset({"samples_per_fit", "noise_std"}),
}


@pytest.mark.parametrize("rq", sorted(_RQ_REQUIRED_AXES))
def test_every_research_question_has_its_required_axes(rq: str) -> None:
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    required = _RQ_REQUIRED_AXES[rq]
    missing = required - set(config.axes)
    assert not missing, f"{rq} requires axes {missing}, absent from configs/main_campaign.toml"


SUPPLEMENTARY_N_X_NOISE_CONFIG = REPO_ROOT / "configs" / "supplementary_n_x_noise.toml"


def _has_n_x_noise_interaction(config_path: Path) -> bool:
    config = load_sweep_config(config_path)
    required_pair = _RQ_REQUIRED_INTERACTIONS["RQ6"]
    return any(required_pair <= set(grid_axes) for grid_axes in config.grids.values())


def test_rq6_requires_a_grid_the_preregistered_config_does_not_have() -> None:
    """THE guard against P2, stated as directly as possible: RQ6 needs a
    `samples_per_fit x noise_std` interaction grid, which does not exist
    in `configs/main_campaign.toml` (docs/PREREGISTRATION.md deviation
    D6). Marked `xfail` -- this is a known, dated, recorded defect. See
    `test_supplementary_n_x_noise_config_has_the_required_interaction`
    below for the sibling check confirming the FIX exists, against Week
    5 Task 6's supplementary config.
    """
    if not _has_n_x_noise_interaction(MAIN_CAMPAIGN_CONFIG):
        pytest.xfail(
            "known defect, docs/PREREGISTRATION.md deviation D6: no "
            "samples_per_fit x noise_std interaction grid exists in the "
            "preregistered config, so RQ6's N-vs-noise design chart cannot be "
            "produced. Fixed for the SUPPLEMENTARY experiment only, per D6 -- "
            "see test_supplementary_n_x_noise_config_has_the_required_interaction. "
            "The preregistered campaign itself is never re-run to fix this."
        )


def test_supplementary_n_x_noise_config_has_the_required_interaction() -> None:
    """The other half of P2's fix (Week 5 Task 6, Day 34): confirms
    `configs/supplementary_n_x_noise.toml` actually has the
    samples_per_fit x noise_std interaction grid the preregistered config
    lacks. Expected to PASS, unlike the sibling test above -- if it
    starts failing, the supplementary config has stopped providing what
    it claims to."""
    assert _has_n_x_noise_interaction(SUPPLEMENTARY_N_X_NOISE_CONFIG)


# ---- 5. Preregistered/supplementary provenance guard ----------------------


def test_preregistered_results_tree_has_not_been_touched_by_supplementary_runs() -> None:
    """Guards the plan's own constraint (docs/WEEK5-6_EXECUTION_PLAN.md,
    Global Constraints): `results/raw/` and `results/main_campaign_summary.csv`
    are read-only for the rest of the project. A supplementary run must
    write to `results/supplementary/<experiment_name>/`, a physically
    separate tree, so a directory-configuration mistake (a script's
    OUTPUT_DIR accidentally pointed at `results/raw/` itself, or nested
    inside it) cannot silently overwrite or blend into the preregistered
    data.

    Design decision: does NOT require `results/raw/` to exist (its
    contents are gitignored -- a fresh clone legitimately has no
    `results/raw/` directory; an earlier version of this test asserted
    `raw_dir.is_dir()` unconditionally and failed in CI for exactly this
    reason, `docs/journal/day29.md`).

    Design decision, REVISED Day 31 (`docs/journal/day31.md`): an earlier
    version of this test also asserted no `*.parquet` FILENAME may appear
    in both `results/raw/` and `results/supplementary/`. That was wrong,
    caught by real usage: Day 31's `scripts/rq1_cost_measurement.py`
    deliberately re-runs several of the SAME preregistered conditions
    (same condition names, hence the same filenames via
    `runner.condition_filename`) into `results/supplementary/
    cost_measurement/`, by design -- measuring cost under a different
    execution mode (serial vs. parallel) for the identical preregistered
    input. That is exactly the point of a supplementary cost pass, not a
    bug, and it is completely safe: the two files live in two DIFFERENT,
    NON-NESTED directories, so no reader that globs a specific directory
    (which is how `load_results` and every script in this project reads
    results) could ever confuse them. A shared BASENAME across separate
    directories was never the actual risk this test's docstring names --
    a script writing INTO `results/raw/` is. Checked directly below
    instead: the two trees are distinct paths and neither is nested
    inside the other, which is what a misconfigured OUTPUT_DIR would
    violate.

    Whether an individual supplementary analysis script correctly adds a
    provenance column before blending its own output with preregistered
    data is checked per-script in the tasks that write those analyses
    (Week 5 Tasks 4 and 6), since a generic static check cannot verify a
    script's own pandas logic.
    """
    raw_dir = (REPO_ROOT / "results" / "raw").resolve()
    supplementary_dir = (REPO_ROOT / "results" / "supplementary").resolve()
    assert raw_dir != supplementary_dir
    assert supplementary_dir not in raw_dir.parents
    assert raw_dir not in supplementary_dir.parents
