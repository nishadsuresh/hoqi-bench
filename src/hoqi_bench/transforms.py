"""
Classic Heydemann (1981) distortion transforms: amplitude imbalance,
quadrature phase error, and DC offset. See docs/derivations/heydemann.md for
the from-scratch derivation these implement in reverse (the derivation
recovers true phase FROM a distorted signal; these transforms produce the
distortion in the first place, for the forward model).

Equation provenance: Heydemann 1981 (`refs/references.bib`, `Heydemann1981`)
for the physical error model itself; docs/derivations/heydemann.md Section 2
for the exact combined-signal equation these transforms must reproduce when
composed (Q = I0 + A*g*sin(phi+eps)).

Pipeline position: bound (via a closure over mean_intensity and the
distortion magnitude) into `pipeline.Transform`-compatible functions and
composed via `pipeline.apply_pipeline`, in the order documented and verified
in `pipeline.py` -- quadrature_phase_error, THEN amplitude_imbalance, THEN
dc_offset last (additive, commutes with the other two -- see pipeline.py's
module docstring for the full ordering justification, including the wrong
order tried first for the first two).
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray


def amplitude_imbalance(
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    mean_intensity: float,
    amplitude_ratio: float,
) -> tuple[FloatArray, FloatArray]:
    """Scales the Q channel's oscillation about its own DC level by
    `amplitude_ratio` -- models a Q-channel photodetector/amplifier gain
    that differs from the I channel's. `amplitude_ratio=1.0` is an exact
    identity (Q returned unchanged).

    Design decision: only Q is scaled, not I -- amplitude imbalance is a
    RATIO between the two channels' gains, so I is kept as the reference
    channel by convention (matching the parameterization in Day 2's
    derivation and in the prior quadrature-interferometer-sim project).
    Scaling both channels by inverse factors would be equivalent up to an
    overall constant, but would need an extra normalization step for no
    benefit.

    Failure mode: none at this stage -- a pure linear scaling has no
    singularities. (Contrast with quadrature_phase_error below, which does
    have one, at the ellipse-fit-correction stage downstream, not here.)
    """
    q_ac = intensity_q - mean_intensity
    return intensity_i, mean_intensity + amplitude_ratio * q_ac


def quadrature_phase_error(
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    mean_intensity: float,
    quadrature_error_rad: float,
) -> tuple[FloatArray, FloatArray]:
    """Mixes I's AC content into Q, weighted by sin/cos of the quadrature
    phase error -- models the two detector channels being separated by
    `90 + quadrature_error_rad` degrees instead of exactly 90.
    `quadrature_error_rad=0.0` is an exact identity (Q returned unchanged).

    Equation: Q' = mean + cos(eps)*(Q-mean) + sin(eps)*(I-mean). This is the
    angle-addition expansion from docs/derivations/heydemann.md Section 4,
    applied here as a transform on an already-generated ideal signal rather
    than baked into the original phi-to-signal equation -- verified
    (pipeline.py's module docstring) to reproduce the combined Heydemann
    formula exactly when composed with amplitude_imbalance in the documented
    order.

    Failure mode: at quadrature_error_rad = +-pi/2, this transform itself is
    well-defined (cos/sin are finite everywhere) -- the singularity Day 2's
    derivation identifies (division by cos(eps)) belongs to the INVERSE
    operation (recovering phase from a distorted signal), not to this
    forward-direction transform. Documented here so a reader doesn't
    mistakenly look for a guard against it in this function.
    """
    i_ac = intensity_i - mean_intensity
    q_ac = intensity_q - mean_intensity
    q_new = (
        mean_intensity
        + np.cos(quadrature_error_rad) * q_ac
        + np.sin(quadrature_error_rad) * i_ac
    )
    return intensity_i, q_new


def dc_offset(
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    dc_offset_i: float,
    dc_offset_q: float,
) -> tuple[FloatArray, FloatArray]:
    """Adds independent constant biases to each channel -- models stray
    light, detector bias voltage, or other per-channel DC contributions.
    `dc_offset_i=dc_offset_q=0.0` is an exact identity (both channels
    returned unchanged).

    Design decision: purely additive, and applied LAST in the documented
    pipeline order (pipeline.py) -- unlike amplitude_imbalance and
    quadrature_phase_error, this transform doesn't multiply or mix with the
    oscillating content, so it commutes with both of them algebraically;
    applied last only to match the natural construction order (build the
    distorted oscillation, then add each channel's bias on top), not because
    the math requires a specific position.

    Failure mode: none -- a pure additive shift has no singularities at any
    parameter value.
    """
    return intensity_i + dc_offset_i, intensity_q + dc_offset_q


def hysteresis(
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    mean_intensity: float,
    hysteresis_magnitude: float,
) -> tuple[FloatArray, FloatArray]:
    """Direction-dependent (path-dependent) radial perturbation, per
    Lehmann et al. 2025's finding (`notes/lehmann_2025.md`, Section IV.A)
    that residual radius deviation traces different paths depending on the
    direction of phase travel. `hysteresis_magnitude=0.0` is an exact
    identity.

    WHY THIS TRANSFORM CANNOT BE PURE POINTWISE, UNLIKE EVERY OTHER
    TRANSFORM IN THIS MODULE: amplitude_imbalance, quadrature_phase_error,
    and dc_offset each compute their output for sample i using ONLY sample
    i's own (I,Q) value -- a static, memoryless mapping. Hysteresis is
    fundamentally different: "direction of travel" is not a property of a
    single point, it's a property of how phase is CHANGING between
    neighboring points. This function must look at the whole array's local
    phase gradient (via np.gradient) to determine, at each sample, whether
    phase is locally increasing or decreasing -- it carries this
    neighbor-dependent state through the whole computation, rather than
    mapping each point independently of its neighbors.

    Model: radius is perturbed by exactly hysteresis_magnitude in the
    direction of local phase travel (angle preserved, only radius changes)
    -- a phase sweep going "up" ends up on a circle/ellipse of radius R+h,
    the same phase values reached while sweeping "down" end up at R-h,
    tracing two visibly different paths through the same phase range. This
    is a deliberately simple model (not derived from a specific numbered
    equation in Lehmann et al., who characterize this qualitatively rather
    than with one closed-form hysteresis equation) chosen because it
    produces the two testable, unambiguous properties this project's
    documentation standard requires: the up and down paths must differ, and
    the loop area between them must scale with `hysteresis_magnitude` --
    both verified empirically in tests/test_hysteresis.py before being
    written into this docstring as fact.

    Failure mode: at a sample where radius is exactly zero (i_ac=q_ac=0),
    "direction preserving angle, perturbing radius" is undefined (a point
    at the origin has no angle) -- guarded by leaving such a sample
    unperturbed rather than dividing by zero. Not expected to occur for any
    realistic non-degenerate oscillating signal (radius is only zero at an
    isolated instant, if ever), so this guard is a robustness safeguard,
    not a case this project's own test data is expected to exercise.
    """
    # ---- 1. Identity case: no path-dependence, no neighbor lookup needed ----
    if hysteresis_magnitude == 0.0:
        return intensity_i, intensity_q

    # ---- 2. AC-centered coordinates ----
    i_ac = intensity_i - mean_intensity
    q_ac = intensity_q - mean_intensity

    # ---- 3. Local direction of phase travel (the neighbor-dependent state) ----
    phase = np.unwrap(np.arctan2(q_ac, i_ac))
    direction = np.sign(np.gradient(phase))

    # ---- 4. Perturb radius by the direction-dependent amount, preserving angle ----
    radius = np.sqrt(i_ac**2 + q_ac**2)
    safe_radius = np.where(radius == 0.0, 1.0, radius)  # guard div-by-zero; unperturbed below
    scale = np.where(radius == 0.0, 1.0, (radius + hysteresis_magnitude * direction) / safe_radius)

    return i_ac * scale + mean_intensity, q_ac * scale + mean_intensity
