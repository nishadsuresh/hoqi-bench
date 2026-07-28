"""
Day 25's statistical protocol, implemented EXACTLY per
`docs/PREREGISTRATION.md`'s Statistical protocol section: bootstrap
confidence intervals, breakdown-threshold detection, and the Bonferroni
multiple-comparison correction. `docs/WEEK3-4_PLAN.md` Day 25's hard rule
governs this whole module: no statistical test not preregistered, and
anything that looks missing is flagged for Nishi, not silently added.

**Breakdown-threshold's three ambiguities were resolved via `llm-council`
(2026-07-28, 5 advisors + 5-way peer review) before this module was
written**, per the same discipline `docs/PREREGISTRATION.md`'s D1/D2
deviations already hold themselves to -- resolving a genuine ambiguity in
an already-preregistered statistic is itself a dated clarification, not a
free implementation choice, and is recorded as D3 in that document. Full
reasoning below; the council's own key correction is folded in rather than
just its conclusion, since the correction changes WHY the answer is right,
not just what the answer is.

**Ambiguity 1 (denominator) -- resolved: `PREREGISTERED_TOLERANCE_M`,
identical on both axes, not a per-condition percentage.** The preregistered
text ("1% relative RMS error") names no denominator. Two live candidates:
(a) a FIXED physical scale independent of the condition
(`reference_scale.PREREGISTERED_TOLERANCE_M`, 1% of lambda/2); (b) 1% of
the record's OWN displacement range for that condition, which varies with
`arc_fraction` and makes the arc-coverage axis's own threshold partly
self-referential. The council initially converged on (a) by analogy to Day
21's cross-validation gate, which fixed an explicit denominator rather than
the record's own noisy RMS -- but one advisor (the Contrarian) correctly
caught that the ANALOGY, as first framed, was imprecise: Day 21's
denominator (`arc_fraction * 2*pi`) is condition-DEPENDENT, the opposite of
option (a)'s condition-INDEPENDENCE. Peer review resolved this precisely:
the generalizable principle Day 21 actually established was not "the
denominator must be fixed across conditions," it was **anti-circularity**
-- the denominator must not be a function of the noisy, FITTED quantity the
metric is scoring. `arc_fraction * 2*pi` is condition-dependent but not
self-referential (a deterministic nominal, known before any fit is
attempted, never derived from a method's noisy output);
`PREREGISTERED_TOLERANCE_M` is even more strongly anti-circular
(condition-independent AND non-derived). Both satisfy the real principle;
option (b) violates it. Verified before trusting this reuse (Contrarian's
"theater risk" challenge): `git log --follow` shows `reference_scale.py`
was introduced in Day 22 for a DIFFERENT purpose
(`classify_displacement_error`), before any breakdown-threshold code
existed -- reusing it here is a genuine decision, not a rubber stamp of an
assumption already baked into not-yet-written code.

**Ambiguity 2 (interpolation scale) -- resolved: match each grid's own
design, unanimous across all 5 advisors.** `amplitude_ratio`'s grid is
roughly linearly spaced; `arc_fraction`'s is roughly log-spaced (spanning
two orders of magnitude multiplicatively, since arc_fraction represents a
FRACTION of a fringe cycle covered). Interpolating linearly in the raw
parameter on the log-spaced axis would report a "midpoint" nowhere near the
physical midpoint the grid was designed around. `log_scale` is therefore an
explicit boolean the CALLER sets per axis (never inferred from grid spacing
at runtime, per the Executor's concrete recommendation) --
`log_scale=True` for `arc_fraction`, `False` for `amplitude_ratio` and
every other axis this function might see.

**Ambiguity 3 (scan direction, non-monotonicity, and two missing edge
cases the council itself surfaced) -- resolved:**
- Scan proceeds in the order `parameter_values`/`mean_errors` are given, an
  EXPLICIT contract the caller is responsible for (easiest-to-hardest --
  for this project's two applicable axes, that happens to match the grids'
  natural listed order, `amplitude_ratio` ascending from 1.0 and
  `arc_fraction` descending from 1.0, but that is a property of THESE
  grids, not inferred by this function, per the Outsider's point that nothing
  in the preregistered text states a scan direction).
- First crossing in that scan order wins; later re-crossings (real noise
  will not make every curve monotonic) are ignored, never averaged.
- **All five peer reviews independently flagged a fourth case the original
  three ambiguities never named**: what to report when a method NEVER
  crosses tolerance across the whole swept range -- the mirror image of
  "broken at the first point," and per
  `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` almost certainly the MORE
  common case (Heydemann, Halir & Flusser, Fitzgibbon, Koenig are
  near-ceiling on these axes by construction). A `float | None` return type
  -- this module's first draft, before the council ran -- cannot
  distinguish "broken at start" from "never breaks down" from "a real
  crossing at exactly grid point 0," which is precisely the kind of
  silently-wrong-but-plausible number this whole exercise exists to
  prevent. Fixed via `BreakdownThreshold`, a three-way discriminated
  result, below.

**Left as an explicit, acknowledged limitation, not resolved (escalated by
3 of 5 peer reviews as beyond what the council itself could decide):** no
uncertainty quantification on the crossing point itself. The estimate comes
from noisy per-condition means on a finite grid; noise near the threshold
could shift which grid point is "first." Not addressed here -- flagged for
Nishi's judgment on whether it belongs in Week 4's scope or a later
refinement, per the hard rule that a statistical test not preregistered
does not get added on this module's own initiative.

Pipeline position: consumed by Day 28's RQ1/RQ2 analysis, over
`aggregate.MethodConditionSummary` rows the sweep runner (Day 24) and
metrics layer (Day 22) already produce.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import scipy.stats

from hoqi_bench._types import AnyFloatArray

# Bonferroni family size: docs/PREREGISTRATION.md's "all pairwise method
# comparisons WITHIN a single research question and a single swept
# condition" -- 7 methods choose 2 = 21, the preregistered family.
BONFERRONI_FAMILY_SIZE = 21


def corrected_alpha(alpha: float = 0.05) -> float:
    """Bonferroni-corrected significance level for one pairwise comparison
    within the preregistered 21-comparison family (`docs/PREREGISTRATION.md`:
    "corrected alpha = 0.05/21 ~= 0.0024 per condition"). NOT a single
    global correction across all 359 conditions x 5 RQs -- the family is
    scoped to one research question at one condition, per that document's
    explicit statement, unchanged from v1.
    """
    return alpha / BONFERRONI_FAMILY_SIZE


def bootstrap_ci(
    values: Sequence[float] | AnyFloatArray,
    *,
    n_resamples: int = 10_000,
    confidence: float = 0.95,
    seed: int,
) -> tuple[float, float]:
    """Percentile-method bootstrap confidence interval on the mean,
    `docs/PREREGISTRATION.md`'s "Bootstrap confidence intervals (percentile
    method) on the mean across 50 seeds per condition" -- chosen there over
    a normal-approximation CI because failure-inflated distributions are
    not assumed normal.

    Equation provenance: the percentile bootstrap (Efron 1979) -- resample
    `values` with replacement `n_resamples` times, compute the mean of each
    resample, and take the `(1-confidence)/2` and `1-(1-confidence)/2`
    percentiles of the resulting distribution of means as the CI bounds.

    Design decision: `seed` is REQUIRED, not defaulted, matching this
    project's seeds.py convention that nothing in the campaign draws from
    an unseeded global RNG state -- a bootstrap CI computed twice on
    identical input must be byte-identical, and an implicit default seed
    would make that true only by accident.

    Failure mode: on a degenerate all-identical input (every value the
    same constant), every resample's mean equals that constant, so the CI
    collapses to a zero-width interval at that value -- not NaN, not an
    error, the mathematically correct answer for zero-variance data.
    """
    values_array = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n = len(values_array)

    resample_indices = rng.integers(0, n, size=(n_resamples, n))
    resample_means = values_array[resample_indices].mean(axis=1)

    lower_percentile = 100 * (1 - confidence) / 2
    upper_percentile = 100 * (1 - (1 - confidence) / 2)
    low = float(np.percentile(resample_means, lower_percentile))
    high = float(np.percentile(resample_means, upper_percentile))
    return low, high


@dataclass(frozen=True)
class BreakdownThreshold:
    """The three-way discriminated result `breakdown_threshold` returns --
    see this module's docstring for why a bare `float | None` cannot
    represent this correctly.

    value: the interpolated crossing point, populated ONLY when
        `status == "found"`; `None` in both other cases.
    status: `"found"` (a real crossing was interpolated between two grid
        points), `"broken_at_start"` (mean error already exceeds tolerance
        at the very first, easiest grid point -- no interpolation is
        possible below the grid's own start, e.g. `raw_atan2` on several
        axes), or `"no_breakdown_in_range"` (mean error never exceeds
        tolerance anywhere in the swept range -- the expected case for
        this benchmark's near-ceiling conic fitters on the classic axes,
        per `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`).
    """

    value: float | None
    status: str


def breakdown_threshold(
    parameter_values: Sequence[float],
    mean_errors: Sequence[float],
    tolerance_m: float,
    *,
    log_scale: bool = False,
) -> BreakdownThreshold:
    """Smallest swept value where mean error first exceeds `tolerance_m`,
    via interpolation between grid points -- see this module's docstring
    for the full, council-resolved specification this implements.

    `parameter_values`/`mean_errors` must already be in SCAN order
    (easiest-to-hardest) and the same length; this function does not sort
    or validate that ordering, per the design decision recorded above that
    scan direction is an explicit caller contract, not something inferred
    here. `mean_errors` must already exclude outright failures per
    `docs/PREREGISTRATION.md` ("mean error (excluding outright failures,
    tracked separately)") -- computed by the caller via
    `aggregate.summarize`, not re-derived here.

    `log_scale=True` interpolates in `log(parameter_values)` rather than
    the raw value -- set this for `arc_fraction`, leave `False` for
    `amplitude_ratio` and any other linearly-spaced axis.

    Failure mode: none that raises. A single-point input (`len == 1`) with
    that point already above tolerance reports `"broken_at_start"`; with
    it below, reports `"no_breakdown_in_range"` -- both well-defined
    without needing a second point to interpolate against.
    """
    if mean_errors[0] > tolerance_m:
        return BreakdownThreshold(value=None, status="broken_at_start")

    for index in range(1, len(parameter_values)):
        if mean_errors[index] > tolerance_m:
            x0, x1 = parameter_values[index - 1], parameter_values[index]
            y0, y1 = mean_errors[index - 1], mean_errors[index]

            x0_transformed = math.log(x0) if log_scale else x0
            x1_transformed = math.log(x1) if log_scale else x1

            fraction = (tolerance_m - y0) / (y1 - y0)
            crossing_transformed = x0_transformed + fraction * (x1_transformed - x0_transformed)
            value = math.exp(crossing_transformed) if log_scale else crossing_transformed
            return BreakdownThreshold(value=value, status="found")

    return BreakdownThreshold(value=None, status="no_breakdown_in_range")


@dataclass(frozen=True)
class PairwiseComparison:
    """One method-pair's comparison at one condition -- the row
    `docs/PREREGISTRATION.md`'s "21 pairwise comparisons per condition"
    produces.

    mean_difference: `mean(errors[method_a] - errors[method_b])` over the
        seeds where BOTH methods have a valid (non-NaN) result -- signed,
        so a caller can tell which method the comparison favors, not just
        that they differ.
    p_value: from a PAIRED t-test (see `pairwise_comparisons` docstring for
        why paired) on those same jointly-valid seeds.
    significant: `p_value < corrected_alpha()` -- the preregistered
        Bonferroni threshold for the fixed 21-comparison family
        (`BONFERRONI_FAMILY_SIZE`), not adjusted for however many pairs a
        given call happens to receive.
    """

    method_a: str
    method_b: str
    mean_difference: float
    p_value: float
    significant: bool


def pairwise_comparisons(
    errors_by_method: Mapping[str, Sequence[float] | AnyFloatArray],
) -> list[PairwiseComparison]:
    """Every pairwise comparison among the methods in `errors_by_method`,
    at one condition -- `docs/PREREGISTRATION.md`'s "21 pairwise
    comparisons per condition for 7 methods."

    Design decision -- a PAIRED t-test, not an unpaired one:
    `docs/experimental_design.md` names "an uncorrected pairwise t-test"
    as the baseline this project corrects via Bonferroni, deferring "full
    detail" to this day's implementation. `docs/PREREGISTRATION.md`'s v2
    seed-pairing decision is the detail that resolves it: every method is
    evaluated against the IDENTICAL noise realization at a given
    `(condition, seed_index)` (`seeds.derive_seed`, which structurally
    cannot take a method identifier), specifically to "remove the
    shared-noise-draw variance term from every method-vs-method
    comparison." An UNPAIRED test would throw away exactly the variance
    reduction that pairing was built to provide. `scipy.stats.ttest_rel`
    (a paired t-test on same-index differences) is therefore the test that
    actually uses the data this project went to the trouble of pairing.

    `errors_by_method` values must be aligned by SEED INDEX (position `i`
    in every array is the same seed) -- the same alignment
    `aggregate.MethodConditionSummary` rows naturally have when read back
    from Day 24's per-condition Parquet files, since `run_condition`
    writes seeds in a fixed `range(n_seeds)` order per method.

    A seed where either method's value is NaN (Week 3's fit-failure
    contract: `docs/WEEK3_METHOD_CONTRACT.md` sec2) is excluded from THAT
    PAIR's comparison -- the pairing is per seed_index, so one side
    missing invalidates the pair for that seed specifically, even if the
    other method in a DIFFERENT pair succeeded on it. Each pair is
    therefore filtered independently, not against one global valid-seed
    mask.

    Failure mode: if fewer than 2 jointly-valid seeds remain for a pair
    (extreme failure rates on both methods), `scipy.stats.ttest_rel`
    returns `nan` for both statistic and p-value rather than raising --
    propagated here as `PairwiseComparison(p_value=nan, significant=False)`
    rather than crashing the whole comparison table over one degenerate
    pair; NaN is not treated as significant.
    """
    comparisons: list[PairwiseComparison] = []
    for method_a, method_b in itertools.combinations(sorted(errors_by_method), 2):
        values_a = np.asarray(errors_by_method[method_a], dtype=np.float64)
        values_b = np.asarray(errors_by_method[method_b], dtype=np.float64)

        jointly_valid = np.isfinite(values_a) & np.isfinite(values_b)
        paired_a = values_a[jointly_valid]
        paired_b = values_b[jointly_valid]

        if len(paired_a) < 2:
            comparisons.append(
                PairwiseComparison(
                    method_a=method_a,
                    method_b=method_b,
                    mean_difference=float("nan"),
                    p_value=float("nan"),
                    significant=False,
                )
            )
            continue

        test_result = scipy.stats.ttest_rel(paired_a, paired_b)
        p_value = float(test_result.pvalue)
        comparisons.append(
            PairwiseComparison(
                method_a=method_a,
                method_b=method_b,
                mean_difference=float(np.mean(paired_a - paired_b)),
                p_value=p_value,
                significant=(not math.isnan(p_value)) and p_value < corrected_alpha(),
            )
        )
    return comparisons
