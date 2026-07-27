"""
The common interface every Week 3 phase-recovery method (Days 15-20)
implements: `FitResult`, the return type every method must produce, and
`PhaseRecoveryMethod`, the calling convention every method's `fit()`
function satisfies.

Why this exists: `docs/WEEK3_METHOD_CONTRACT.md` fixes the CONTRACT a
result type must satisfy (wrapped circular phase error as the primary
endpoint; on failure, every numeric field NaN, a boolean `failed` flag, and
a specific reason code) before any method exists, so gate criteria and
failure-handling conventions are decided in advance rather than authored
after seeing results. This module is where that contract becomes a real
type, not just prose -- designed against the HARDEST method's needs
(Day 20's Köning/Wimmer/Witkovský iterative EIV fit, which needs
convergence status, iteration count, and parameter covariance), not the
simplest (this day's own raw-atan2 baseline), so Days 16-19's tests are
not invalidated by a forced interface refactor once Day 20 arrives
(docs/WEEK3-4_PLAN.md Part 2, Day 15's standing rules).

Design decision -- functions in a registry, NOT class instances satisfying
a `typing.Protocol` (a deviation from `docs/WEEK3-4_PLAN.md`'s own draft
phrasing, recorded here per that document's own deviation-logging rule):
every other module in this project (`transforms.py`, `noise.py`,
`pipeline.py`, `simulate.py`) is a plain function operating on plain data,
with the two existing `@dataclass(frozen=True)` records
(`resolve.ResolvedCondition`, `simulate.SimulatedSignal`) used purely as
data, never as behavior-carrying objects. Introducing method-as-class-
instance here would be this codebase's first behavioral OOP construct, for
no benefit `NAME` constants plus a plain-function registry
(`methods/__init__.py`) don't already provide just as cleanly. A `Protocol`
describing a bound method (`self.fit(...)`, `self.name`) buys nothing over
a `dict[str, PhaseRecoveryMethod]` built from each module's own `NAME`
constant, which is what `methods/__init__.py` builds.

Pipeline position: every `methodsNN.py` module (Days 15-20) implements
`fit()` against this interface; `methods/__init__.py` collects them into a
name -> callable registry; Week 4's sweep runner (Day 24, not yet built)
iterates that registry, calling each method's `fit()` against every
`simulate.SimulatedSignal` the campaign produces.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from hoqi_bench._types import FloatArray


@dataclass(frozen=True)
class FitResult:
    """One method's result for one (condition, seed_index) simulated
    signal -- the type every Week 3 method returns, per
    `docs/WEEK3_METHOD_CONTRACT.md` §2's fit-failure contract.

    recovered_phase: the method's estimate of true phase (radians), for
        every sample in the input signal -- compared against
        `simulate.SimulatedSignal.true_phase` via
        `metrics.wrapped_phase_error` (Day 22-23, not yet built), never a
        naive linear difference (docs/WEEK3_METHOD_CONTRACT.md §1). On
        failure, every entry is NaN (see `failed_result` below).
    failed: True if this method could not produce a valid fit for this
        signal (non-convergence, a singular matrix, a rejected
        ellipse-specific solution, etc.) -- the contract's first-class
        failure-rate signal (`mean(failed)`), not something inferred from
        NaN presence.
    reason: a short, SPECIFIC string identifying the failure mode when
        `failed=True` (e.g. "singular_scatter_matrix", "non_convergent",
        "rejected_ellipse_solution") -- never a generic "failed", per the
        contract. `None` when `failed=False`.
    params: the method's fitted model parameters (e.g. an ellipse's
        center/semi-axes/tilt, or a circle's center/radius), keyed by name
        -- optional (`None` for a method with nothing meaningful to report
        here, though none of the 7 planned methods currently expect this;
        kept optional rather than required so a future method type isn't
        forced to fabricate values). NOT used by any metric computation;
        exists for diagnostics and the robustness matrix (Day 20).
    converged: `True`/`False` for an ITERATIVE method (only Day 20's Köning
        fit, among the 7 planned); `None` for a non-iterative,
        single-solve method (atan2, Kasa, Heydemann, Halir & Flusser,
        Fitzgibbon, Taubin all solve in one step -- "did it converge" does
        not apply to them, and `None` says so explicitly rather than a
        method needing to fabricate `True`).
    n_iter: iteration count for an iterative method; `None` for a
        non-iterative one, same rationale as `converged`.
    covariance: the fitted parameter covariance matrix, for a method that
        estimates one (only Köning's errors-in-variables fit, per
        `notes/koning_2014.md`); `None` for every other method.
    runtime_s: wall-clock seconds this fit took. Deliberately NOT populated
        by individual methods themselves (see `timed_fit` below) -- timing
        every method identically, in one place, is both less error-prone
        than asking 7 implementations to self-time correctly and
        guarantees the numbers are comparable (same clock, same
        measurement boundary) across all of them.

    Design decision: `frozen=True`, matching every other data record in
    this project (`resolve.ResolvedCondition`, `simulate.SimulatedSignal`)
    -- a fit result is a value produced once and read many times (by
    metrics, by the sweep runner's Parquet writer), never mutated in
    place.
    """

    recovered_phase: FloatArray
    failed: bool = False
    reason: str | None = None
    params: dict[str, float] | None = None
    converged: bool | None = None
    n_iter: int | None = None
    covariance: FloatArray | None = None
    runtime_s: float | None = None


def failed_result(n_samples: int, reason: str, *, converged: bool | None = None) -> FitResult:
    """Builds a `FitResult` satisfying `docs/WEEK3_METHOD_CONTRACT.md` §2's
    failure contract: `recovered_phase` filled with NaN (never a
    zero-length or partially-valid array -- every downstream consumer can
    assume `recovered_phase` always has the same length as the input
    signal, failed or not), `failed=True`, and the given SPECIFIC reason
    code.

    `converged` is exposed as a keyword for iterative methods that fail
    via non-convergence (so they can record `converged=False` explicitly,
    distinct from a non-iterative method's failure, which leaves this
    `None` -- "did not converge" and "convergence does not apply" are
    different facts, per `FitResult`'s own docstring above).

    Every method implementation in Days 15-20 that has a real failure mode
    (a singular matrix, a rejected candidate, non-convergence) should call
    this rather than constructing `FitResult(failed=True, ...)` by hand --
    a single shared factory means the "every numeric field NaN" rule can't
    be gotten subtly wrong (e.g. by forgetting a field) in one method but
    not another.
    """
    return FitResult(
        recovered_phase=np.full(n_samples, np.nan, dtype=np.float64),
        failed=True,
        reason=reason,
        converged=converged,
    )


# A method's `fit()` function: takes the distorted (I, Q) signal plus
# whatever method-specific keyword arguments it needs (e.g. raw_atan2's
# `mean_intensity` -- the one nominal design constant that "no correction"
# baseline is allowed to assume, since it fits nothing from the data
# itself), returns a FitResult. Positional args are always exactly
# (intensity_i, intensity_q); everything else is keyword-only and
# method-specific, per this module's own docstring design-decision note.
PhaseRecoveryMethod = Callable[..., FitResult]


def timed_fit(fit_fn: PhaseRecoveryMethod, *args: FloatArray, **kwargs: object) -> FitResult:
    """Calls `fit_fn(*args, **kwargs)`, measuring wall-clock time, and
    returns a FitResult identical to `fit_fn`'s own return value except
    with `runtime_s` populated -- the ONE place runtime is measured (see
    `FitResult.runtime_s`'s docstring for why this isn't each method's own
    job).

    Uses `dataclasses.replace` rather than requiring `fit_fn` to accept a
    timing callback or pre-populate its own `runtime_s` -- keeps every
    method implementation's own code entirely about the math, with zero
    timing boilerplate.
    """
    import time
    from dataclasses import replace

    start = time.perf_counter()
    result = fit_fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return replace(result, runtime_s=elapsed)
