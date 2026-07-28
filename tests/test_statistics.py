"""
Tests for hoqi_bench.statistics -- Day 25's bootstrap CI, breakdown-threshold
detection, and Bonferroni correction, per docs/PREREGISTRATION.md's
Statistical protocol section, implemented EXACTLY as specified there --
`docs/WEEK3-4_PLAN.md` Day 25's hard rule: no statistical test not
preregistered, and anything that looks missing gets flagged for Nishi, not
added.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench.statistics import (
    BONFERRONI_FAMILY_SIZE,
    bootstrap_ci,
    breakdown_threshold,
    corrected_alpha,
    pairwise_comparisons,
)


def test_breakdown_threshold_on_a_hand_computed_crossing() -> None:
    """Grid [1.0, 1.1, 1.2], errors [1e-9, 2e-9, 6e-9], tolerance 3e-9.
    The crossing lies between 1.1 (2e-9, below) and 1.2 (6e-9, above).
    Linear interpolation: the tolerance is (3e-9 - 2e-9) / (6e-9 - 2e-9)
    = 0.25 of the way from 1.1 to 1.2, so the threshold is
    1.1 + 0.25 * 0.1 = 1.125. Computed by hand, not by running the code."""
    result = breakdown_threshold([1.0, 1.1, 1.2], [1e-9, 2e-9, 6e-9], 3e-9)
    assert result.status == "found"
    assert result.value is not None
    assert abs(result.value - 1.125) < 1e-12


def test_breakdown_threshold_reports_no_breakdown_when_never_exceeded() -> None:
    """A method that stays under tolerance across the whole swept range
    -- the MORE common case for this benchmark's near-ceiling conic
    fitters (docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md), and the case the
    original plan's `float | None` interface didn't distinguish from
    'broken at the first point' (llm-council, Day 25: both collapsing to
    None/NaN is exactly the ambiguity this gate exists to prevent).
    Reported via a status DISTINCT from the broken-at-start case."""
    result = breakdown_threshold([1.0, 1.1, 1.2], [1e-9, 1e-9, 1e-9], 3e-9)
    assert result.status == "no_breakdown_in_range"
    assert result.value is None


def test_breakdown_threshold_reports_broken_at_start_distinctly() -> None:
    """raw_atan2 will be above tolerance from the first point on several
    axes. Per the llm-council resolution (Day 25, all 5 advisors and all
    5 peer reviews converged this needs a status DISTINCT from both
    'found' and 'no_breakdown_in_range' -- not the first grid value as a
    bare float, which reads identically to a real interpolated crossing,
    and not None, which is indistinguishable from 'never breaks down'."""
    result = breakdown_threshold([1.0, 1.1, 1.2], [9e-9, 9e-9, 9e-9], 3e-9)
    assert result.status == "broken_at_start"
    assert result.value is None


def test_breakdown_threshold_on_a_second_hand_computed_crossing() -> None:
    """A different grid spacing and a crossing later in the range, so the
    first test's numbers can't accidentally validate a formula that only
    happens to work for one specific case. Grid [0.0, 0.02, 0.05, 0.1],
    errors [1e-10, 2e-10, 5e-10, 12e-10], tolerance 8e-10. The crossing is
    between 0.05 (5e-10, below) and 0.1 (12e-10, above): fraction =
    (8e-10 - 5e-10) / (12e-10 - 5e-10) = 3/7. Threshold =
    0.05 + (3/7) * (0.1 - 0.05) = 0.05 + 3/7 * 0.05 = 0.0714285714..."""
    result = breakdown_threshold([0.0, 0.02, 0.05, 0.1], [1e-10, 2e-10, 5e-10, 12e-10], 8e-10)
    assert result.status == "found"
    assert result.value is not None
    assert abs(result.value - (0.05 + (3 / 7) * 0.05)) < 1e-12


def test_breakdown_threshold_log_scale_on_a_hand_computed_crossing() -> None:
    """arc_fraction's grid is log-spaced (llm-council, Day 25: unanimous
    across all 5 advisors that interpolation must match the grid's own
    design -- log for arc_fraction, linear for amplitude_ratio). Grid
    [1.0, 0.5, 0.25], errors [1e-9, 2e-9, 8e-9], tolerance 4e-9. In LOG
    space: log(1.0)=0, log(0.5)=-0.6931..., log(0.25)=-1.3862...
    Crossing between 0.5 (2e-9, below) and 0.25 (8e-9, above): fraction =
    (4e-9-2e-9)/(8e-9-2e-9) = 1/3. log(threshold) =
    log(0.5) + (1/3)*(log(0.25)-log(0.5)) = -0.6931 + (1/3)*(-0.6931)
    = -0.9241..., threshold = exp(-0.9241...) = 0.39685..."""
    import math

    result = breakdown_threshold([1.0, 0.5, 0.25], [1e-9, 2e-9, 8e-9], 4e-9, log_scale=True)
    assert result.status == "found"
    assert result.value is not None
    expected = math.exp(math.log(0.5) + (1 / 3) * (math.log(0.25) - math.log(0.5)))
    assert abs(result.value - expected) < 1e-9
    assert abs(result.value - 0.39685) < 1e-4


def test_bootstrap_ci_brackets_a_known_mean() -> None:
    """A percentile bootstrap on 50 draws from N(mu=5, sigma=1) must
    bracket mu comfortably, and must be reproducible from its seed."""
    rng = np.random.default_rng(0)
    values = rng.normal(5.0, 1.0, 50)

    low, high = bootstrap_ci(values, seed=42)
    assert low < 5.0 < high
    assert high - low < 1.0  # 50 samples of unit sigma -> CI width ~0.55

    assert bootstrap_ci(values, seed=42) == (low, high)  # deterministic
    assert bootstrap_ci(values, seed=43) != (low, high)  # genuinely resampling


def test_bootstrap_ci_on_a_degenerate_single_value() -> None:
    """All-identical values (e.g. every seed hit the exact same failure)
    must produce a zero-width CI at that value, not NaN or an error --
    every resample is identical to the input, so the mean is always the
    same constant."""
    low, high = bootstrap_ci(np.full(50, 3.0), seed=0)
    assert low == 3.0
    assert high == 3.0


def test_bonferroni_family_size_matches_the_preregistration() -> None:
    """docs/PREREGISTRATION.md: '21 pairwise comparisons per condition for
    7 methods' -- 7 choose 2 = 21, hand-computed, not derived from the
    constant itself."""
    assert BONFERRONI_FAMILY_SIZE == 21


def test_corrected_alpha_matches_the_preregistration() -> None:
    """docs/PREREGISTRATION.md: 'corrected alpha = 0.05/21 ~= 0.0024 per
    condition' -- checked against the hand-computed division, and against
    the specific rounded value the preregistration itself states."""
    alpha = corrected_alpha()
    assert abs(alpha - 0.05 / 21) < 1e-15
    assert abs(alpha - 0.0024) < 0.0001


def test_pairwise_comparison_matches_a_hand_computed_paired_t_test() -> None:
    """Two methods, 5 paired seeds each (docs/PREREGISTRATION.md v2:
    'seeds are PAIRED across all 7 methods' -- exploited here via a PAIRED
    t-test on same-seed-index differences, per
    docs/experimental_design.md's 'full detail deferred to Day 25').
    Hand-computed: diffs = a - b = [-0.5, -0.2, 0.2, -0.3, -0.5], mean =
    -0.26, sample std (ddof=1) = 0.2880972..., t = mean / (std/sqrt(5)) =
    -2.017991... -- verified against scipy.stats.ttest_rel independently
    before writing this test (not assumed to match)."""
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [1.5, 2.2, 2.8, 4.3, 5.5]

    results = pairwise_comparisons({"method_a": a, "method_b": b})
    assert len(results) == 1
    result = results[0]
    assert {result.method_a, result.method_b} == {"method_a", "method_b"}
    assert abs(result.mean_difference - (-0.26)) < 1e-9
    assert abs(result.p_value - 0.11375780482862581) < 1e-9
    # 0.1138 > corrected_alpha() (~0.0024) -- not significant at this n.
    assert result.significant is False


def test_pairwise_comparisons_covers_every_pair_among_seven_methods() -> None:
    """docs/PREREGISTRATION.md: '21 pairwise comparisons per condition for
    7 methods' -- 7 choose 2 = 21, checked directly rather than trusting
    itertools.combinations to have been called correctly."""
    rng = np.random.default_rng(0)
    errors_by_method = {f"method_{i}": rng.normal(0, 1, 10) for i in range(7)}
    results = pairwise_comparisons(errors_by_method)
    assert len(results) == 21
    pairs = {frozenset((r.method_a, r.method_b)) for r in results}
    assert len(pairs) == 21  # no duplicate or missing pair


def test_pairwise_comparisons_excludes_seeds_where_either_method_failed() -> None:
    """A seed where either method has a NaN (a failed fit, per the Week 3
    contract) cannot contribute to a PAIRED comparison -- the pairing is
    per seed_index, so one side missing invalidates that seed for this
    comparison specifically. Verified the joint-valid filter actually
    drops the NaN seed rather than propagating it (a paired t-test on
    data containing NaN would silently return NaN for VALID seeds too)."""
    a = [1.0, 2.0, float("nan"), 4.0, 5.0]
    b = [1.5, 2.2, 2.8, 4.3, 5.5]

    results = pairwise_comparisons({"a": a, "b": b})
    assert len(results) == 1
    result = results[0]
    assert not np.isnan(result.mean_difference)
    assert not np.isnan(result.p_value)
    # Recomputed by hand over the 4 jointly-valid seeds only:
    # diffs = [1.0-1.5, 2.0-2.2, 4.0-4.3, 5.0-5.5] = [-0.5,-0.2,-0.3,-0.5]
    expected_diffs = np.array([-0.5, -0.2, -0.3, -0.5])
    assert abs(result.mean_difference - float(expected_diffs.mean())) < 1e-9
