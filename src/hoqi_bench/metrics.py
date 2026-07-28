"""
Error metrics for phase-recovery methods: the circular-statistics phase
primitive (Weeks 1-2), and Day 22's displacement RMSE / peak absolute
error built on top of it.

Why this exists (Weeks 1-2 audit, 2026-07-26, adversarial council review):
recovered phase is periodic (mod 2*pi) -- a method that recovers phase
correct to within a small error near a +-pi wrap boundary (e.g. true phase
= pi - 0.01, recovered = -pi + 0.01) has a TRUE error of 0.02 radians, but a
naive linear difference reports ~2*pi, a ~628x overstatement that would
dominate any RMSE computed the ordinary way. This module exists so Week 3's
methods (Days 15-20) and the Day 22-23 metrics implementation have a single,
correct, pre-built primitive for this rather than each re-deriving (or
forgetting) the wraparound correction independently.

**Why displacement error is derived FROM the wrapped phase error, rather
than by converting each phase series to meters and differencing them**
(Day 22, the subtle part of this module): `atan2` returns recovered phase
wrapped into `(-pi, pi]`, while `simulate.SimulatedSignal.true_phase` runs
monotonically from 0 to `arc_fraction * 2*pi`. Converting both to meters
and subtracting would therefore report a displacement error of up to
`lambda/2` for a sample whose phase is actually recovered perfectly, purely
because the two series live on different branches. Wrapping FIRST (in
phase, where wrapping is meaningful) and converting the already-correct
error to meters afterwards is the only ordering that gives the right
answer, and it is what keeps every displacement number in this module
compliant with `docs/WEEK3_METHOD_CONTRACT.md` sec1 rather than merely
adjacent to it.

Pipeline position: `wrapped_phase_error` is called by Week 3's own
per-method tests and Day 21's gate; the Day 22 functions below are called
by `aggregate.py`, which collapses them across seeds, and through it by
Day 24's sweep runner. Physical interpretation of the resulting magnitudes
lives in `reference_scale.py`, deliberately not here -- this module answers
"how big is the error", that one answers "is that big".
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray


def wrapped_phase_error(true_phase: AnyFloatArray, recovered_phase: AnyFloatArray) -> FloatArray:
    """Returns the shortest signed angular difference `recovered_phase -
    true_phase`, wrapped into (-pi, pi] -- the CORRECT error metric for
    periodic phase, unlike a naive `recovered_phase - true_phase` which can
    report an error near 2*pi for two phases that are actually adjacent
    across the +-pi wrap boundary.

    Equation provenance: standard circular-statistics wrapping,
    `((x + pi) mod 2*pi) - pi`, applied to the raw difference -- not specific
    to interferometry, a general technique for any periodic quantity.

    Design decision: returns the SIGNED wrapped difference (not absolute
    value) so callers can distinguish a method that's biased in one
    direction from one that's unbiased but noisy -- RMSE, mean signed error,
    and any other aggregate are computed by the caller from this array, not
    baked in here, keeping this function a single-purpose primitive.

    Failure mode: none -- well-defined for any real-valued inputs (this is
    a modular arithmetic operation, not a division or other operation with
    singularities).
    """
    raw_diff = recovered_phase - true_phase
    wrapped = np.mod(raw_diff + np.pi, 2 * np.pi) - np.pi
    return np.asarray(wrapped, dtype=np.float64)


def phase_error_to_displacement(
    phase_errors: AnyFloatArray, wavelength_m: float
) -> FloatArray:
    """Converts an ALREADY-WRAPPED phase error (radians) to displacement
    error (meters).

    Equation provenance: inverts `forward_model.py`'s own
    `phi = 4*pi*x/wavelength_m` -- the factor of 4 (not 2) is the
    double-pass geometry, light travelling to the mirror and back, so one
    full `2*pi` of phase corresponds to `lambda/2` of mirror displacement,
    not `lambda`.

    Takes phase ERRORS rather than phase values, and says so in the name,
    because the ordering matters and getting it backwards is silent -- see
    this module's docstring for why converting first and differencing
    afterwards produces errors of up to `lambda/2` on perfectly-recovered
    samples.
    """
    return np.asarray(np.asarray(phase_errors) * wavelength_m / (4 * np.pi), dtype=np.float64)


def displacement_errors(
    true_phase: AnyFloatArray, recovered_phase: AnyFloatArray, wavelength_m: float
) -> FloatArray:
    """Per-sample signed displacement error (meters), via the wrapped phase
    error -- the composition of `wrapped_phase_error` and
    `phase_error_to_displacement`, in the one correct order.

    Failure mode: a failed fit's `recovered_phase` is all-NaN
    (`docs/WEEK3_METHOD_CONTRACT.md` sec2), and this function propagates
    that as all-NaN rather than substituting a value. That is deliberate:
    `aggregate.py` excludes failed seeds explicitly using the `failed`
    flag, and a NaN reaching an aggregate is a signal that something
    bypassed that exclusion, which is worth being loud about.
    """
    return phase_error_to_displacement(
        wrapped_phase_error(true_phase, recovered_phase), wavelength_m
    )


def rmse(errors: AnyFloatArray) -> float:
    """Root-mean-square of an error array -- the preregistered primary
    accuracy statistic (`docs/PREREGISTRATION.md` Metrics).

    Deliberately NOT NaN-tolerant (no `np.nanmean`): silently averaging
    over whichever samples happen to be finite is exactly the
    survivorship-bias mechanism `docs/WEEK3-4_PLAN.md` sec0.4 and
    `docs/WEEK3_METHOD_CONTRACT.md` sec2.1 exist to prevent, one level down.
    A NaN in, a NaN out, and the caller deals with it explicitly.
    """
    values = np.asarray(errors, dtype=np.float64)
    return float(np.sqrt(np.mean(values**2)))


def peak_absolute_error(errors: AnyFloatArray) -> float:
    """Largest absolute error in the record -- the preregistered companion
    to RMSE (`docs/PREREGISTRATION.md` Metrics), reported alongside it
    because a method with a good RMSE and one catastrophic sample is a
    different proposition from one with the same RMSE spread evenly, and
    for a displacement sensor the worst sample is often the one that
    matters.

    Same deliberate NaN intolerance as `rmse`, for the same reason.
    """
    return float(np.max(np.abs(np.asarray(errors, dtype=np.float64))))
