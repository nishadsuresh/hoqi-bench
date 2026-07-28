"""
Collapses one method's per-seed results at one condition into the summary
row Week 5's analysis reads -- and is where both survivorship-bias fixes
land, which is the substance of this module rather than the averaging.

Why this exists, and why it is more than a `mean()` (Day 22):

- **`docs/WEEK3-4_PLAN.md` §0.4** -- a per-condition mean over surviving
  runs compares DIFFERENT POPULATIONS across methods whenever one method
  drops out preferentially in the hard regimes, which are exactly the
  regimes that discriminate between methods. Köning fails to converge
  preferentially at small `arc_fraction`; averaging its survivors there
  against Fitzgibbon's full sample flatters whichever method dropped out of
  the hardest cases.
- **`docs/WEEK3_METHOD_CONTRACT.md` §2.1** -- the mirror image, found by
  the Week 3 review and NOT anticipated by §0.4: the `failed` flag records
  whether a method DETECTS its own failure, not whether it failed. Measured
  over the full campaign grid, Fitzgibbon self-reports 0.00% failures while
  returning an unusable answer 13.48% of the time; Heydemann self-reports
  24.51% and returns an unusable answer 0.00% of the time. A gate built on
  the `failed` flag alone would let a method with no failure mode be ranked
  on conditions where its output is meaningless, while excluding the one
  method honest enough to say it could not fit.

Every summary this module produces therefore carries THREE reliability
numbers, never one: `failure_rate` (self-reported), `gross_error_rate`
(claimed success, unusable answer), and `unusable_rate` (their sum -- the
one that actually matters, and the one the ranking gate uses).

Pipeline position: fed by Day 24's sweep runner, one `SeedOutcome` per
`(method, condition, seed)`; read by Day 25's statistics layer and Day 28's
analysis. `outcome_from_fit` is the bridge from a `methods.base.FitResult`,
so the runner never constructs a `SeedOutcome` field by field and cannot
get the failed/NaN handling subtly different from this module's own.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray
from hoqi_bench.forward_model import HENE_WAVELENGTH_M
from hoqi_bench.methods.base import FitResult
from hoqi_bench.metrics import (
    displacement_errors,
    peak_absolute_error,
    rmse,
    wrapped_phase_error,
)

# ---- Thresholds, fixed 2026-07-27 BEFORE the campaign runs ----

# `docs/WEEK3_METHOD_CONTRACT.md` §2.1. A wrapped-phase RMSE above 0.5 rad
# is ~8% of a full cycle -- ~25 nm of the 316.4 nm HeNe half-wavelength
# range, or ~25x the entire on-resonance motion Lehmann et al. 2025 measure
# (`reference_scale.py`). No practitioner could act on it, whatever the
# method reports about itself. Expressed in PHASE rather than meters so it
# is independent of wavelength, and so it means the same thing at every
# `arc_fraction`.
GROSS_ERROR_PHASE_RAD = 0.5

# `docs/WEEK3-4_PLAN.md` §0.4 requires this threshold be fixed before Day 24.
#
# Chosen on an external principle rather than from the observed
# distribution, which matters because the campaign-wide rates were already
# measured during the Week 3 review and a threshold picked afterwards could
# not be shown to be innocent of them: above ~20% attrition, a
# complete-case analysis is conventionally treated as at serious risk of
# bias regardless of the mechanism, because the survivors are a strongly
# selected subsample of the intended one. 20% is that convention, not a
# number that includes or excludes any particular method here.
#
# STRENGTHENED beyond §0.4's own wording, per §2.1: §0.4 says "no method is
# ranked on any condition where any method's FAILURE RATE exceeds a
# threshold". Applied literally, a method with no failure mode at all
# reports 0% forever and never triggers the gate, no matter how much
# garbage it emits -- which is precisely the hole §2.1 found. The gate below
# therefore uses `unusable_rate` (failure + gross error), so a method that
# is silently wrong is excluded on the same terms as one that says so.
MAX_UNUSABLE_RATE_FOR_RANKING = 0.20


@dataclass(frozen=True)
class SeedOutcome:
    """One method's result for one `(condition, seed_index)`, reduced to
    the scalars aggregation needs.

    Every error field is NaN when `failed` is True -- never 0.0, never
    omitted -- so that a bug which forgets to check `failed` produces a NaN
    that propagates loudly rather than a zero that silently improves a
    mean. `docs/WEEK3_METHOD_CONTRACT.md` §2's contract, one level down.
    """

    failed: bool
    reason: str | None
    displacement_rmse_m: float
    peak_absolute_error_m: float
    phase_rmse_rad: float
    runtime_s: float | None
    converged: bool | None


@dataclass(frozen=True)
class MethodConditionSummary:
    """One method at one condition, across all seeds -- the row Week 5
    reads.

    `*_mean`/`median`/`std`/`p05`/`p95` are computed over SUCCESSFUL seeds
    only, and are NaN when there are none. That exclusion is why the three
    reliability rates above them are not optional context: the accuracy
    numbers describe a subpopulation whose size those rates define.
    """

    method_name: str
    condition_name: str
    n_seeds: int
    n_failed: int
    n_gross_error: int
    failure_rate: float
    gross_error_rate: float
    unusable_rate: float
    convergence_rate: float | None
    displacement_rmse_mean_m: float
    displacement_rmse_median_m: float
    displacement_rmse_std_m: float
    displacement_rmse_p05_m: float
    displacement_rmse_p95_m: float
    peak_absolute_error_mean_m: float
    phase_rmse_mean_rad: float
    runtime_s_mean: float


def outcome_from_fit(
    result: FitResult,
    true_phase: AnyFloatArray,
    wavelength_m: float = HENE_WAVELENGTH_M,
) -> SeedOutcome:
    """Builds a `SeedOutcome` from a raw `FitResult` -- the single bridge
    between Week 3's method interface and Week 4's aggregation, so the
    failed/NaN/gross-error rules are applied in exactly one place rather
    than re-derived by the sweep runner.

    A failed fit short-circuits to all-NaN without computing metrics on its
    all-NaN phase array, which would produce the same NaNs but also a pile
    of numpy warnings that mean nothing.
    """
    if result.failed:
        return SeedOutcome(
            failed=True,
            reason=result.reason,
            displacement_rmse_m=float("nan"),
            peak_absolute_error_m=float("nan"),
            phase_rmse_rad=float("nan"),
            runtime_s=result.runtime_s,
            converged=result.converged,
        )

    phase_errors = wrapped_phase_error(true_phase, result.recovered_phase)
    displacement = displacement_errors(true_phase, result.recovered_phase, wavelength_m)
    return SeedOutcome(
        failed=False,
        reason=None,
        displacement_rmse_m=rmse(displacement),
        peak_absolute_error_m=peak_absolute_error(displacement),
        phase_rmse_rad=rmse(phase_errors),
        runtime_s=result.runtime_s,
        converged=result.converged,
    )


def is_gross_error(outcome: SeedOutcome) -> bool:
    """True for a seed that claimed success and returned an unusable
    answer -- `failed=False` with a phase RMSE above
    `GROSS_ERROR_PHASE_RAD`. A failed seed is NOT a gross error: it is
    already counted in `failure_rate`, and double-counting it would make
    `unusable_rate` exceed 1.0."""
    return not outcome.failed and outcome.phase_rmse_rad > GROSS_ERROR_PHASE_RAD


def summarize(
    method_name: str, condition_name: str, outcomes: Sequence[SeedOutcome]
) -> MethodConditionSummary:
    """Collapses every seed for one `(method, condition)` into one summary.

    Failure mode: an empty `outcomes` raises `ValueError` rather than
    returning a row of NaNs. A condition with zero seeds means the sweep
    runner lost rows, and `docs/WEEK3_METHOD_CONTRACT.md` §2's whole point
    is that a missing row is never an acceptable outcome -- silently
    summarising nothing would defeat the contract it is enforcing.
    """
    if not outcomes:
        raise ValueError(f"no seeds for {method_name} at {condition_name}")

    n_seeds = len(outcomes)
    n_failed = sum(1 for o in outcomes if o.failed)
    n_gross = sum(1 for o in outcomes if is_gross_error(o))
    successful = [o for o in outcomes if not o.failed]

    # `converged` is None for the six non-iterative methods -- "convergence
    # does not apply" and "did not converge" are different facts
    # (methods/base.py's FitResult docstring), so a convergence rate is
    # reported only where the concept exists.
    iterative = [o for o in outcomes if o.converged is not None]
    convergence_rate = (
        sum(1 for o in iterative if o.converged) / len(iterative) if iterative else None
    )

    rmses = np.array([o.displacement_rmse_m for o in successful], dtype=np.float64)
    runtimes = [o.runtime_s for o in successful if o.runtime_s is not None]

    def _stat(fn: object, values: FloatArray) -> float:
        """NaN rather than an exception when every seed failed -- an
        all-failed condition is a real, reportable outcome (its
        `failure_rate` is 1.0), not an error."""
        return float(fn(values)) if values.size else float("nan")  # type: ignore[operator]

    return MethodConditionSummary(
        method_name=method_name,
        condition_name=condition_name,
        n_seeds=n_seeds,
        n_failed=n_failed,
        n_gross_error=n_gross,
        failure_rate=n_failed / n_seeds,
        gross_error_rate=n_gross / n_seeds,
        unusable_rate=(n_failed + n_gross) / n_seeds,
        convergence_rate=convergence_rate,
        displacement_rmse_mean_m=_stat(np.mean, rmses),
        displacement_rmse_median_m=_stat(np.median, rmses),
        displacement_rmse_std_m=_stat(np.std, rmses),
        displacement_rmse_p05_m=_stat(lambda v: np.percentile(v, 5), rmses),
        displacement_rmse_p95_m=_stat(lambda v: np.percentile(v, 95), rmses),
        peak_absolute_error_mean_m=_stat(
            np.mean, np.array([o.peak_absolute_error_m for o in successful], dtype=np.float64)
        ),
        phase_rmse_mean_rad=_stat(
            np.mean, np.array([o.phase_rmse_rad for o in successful], dtype=np.float64)
        ),
        runtime_s_mean=float(np.mean(runtimes)) if runtimes else float("nan"),
    )


def is_rankable(summaries_at_condition: Sequence[MethodConditionSummary]) -> bool:
    """Whether methods may be RANKED against each other at this condition.

    The gate from `docs/WEEK3-4_PLAN.md` §0.4, strengthened per
    `docs/WEEK3_METHOD_CONTRACT.md` §2.1 (see
    `MAX_UNUSABLE_RATE_FOR_RANKING`): if ANY method's unusable rate exceeds
    the threshold, no method is ranked here -- not just the offending one.

    Why all-or-nothing rather than excluding the one bad method: the harm
    §0.4 names is that the surviving methods' means describe different
    populations, and that harm is done to the COMPARISON, not to the
    dropout. Dropping the worst method and ranking the rest leaves exactly
    the flattering-by-attrition artifact the gate exists to prevent, on the
    remaining pairs.

    A non-rankable condition is not discarded. Its per-method numbers are
    still reported -- with their reliability rates, which are frequently
    the most informative thing about a hard condition. It simply does not
    contribute an ordering.
    """
    if not summaries_at_condition:
        raise ValueError("no summaries to assess rankability for")
    return all(
        summary.unusable_rate <= MAX_UNUSABLE_RATE_FOR_RANKING
        for summary in summaries_at_condition
    )
