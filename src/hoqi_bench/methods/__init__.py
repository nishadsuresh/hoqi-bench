"""
Registry of every implemented phase-recovery method, name -> `fit()`
callable (`methods.base.PhaseRecoveryMethod`).

Why this exists: Week 4's sweep runner (Day 24, not yet built) needs to
iterate "every method" without hardcoding a list of imports at the call
site, and `config.SweepConfig.methods` (a list of name strings, loaded
from TOML) needs a name -> callable lookup to actually run what a config
requests. Built incrementally as each Day 15-20 method lands -- this file
is updated once per new method, not written all at once, so `METHOD_REGISTRY`
always reflects exactly what's implemented so far, not the full eventual
set of 7 ahead of schedule.

Pipeline position: imported by Week 4's sweep runner; also usable directly
by any Week 3 method's own test (e.g. Day 21's cross-validation gate,
which needs every method callable by name in one place).
"""

from __future__ import annotations

from hoqi_bench._types import FloatArray
from hoqi_bench.methods import (
    fitzgibbon,
    halir_flusser,
    heydemann,
    kasa,
    koning_wimmer_witkovsky,
    raw_atan2,
    taubin,
)
from hoqi_bench.methods.base import FitResult, PhaseRecoveryMethod, failed_result, timed_fit

METHOD_REGISTRY: dict[str, PhaseRecoveryMethod] = {
    raw_atan2.NAME: raw_atan2.fit,
    kasa.NAME: kasa.fit,
    heydemann.NAME: heydemann.fit,
    halir_flusser.NAME: halir_flusser.fit,
    fitzgibbon.NAME: fitzgibbon.fit,
    taubin.NAME: taubin.fit,
    koning_wimmer_witkovsky.NAME: koning_wimmer_witkovsky.fit,
}


def _resolve_fit_call(
    method_name: str,
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    *,
    mean_intensity: float,
) -> tuple[PhaseRecoveryMethod, tuple[FloatArray, FloatArray], dict[str, float]]:
    """Resolves a method's `fit()` callable plus the exact positional/keyword
    arguments it should be called with -- the ONE place the registry's one
    non-uniform calling convention (`raw_atan2` alone needs `mean_intensity`)
    is handled, shared by both `fit_by_name` and `timed_fit_by_name` below
    so the dispatch logic exists exactly once regardless of which of them a
    caller needs.

    Why this exists as a THIRD function rather than having
    `timed_fit_by_name` call `fit_by_name` directly (Week 5 Task 3, Day 31):
    `methods.base.timed_fit`'s signature is `(fit_fn: PhaseRecoveryMethod,
    *args: FloatArray, **kwargs: object)` -- deliberately typed so `*args`
    can only ever be signal arrays, which is what lets `mypy --strict`
    catch a caller passing something that isn't fit data. `fit_by_name`
    takes `method_name: str` as its own first argument, so
    `timed_fit(fit_by_name, method_name, intensity_i, intensity_q, ...)`
    does not type-check -- `method_name` would need to flow into
    `*args: FloatArray`. Extracting the dispatch decision into its own
    function, returning the resolved callable and its args separately,
    lets both wrappers call `timed_fit`/`fit_fn` directly with only
    `FloatArray` positional arguments, with the `raw_atan2` branch written
    once instead of duplicated a fourth time (see `fit_by_name`'s own
    Week 3 review history below for why a fourth copy is exactly the
    regression this project has already paid for once).
    """
    fit_fn = METHOD_REGISTRY[method_name]
    if method_name == raw_atan2.NAME:
        return fit_fn, (intensity_i, intensity_q), {"mean_intensity": mean_intensity}
    return fit_fn, (intensity_i, intensity_q), {}


def fit_by_name(
    method_name: str,
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    *,
    mean_intensity: float,
) -> FitResult:
    """Calls one registered method by name, supplying whatever
    condition-derived arguments that particular method needs -- the single
    place the registry's one non-uniform calling convention is handled.

    Why this exists (Week 3 review, 2026-07-27): `PhaseRecoveryMethod` is
    `Callable[..., FitResult]` with everything past `(intensity_i,
    intensity_q)` keyword-only and method-specific (`methods/base.py`), and
    exactly one method uses that freedom -- `raw_atan2` takes
    `mean_intensity`, the one nominal design constant a "no correction"
    baseline is allowed to assume without estimating it (see that module's
    docstring for why that is what makes it the floor). Iterating
    `METHOD_REGISTRY` therefore requires an `if name == "raw_atan2"` branch
    at the call site, and by the end of Week 3 three separate call sites had
    independently grown their own copy of it (`scripts/robustness_matrix.py`,
    `tests/test_full_campaign_smoke.py`, `tests/test_cross_validation_gate.py`).
    Day 24's sweep runner would have been the fourth.

    That is the same duplication `docs/WEEK3-4_PLAN.md` Part 1's P1 named as
    its highest-value pre-Week-3 fix, in the same shape: glue that every
    consumer reconstructs independently, with no single place enforcing it,
    so the copies can silently drift. Consolidated here BEFORE the runner
    exists rather than after -- a copy that passes the wrong
    `mean_intensity` produces a plausible-looking wrong answer from the
    baseline method, with nothing raising.

    `mean_intensity` is required rather than defaulted deliberately: the
    campaign's own value comes from each condition's resolved dict, and a
    default here would let a caller silently benchmark the baseline against
    a DC bias point the signal does not have.
    """
    fit_fn, args, kwargs = _resolve_fit_call(
        method_name, intensity_i, intensity_q, mean_intensity=mean_intensity
    )
    return fit_fn(*args, **kwargs)


def timed_fit_by_name(
    method_name: str,
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    *,
    mean_intensity: float,
) -> FitResult:
    """`fit_by_name`, with `runtime_s` populated via `methods.base.timed_fit`
    -- the wall-clock-timed counterpart `runner.py` should call so the
    preregistered cost metric is actually recorded (Week 5 Task 3, Day 31;
    `docs/WEEK5_PREFLIGHT_AUDIT.md` finding P3: `runner.py` previously
    called `fit_by_name` directly, so `runtime_s` was null in 100% of the
    125,650-fit main campaign).

    Shares `_resolve_fit_call`'s dispatch logic with `fit_by_name` rather
    than wrapping it, specifically so the ONE place runtime is measured
    (`methods.base.timed_fit`, per `FitResult.runtime_s`'s own docstring)
    stays true even for the method-by-name entry point -- see
    `_resolve_fit_call`'s docstring for why `timed_fit(fit_by_name, ...)`
    was not an option.
    """
    fit_fn, args, kwargs = _resolve_fit_call(
        method_name, intensity_i, intensity_q, mean_intensity=mean_intensity
    )
    return timed_fit(fit_fn, *args, **kwargs)


__all__ = [
    "METHOD_REGISTRY",
    "FitResult",
    "PhaseRecoveryMethod",
    "failed_result",
    "fit_by_name",
    "timed_fit",
    "timed_fit_by_name",
]
