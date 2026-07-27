"""
Day 10 KEYSTONE VALIDATION: for ANY combination of amplitude imbalance,
quadrature phase error, and DC offset applied together (not each tested only
in isolation, as Day 9 did), the resulting (I,Q) point cloud's geometric
parameters -- center, semi-axes, rotation -- must match closed-form
predictions derived from the injected parameter values.

Why this is the most important test in the forward model: Day 9 tested each
distortion transform ALONE, which cannot catch a bug that only appears when
transforms interact -- e.g. a wrong composition order (Day 8 found exactly
this kind of bug for two transforms; there's no guarantee a similar bug
doesn't exist for the three-way combination), an off-by-one in how one
transform reads the OUTPUT of another rather than the original ideal signal,
or a sign error that happens to cancel out when a distortion is tested in
isolation but not when combined with another. If this test passes, every
later distortion transform (Days 11-14) and every method that consumes their
combined output (Days 15-20) is built on a forward model that has been
checked as a WHOLE, not just as a collection of independently-correct parts.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray
from hoqi_bench.forward_model import HENE_WAVELENGTH_M, simulate_ideal_interferometer
from hoqi_bench.transforms import amplitude_imbalance, dc_offset, quadrature_phase_error


def _make_ideal_iq(
    mean_intensity: float, contrast: float, n_points: int = 20_000
) -> tuple[FloatArray, FloatArray]:
    """Ramp covering exactly 1000 full 2*pi phase cycles -- see
    tests/test_transforms.py's docstring for why an exact integer cycle
    count matters for a clean covariance estimate (a fractional leftover
    cycle biases the estimate enough to fail a tight geometric check)."""
    n_full_cycles = 1000
    duration_s = 1.0
    velocity_m_per_s = n_full_cycles * HENE_WAVELENGTH_M / 2 / duration_s
    t = np.linspace(0, duration_s, n_points, endpoint=False)

    def displacement_fn(t: AnyFloatArray) -> AnyFloatArray:
        return velocity_m_per_s * t

    intensity_i, intensity_q, _ = simulate_ideal_interferometer(
        t, displacement_fn, mean_intensity=mean_intensity, contrast=contrast
    )
    return intensity_i, intensity_q


def _predicted_covariance(amplitude: float, amplitude_ratio: float, eps: float) -> FloatArray:
    """Closed-form covariance matrix for x=A*cos(t), y=g*A*sin(t+eps),
    derived via sympy integration over a full period before this test was
    written (docs/journal/day10.md): Cov = (A^2/2)*[[1, g*sin(eps)],
    [g*sin(eps), g^2]]."""
    a2_half = amplitude**2 / 2
    g = amplitude_ratio
    return np.array(
        [[a2_half, a2_half * g * np.sin(eps)], [a2_half * g * np.sin(eps), a2_half * g**2]]
    )


def test_combined_distortion_matches_closed_form_geometric_prediction() -> None:
    """Apply quadrature_phase_error, then amplitude_imbalance, then
    dc_offset (the documented, verified pipeline order) with a
    non-degenerate combination of all three parameters at once, and check
    the resulting point cloud's center and covariance-derived shape against
    closed-form predictions -- not against what the transforms themselves
    would compute (that would just be re-deriving the same formula), but
    against an INDEPENDENT geometric measurement of the actual output data."""
    mean_intensity, contrast = 1.0, 0.9
    amplitude = mean_intensity * contrast  # the oscillation amplitude A
    amplitude_ratio = 1.25
    quadrature_error_rad = 0.4
    offset_i, offset_q = 0.15, -0.22

    intensity_i, intensity_q = _make_ideal_iq(mean_intensity, contrast)

    # documented, verified pipeline order (pipeline.py)
    i1, q1 = quadrature_phase_error(intensity_i, intensity_q, mean_intensity, quadrature_error_rad)
    i2, q2 = amplitude_imbalance(i1, q1, mean_intensity, amplitude_ratio)
    i3, q3 = dc_offset(i2, q2, offset_i, offset_q)

    # ---- Center check: closed-form is trivial (a full-period average of
    # cos/sin is exactly zero, so the center is just mean_intensity + offset) ----
    measured_center_i = np.mean(i3)
    measured_center_q = np.mean(q3)
    predicted_center_i = mean_intensity + offset_i
    predicted_center_q = mean_intensity + offset_q

    assert abs(measured_center_i - predicted_center_i) < 1e-6
    assert abs(measured_center_q - predicted_center_q) < 1e-6

    # ---- Shape check: covariance of the DC-and-offset-removed signal must
    # match the closed-form prediction exactly ----
    i_ac = i3 - measured_center_i
    q_ac = q3 - measured_center_q
    measured_cov = np.cov(i_ac, q_ac)
    predicted_cov = _predicted_covariance(amplitude, amplitude_ratio, quadrature_error_rad)

    np.testing.assert_allclose(measured_cov, predicted_cov, atol=1e-3)


def test_combined_distortion_at_all_zero_is_bit_identical_to_ideal() -> None:
    """Identity-at-zero, but for the COMBINED pipeline, not each transform
    individually (Day 9 already checked each alone) -- amplitude_ratio=1.0,
    quadrature_error_rad=0.0, offsets=0.0 together must reproduce the exact
    ideal signal, bit-for-bit."""
    mean_intensity, contrast = 1.0, 0.9
    intensity_i, intensity_q = _make_ideal_iq(mean_intensity, contrast)

    i1, q1 = quadrature_phase_error(intensity_i, intensity_q, mean_intensity, 0.0)
    i2, q2 = amplitude_imbalance(i1, q1, mean_intensity, 1.0)
    i3, q3 = dc_offset(i2, q2, 0.0, 0.0)

    assert np.array_equal(i3, intensity_i)
    assert np.array_equal(q3, intensity_q)


def test_combined_distortion_across_multiple_parameter_combinations() -> None:
    """The single combination above could pass by coincidence -- check
    several distinct, non-trivial parameter combinations, not just one."""
    mean_intensity, contrast = 1.0, 0.9
    amplitude = mean_intensity * contrast
    intensity_i, intensity_q = _make_ideal_iq(mean_intensity, contrast)

    combinations = [
        (1.1, 0.1, 0.02, -0.01),
        (0.8, -0.2, -0.05, 0.03),
        (1.5, 0.35, 0.1, 0.1),
        (1.0, 0.0, 0.2, -0.2),  # amplitude_ratio=1 (identity), only offsets/eps vary
    ]

    for amplitude_ratio, eps, off_i, off_q in combinations:
        i1, q1 = quadrature_phase_error(intensity_i, intensity_q, mean_intensity, eps)
        i2, q2 = amplitude_imbalance(i1, q1, mean_intensity, amplitude_ratio)
        i3, q3 = dc_offset(i2, q2, off_i, off_q)

        center_i, center_q = np.mean(i3), np.mean(q3)
        assert abs(center_i - (mean_intensity + off_i)) < 1e-6
        assert abs(center_q - (mean_intensity + off_q)) < 1e-6

        cov = np.cov(i3 - center_i, q3 - center_q)
        predicted = _predicted_covariance(amplitude, amplitude_ratio, eps)
        np.testing.assert_allclose(
            cov, predicted, atol=1e-3,
            err_msg=f"failed for amplitude_ratio={amplitude_ratio}, eps={eps}",
        )
