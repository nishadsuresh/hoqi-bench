"""
Cyclic-error harmonic amplitudes -- the interferometry field's standard
figure of merit for residual nonlinearity, and a preregistered metric
(`docs/PREREGISTRATION.md`, Metrics: "Cyclic-error harmonic amplitude
(first and second order)").

What it measures: after a method recovers phase, the leftover error is not
random if the method failed to correct some distortion -- it repeats once
or twice per fringe, because the distortion is a fixed function of position
on the ellipse. The residual therefore looks like
`A1*sin(phi + th1) + A2*sin(2*phi + th2) + noise`, and `A1`/`A2` are the
first- and second-order cyclic errors every calibration paper reports.

Why least squares and NOT an FFT (a real decision, measured before being
made): an FFT assumes the record spans a whole number of periods. 88 of the
main campaign's 359 conditions have `arc_fraction < 1.0` (Week 6 doc audit,
2026-07-29, corrected from an earlier "99" that miscounted the
`arc_x_noise` grid's own 80 sub-fringe points), where that is
false and the FFT's bins stop corresponding to the harmonics of interest.
Measured on a residual with injected A1=0.05, A2=0.03: at
`arc_fraction=0.5` the FFT reports A1=0.0311 and A2=0.0074 (38% and 75%
wrong) while the least-squares projection below is exact to 1e-16. The
projection is exact at every arc down to 0.02 on noiseless data.

**The failure mode this module guards, which is why `conditioning` is a
first-class output**: being algebraically exact is not the same as being
usable. `cos(phi), sin(phi), cos(2*phi), sin(2*phi)` become nearly
collinear when `phi` spans only a small arc -- a fragment of a cycle cannot
distinguish "some first harmonic" from "some second harmonic" -- so with
realistic noise the estimator degrades badly while still returning a
confident number, with no exception and no warning. Measured over 200
seeds at n=60 with residual noise 0.005, injected A1=0.05/A2=0.03:

    arc_fraction  cond    median A1 err  median A2 err
    1.0           1.00    1.3%           2.1%
    0.5           3.50    1.4%           2.7%
    0.35          10.25   1.6%           9.2%
    0.25          33.4    6.1%           19.4%
    0.15          180.9   34.1%          35.4%

The design matrix's condition number tracks this monotonically, so it is
reported directly rather than inferred from `arc_fraction` (which this
function never receives -- the check must be a property of the data).

Pipeline position: called by Day 24's sweep runner once per fit, on the
residual between `simulate.SimulatedSignal.true_phase` and a method's
`FitResult.recovered_phase`; its outputs become two columns of the raw
results table that Day 28's RQ1 analysis reads.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray
from hoqi_bench.metrics import wrapped_phase_error

# Calibrated 2026-07-28 by direct measurement (see module docstring's table),
# not chosen as a round number: the largest design-matrix condition number at
# which the SECOND-order amplitude's median relative error stays under 10% at
# the campaign's own noise baseline. Corresponds to arc_fraction ~= 0.35.
# The first-order amplitude is far more robust (1.6% at this same point), so
# this limit is set by the harder of the two quantities, deliberately.
HARMONIC_CONDITIONING_LIMIT = 10.0

# Harmonic orders the preregistration commits to. Not a parameter: adding a
# third order after seeing results would be exactly the forking-paths problem
# docs/PREREGISTRATION.md exists to prevent.
_ORDERS = (1, 2)


@dataclass(frozen=True)
class CyclicError:
    """First- and second-order cyclic error amplitudes for one fit.

    first_order_rad, second_order_rad: amplitudes in RADIANS of phase.
        Converted to meters by `cyclic_error_m` -- kept in radians here
        because that is the unit the estimator natively produces, and a
        single conversion point is harder to get inconsistently wrong than
        two representations of the same quantity.
    conditioning: condition number of the `[cos k*phi, sin k*phi]` design
        matrix. 1.0 is a full circle; it grows without bound as the sampled
        arc shrinks. Reported always, not only on failure.
    well_conditioned: `conditioning <= HARMONIC_CONDITIONING_LIMIT`. A
        REPORTING FLAG, not a silent drop -- the amplitudes are still
        returned, matching `aggregate.is_rankable`'s own choice to keep a
        non-rankable condition's numbers while withholding its ordering.

    Note for callers aggregating over a FAILED fit's result: `conditioning`
    depends only on the true-phase sampling, not on whether the fit itself
    succeeded, so a failed fit (all-NaN `recovered_phase`) still reports
    `well_conditioned=True` alongside NaN amplitudes. Filtering on
    `well_conditioned` alone does not exclude failed fits -- callers must
    filter on `well_conditioned AND NOT failed` using the caller's own
    failure flag (this module has no notion of "failed", only of
    "well-sampled").
    """

    first_order_rad: float
    second_order_rad: float
    conditioning: float
    well_conditioned: bool


def cyclic_error(true_phase: AnyFloatArray, recovered_phase: AnyFloatArray) -> CyclicError:
    """Projects the wrapped phase residual onto the first two harmonics of
    the TRUE phase, by ordinary least squares.

    Equation provenance: the residual model
    `r(phi) = sum_k [a_k*cos(k*phi) + b_k*sin(k*phi)]` is linear in
    `(a_k, b_k)`, so the amplitudes are `|A_k| = hypot(a_k, b_k)` -- the
    standard harmonic-regression form, not specific to interferometry.
    Harmonics are taken of the true phase (known here, since this is a
    simulation) rather than of sample index, which is what makes the
    estimator correct for a non-uniform or partial phase sweep.

    Failure mode: none that raises. On a degenerate input (all-identical
    phase, or a residual of length < 4) `np.linalg.lstsq` returns a
    minimum-norm solution rather than erroring, and `conditioning` becomes
    very large -- which is precisely what `well_conditioned` reports. On an
    all-NaN residual (a failed fit's recovered_phase), `lstsq` returns NaN
    coefficients cleanly, with no exception and no warning (verified
    directly under `numpy.errstate`/`warnings.simplefilter("error")`) -- so
    no special-casing is needed here; see `CyclicError`'s docstring for how
    a caller must interpret `well_conditioned` in that case. The caller
    decides what to do with a badly-conditioned result; this function never
    silently substitutes one.
    """
    # ---- 1. The residual, via the contract's wrapped metric (never a raw
    # difference -- docs/WEEK3_METHOD_CONTRACT.md sec1) ----
    residual = wrapped_phase_error(true_phase, recovered_phase)
    phase = np.asarray(true_phase, dtype=np.float64)

    # ---- 2. Harmonic design matrix, [cos phi, sin phi, cos 2phi, sin 2phi] ----
    columns: list[FloatArray] = []
    for order in _ORDERS:
        columns.append(np.cos(order * phase))
        columns.append(np.sin(order * phase))
    design = np.column_stack(columns)

    # ---- 3. Least-squares solve, plus the conditioning that decides whether
    # the answer means anything (module docstring's table) ----
    coefficients, *_ = np.linalg.lstsq(design, residual, rcond=None)
    conditioning = float(np.linalg.cond(design))

    amplitudes = [
        float(np.hypot(coefficients[2 * index], coefficients[2 * index + 1]))
        for index, _ in enumerate(_ORDERS)
    ]

    return CyclicError(
        first_order_rad=amplitudes[0],
        second_order_rad=amplitudes[1],
        conditioning=conditioning,
        well_conditioned=conditioning <= HARMONIC_CONDITIONING_LIMIT,
    )


def cyclic_error_m(result: CyclicError, wavelength_m: float) -> tuple[float, float]:
    """Converts both amplitudes from radians of phase to meters of
    displacement, via the same `phi = 4*pi*x/lambda` relation
    `metrics.phase_error_to_displacement` uses -- so a cyclic error can be
    compared directly against `reference_scale.py`'s physical bands, which
    are in meters. Returned as a plain tuple rather than a second dataclass:
    this is a unit conversion, not a new concept."""
    scale = wavelength_m / (4 * np.pi)
    return result.first_order_rad * scale, result.second_order_rad * scale
