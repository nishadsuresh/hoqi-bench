"""
Tests for hoqi_bench.aggregate and the Day 22 additions to
hoqi_bench.metrics.

Per docs/WEEK3-4_PLAN.md Day 22: every metric is checked against a
HAND-COMPUTED reference whose arithmetic is shown in the test's comments,
and the aggregation layer is checked on a distribution whose statistics are
known in closed form -- not against whatever the code currently returns,
which would make these change-detectors rather than tests.

The survivorship-bias behaviour (docs/WEEK3-4_PLAN.md sec0.4) and the
gross-error behaviour (docs/WEEK3_METHOD_CONTRACT.md sec2.1) get their own
sections below, since they are the reason this module exists rather than a
call to `np.mean`.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench import reference_scale
from hoqi_bench._types import FloatArray
from hoqi_bench.aggregate import (
    GROSS_ERROR_PHASE_RAD,
    MAX_UNUSABLE_RATE_FOR_RANKING,
    MethodConditionSummary,
    SeedOutcome,
    is_gross_error,
    is_rankable,
    outcome_from_fit,
    summarize,
)
from hoqi_bench.forward_model import HENE_WAVELENGTH_M
from hoqi_bench.methods.base import FitResult, failed_result
from hoqi_bench.metrics import (
    displacement_errors,
    peak_absolute_error,
    phase_error_to_displacement,
    rmse,
)

# ---- 1. Metrics, against arithmetic shown in full ----


def test_phase_error_to_displacement_matches_hand_computation() -> None:
    """phi = 4*pi*x/lambda inverts to x = phi*lambda/(4*pi).

    Hand-computed for a 1.0 rad phase error at the HeNe wavelength
    632.8e-9 m:
        x = 1.0 * 632.8e-9 / (4 * 3.14159265358979...)
          = 632.8e-9 / 12.566370614359172
          = 5.0356624e-8 m
    """
    result = phase_error_to_displacement(np.array([1.0]), HENE_WAVELENGTH_M)
    assert abs(float(result[0]) - 632.8e-9 / (4 * np.pi)) < 1e-20
    assert abs(float(result[0]) - 5.0356624e-8) < 1e-15


def test_one_full_cycle_of_phase_is_half_a_wavelength_of_displacement() -> None:
    """The double-pass factor, checked as a physical identity rather than a
    formula: 2*pi of phase must be exactly lambda/2 of mirror motion,
    because the light travels to the mirror and back. Getting the factor of
    4 wrong (a very easy 2x error) would silently halve or double every
    displacement number the benchmark reports."""
    full_cycle = phase_error_to_displacement(np.array([2 * np.pi]), HENE_WAVELENGTH_M)
    assert abs(float(full_cycle[0]) - HENE_WAVELENGTH_M / 2) < 1e-20
    assert abs(float(full_cycle[0]) - reference_scale.FULL_FRINGE_DISPLACEMENT_M) < 1e-20


def test_rmse_matches_hand_computation() -> None:
    """errors = [3, 4] ->  sqrt((9 + 16)/2) = sqrt(12.5) = 3.5355339059..."""
    assert abs(rmse(np.array([3.0, 4.0])) - np.sqrt(12.5)) < 1e-15
    assert abs(rmse(np.array([3.0, 4.0])) - 3.5355339059327378) < 1e-15


def test_peak_absolute_error_takes_the_largest_magnitude_not_the_largest_value() -> None:
    """errors = [0.1, -0.7, 0.3] -> 0.7, from the NEGATIVE entry. A `max()`
    without the absolute value would return 0.3 and understate the worst
    sample by more than 2x, which for a displacement sensor is the number
    that matters most."""
    assert peak_absolute_error(np.array([0.1, -0.7, 0.3])) == 0.7


def test_displacement_error_uses_the_wrapped_phase_difference() -> None:
    """The subtle one this module exists to get right (metrics.py's own
    docstring). True phase just below +pi, recovered just above -pi: the
    two are 0.02 rad apart, but a naive linear difference reports
    ~2*pi - 0.02.

    Hand-computed correct answer:
        wrapped error = 0.02 rad
        x = 0.02 * 632.8e-9 / (4*pi) = 1.00713...e-9 m

    The naive answer would be ~3.16e-7 m -- a factor of ~314 larger, and
    larger than the entire on-resonance motion Lehmann et al. measure.
    """
    true_phase = np.array([np.pi - 0.01])
    recovered_phase = np.array([-np.pi + 0.01])

    errors = displacement_errors(true_phase, recovered_phase, HENE_WAVELENGTH_M)

    expected = 0.02 * HENE_WAVELENGTH_M / (4 * np.pi)
    assert abs(abs(float(errors[0])) - expected) < 1e-18
    assert abs(float(errors[0])) < 1.1e-9
    assert abs(float(errors[0])) < 0.01 * reference_scale.FULL_FRINGE_DISPLACEMENT_M


# ---- 2. outcome_from_fit: the FitResult -> SeedOutcome bridge ----


def _clean_fit(n: int = 8) -> tuple[FitResult, FloatArray]:
    true_phase: FloatArray = np.linspace(0.0, 2 * np.pi, n, endpoint=False).astype(np.float64)
    return FitResult(recovered_phase=true_phase.copy(), runtime_s=0.5), true_phase


def test_outcome_from_a_perfect_fit_is_zero_error_and_not_failed() -> None:
    result, true_phase = _clean_fit()
    outcome = outcome_from_fit(result, true_phase)
    assert outcome.failed is False
    assert outcome.reason is None
    assert outcome.displacement_rmse_m == 0.0
    assert outcome.phase_rmse_rad == 0.0
    assert outcome.runtime_s == 0.5


def test_outcome_from_a_failed_fit_is_all_nan_never_zero() -> None:
    """docs/WEEK3_METHOD_CONTRACT.md sec2, one level down: a failed seed
    must not contribute a 0.0 that silently IMPROVES a mean. NaN is the
    only safe value here, and it is checked explicitly because 0.0 is
    exactly what a careless implementation would produce."""
    outcome = outcome_from_fit(failed_result(8, "non_convergent", converged=False), np.zeros(8))
    assert outcome.failed is True
    assert outcome.reason == "non_convergent"
    assert np.isnan(outcome.displacement_rmse_m)
    assert np.isnan(outcome.peak_absolute_error_m)
    assert np.isnan(outcome.phase_rmse_rad)
    assert outcome.converged is False


def test_gross_error_requires_claiming_success() -> None:
    """A failed seed is never ALSO a gross error -- it is already counted
    in failure_rate, and double-counting would let unusable_rate exceed
    1.0."""
    claimed_success = SeedOutcome(False, None, 1e-7, 1e-7, 1.0, 0.1, None)
    honestly_failed = SeedOutcome(True, "non_convergent", float("nan"), float("nan"),
                                  float("nan"), 0.1, False)
    fine = SeedOutcome(False, None, 1e-12, 1e-12, 0.001, 0.1, None)

    assert is_gross_error(claimed_success) is True
    assert is_gross_error(honestly_failed) is False
    assert is_gross_error(fine) is False


# ---- 3. Aggregation, on a distribution with known statistics ----


def _outcome(rmse_m: float, *, failed: bool = False, phase_rmse: float = 0.001,
             converged: bool | None = None) -> SeedOutcome:
    if failed:
        return SeedOutcome(True, "non_convergent", float("nan"), float("nan"),
                           float("nan"), 0.1, converged)
    return SeedOutcome(False, None, rmse_m, rmse_m * 2, phase_rmse, 0.1, converged)


def test_summary_statistics_match_a_known_distribution() -> None:
    """Seeds with displacement RMSEs 1..9 nm (a distribution whose mean,
    median and std are known in closed form):
        mean   = (1+2+...+9)/9 = 45/9 = 5 nm
        median = 5 nm
        std    = sqrt(mean((x-5)^2)) = sqrt((16+9+4+1+0+1+4+9+16)/9)
               = sqrt(60/9) = sqrt(6.6667) = 2.5819888... nm
    """
    outcomes = [_outcome(i * 1e-9) for i in range(1, 10)]
    summary = summarize("kasa", "axis:noise_std=0.0", outcomes)

    assert summary.n_seeds == 9
    assert abs(summary.displacement_rmse_mean_m - 5e-9) < 1e-24
    assert abs(summary.displacement_rmse_median_m - 5e-9) < 1e-24
    assert abs(summary.displacement_rmse_std_m - np.sqrt(60 / 9) * 1e-9) < 1e-24
    assert abs(summary.displacement_rmse_std_m - 2.5819888974716116e-9) < 1e-20
    # peak absolute error is 2x the rmse in _outcome, so its mean is 10 nm
    assert abs(summary.peak_absolute_error_mean_m - 10e-9) < 1e-23


def test_percentiles_match_numpys_linear_interpolation_convention() -> None:
    """Seeds 1..9 nm again. numpy's default percentile is linear
    interpolation on the order statistics, so for n=9:
        p05 -> index 0.05*(9-1) = 0.4  -> 1 + 0.4*(2-1) = 1.4 nm
        p95 -> index 0.95*(9-1) = 7.6  -> 8 + 0.6*(9-8) = 8.6 nm
    Pinned explicitly because a future switch of interpolation convention
    would silently move every reported CI edge."""
    summary = summarize("kasa", "c", [_outcome(i * 1e-9) for i in range(1, 10)])
    # 1e-23, not 1e-24: 8.6e-9 is not exactly representable in binary, and
    # numpy's interpolation lands one ulp away from the literal. Tightening
    # past a representable difference tests float layout, not the code.
    assert abs(summary.displacement_rmse_p05_m - 1.4e-9) < 1e-23
    assert abs(summary.displacement_rmse_p95_m - 8.6e-9) < 1e-23


def test_accuracy_statistics_exclude_failed_seeds_entirely() -> None:
    """The sec0.4 behaviour, stated as a number: 4 usable seeds at 1..4 nm
    plus 6 failures must give a mean of (1+2+3+4)/4 = 2.5 nm -- NOT
    (1+2+3+4)/10 = 1.0 nm (treating failures as zero, which would make a
    method look BETTER the more often it failed) and not NaN."""
    outcomes = [_outcome(i * 1e-9) for i in range(1, 5)] + [_outcome(0.0, failed=True)] * 6
    summary = summarize("koning_wimmer_witkovsky", "axis:arc_fraction=0.02", outcomes)

    assert summary.n_seeds == 10
    assert summary.n_failed == 6
    assert summary.failure_rate == 0.6
    assert abs(summary.displacement_rmse_mean_m - 2.5e-9) < 1e-24


def test_all_seeds_failing_is_reported_not_raised() -> None:
    """A 100%-failure condition is a real, reportable outcome -- the
    accuracy fields go NaN and the failure rate goes to 1.0, rather than
    the summary being dropped (which would make the method silently
    disappear from that condition, the exact thing
    docs/WEEK3_METHOD_CONTRACT.md sec2 forbids)."""
    summary = summarize("heydemann", "axis:arc_fraction=0.02", [_outcome(0.0, failed=True)] * 5)
    assert summary.failure_rate == 1.0
    assert summary.unusable_rate == 1.0
    assert np.isnan(summary.displacement_rmse_mean_m)


def test_three_reliability_rates_are_reported_and_consistent() -> None:
    """docs/WEEK3_METHOD_CONTRACT.md sec2.1: failure and gross-error are
    counted separately and sum to unusable. 2 failures + 3 gross errors out
    of 10 -> 0.2, 0.3, 0.5."""
    outcomes = (
        [_outcome(0.0, failed=True)] * 2
        + [_outcome(1e-7, phase_rmse=GROSS_ERROR_PHASE_RAD + 0.1)] * 3
        + [_outcome(1e-12)] * 5
    )
    summary = summarize("fitzgibbon", "c", outcomes)
    assert summary.failure_rate == 0.2
    assert summary.gross_error_rate == 0.3
    assert summary.unusable_rate == 0.5


def test_convergence_rate_is_none_for_non_iterative_methods() -> None:
    """`converged=None` means "convergence does not apply", which is a
    different fact from "did not converge" (methods/base.py). A
    non-iterative method must not be reported as 100% convergent, which
    would imply the concept applies to it."""
    assert summarize("kasa", "c", [_outcome(1e-9) for _ in range(5)]).convergence_rate is None

    iterative = [_outcome(1e-9, converged=True)] * 3 + [_outcome(0.0, failed=True, converged=False)]
    assert summarize("koning_wimmer_witkovsky", "c", iterative).convergence_rate == 0.75


# ---- 4. The ranking gate ----


def _summary(name: str, unusable: float) -> MethodConditionSummary:
    return MethodConditionSummary(
        method_name=name, condition_name="c", n_seeds=50, n_failed=0, n_gross_error=0,
        failure_rate=0.0, gross_error_rate=unusable, unusable_rate=unusable,
        convergence_rate=None, displacement_rmse_mean_m=1e-9,
        displacement_rmse_median_m=1e-9, displacement_rmse_std_m=0.0,
        displacement_rmse_p05_m=1e-9, displacement_rmse_p95_m=1e-9,
        peak_absolute_error_mean_m=1e-9, phase_rmse_mean_rad=0.001, runtime_s_mean=0.1,
    )


def test_condition_is_rankable_when_every_method_is_below_the_threshold() -> None:
    assert is_rankable([_summary("a", 0.0), _summary("b", 0.1), _summary("c", 0.2)]) is True


def test_one_bad_method_makes_the_whole_condition_unrankable() -> None:
    """All-or-nothing, per is_rankable's docstring: dropping the offending
    method and ranking the rest leaves exactly the flattering-by-attrition
    artifact the gate exists to prevent, on the remaining pairs."""
    assert is_rankable([_summary("a", 0.0), _summary("b", 0.0),
                        _summary("c", MAX_UNUSABLE_RATE_FOR_RANKING + 0.01)]) is False


def test_the_gate_triggers_on_silent_gross_errors_not_only_self_reported_failures() -> None:
    """The sec2.1 strengthening, as a test. A method with NO failure mode
    self-reports 0% forever; under sec0.4's literal wording it could never
    trigger the gate however much garbage it emitted. Here it has a 0%
    failure rate and a 40% gross-error rate, and the condition must still
    come out unrankable."""
    silently_wrong = MethodConditionSummary(
        method_name="fitzgibbon", condition_name="c", n_seeds=50, n_failed=0, n_gross_error=20,
        failure_rate=0.0, gross_error_rate=0.4, unusable_rate=0.4, convergence_rate=None,
        displacement_rmse_mean_m=1e-9, displacement_rmse_median_m=1e-9,
        displacement_rmse_std_m=0.0, displacement_rmse_p05_m=1e-9,
        displacement_rmse_p95_m=1e-9, peak_absolute_error_mean_m=1e-9,
        phase_rmse_mean_rad=0.001, runtime_s_mean=0.1,
    )
    assert silently_wrong.failure_rate == 0.0
    assert is_rankable([_summary("a", 0.0), silently_wrong]) is False


# ---- 5. The physical reference scale ----


def test_the_preregistered_tolerance_is_coarser_than_the_measured_motion() -> None:
    """reference_scale.py's headline claim, as a test rather than a
    sentence: 1% of a full fringe is 3.16 nm, which is LARGER than the
    on-resonance motion Lehmann et al. 2025 report ("always less than 5 nm,
    and often even below 1 nm", Section III.3). A method that merely
    satisfies the preregistered tolerance is not usable for the reference
    application, and Week 4's reporting has to say so."""
    assert abs(reference_scale.PREREGISTERED_TOLERANCE_M - 3.164e-9) < 1e-12
    assert reference_scale.PREREGISTERED_TOLERANCE_M > reference_scale.TYPICAL_MEASURED_MOTION_M
    ratio = reference_scale.PREREGISTERED_TOLERANCE_M / reference_scale.INSTRUMENT_NOISE_FLOOR_M
    assert 30_000 < ratio < 33_000, f"tolerance is {ratio:.0f}x the instrument noise floor"


def test_error_bands_classify_in_the_documented_order() -> None:
    classify = reference_scale.classify_displacement_error
    assert classify(1e-15) == "negligible"
    assert classify(1e-13) == "negligible"
    assert classify(5e-12) == "usable"
    assert classify(5e-10) == "marginal"
    assert classify(reference_scale.PREREGISTERED_TOLERANCE_M) == "unusable"
    assert classify(float("nan")) == "unusable"
