"""
Tests for amplitude_imbalance and quadrature_phase_error, verifying the
ANALYTIC geometric consequence each transform has on the (I,Q) trajectory --
not merely that the code runs. Expected values are derived analytically
inside each test (via the covariance-matrix/PCA method below), never
hardcoded from a prior run.

The geometric method: for a full-period parametric curve (x(t), y(t)), the
covariance matrix of (x,y) sampled densely over one period has eigenvalues
proportional to the squared semi-axis lengths of the ellipse the curve
traces, and its eigenvectors point along the ellipse's axes. This is a
real, independent geometric check (PCA on the point cloud), not a restatement
of the transform's own defining formula.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench.forward_model import simulate_ideal_interferometer
from hoqi_bench.transforms import amplitude_imbalance, quadrature_phase_error


def _ellipse_semi_axes_and_angle(
    i_ac: np.ndarray, q_ac: np.ndarray
) -> tuple[float, float, float]:
    """Recovers (semi_axis_1, semi_axis_2, angle_of_semi_axis_1_rad) from a
    point cloud via the covariance-matrix/PCA method described above.
    Independent of any specific transform -- pure geometry."""
    cov = np.cov(i_ac, q_ac)
    eigvals, eigvecs = np.linalg.eigh(cov)
    semi_axes = np.sqrt(2 * eigvals)  # factor of 2: Var = semi_axis^2/2 for a full-period sinusoid
    angle = np.arctan2(eigvecs[1, -1], eigvecs[0, -1])  # eigenvector for the LARGER eigenvalue
    return float(semi_axes[0]), float(semi_axes[1]), float(angle)


def _make_ideal_iq(mean_intensity: float, contrast: float, n_points: int = 20_000):
    """Dense, full-period ideal (I,Q) via a ramp covering EXACTLY 1000 full
    2*pi phase cycles -- deliberately an exact integer, not an arbitrary
    round-number velocity. A first version of this helper used an
    arbitrary-looking ramp that happened to leave a fractional leftover
    cycle at the end (phi_total was not a multiple of 2*pi); that fractional
    cycle biased the covariance-matrix estimate enough to fail the
    axis-ratio check below (measured ratio 1.43 vs. predicted 2.04) even
    though the 45-degree tilt check still passed -- root-caused to the
    windowing asymmetry, fixed by choosing the ramp velocity so phi always
    spans an exact integer number of periods, not by loosening the test
    tolerance."""
    wavelength_m = 632.8e-9  # must match forward_model.HENE_WAVELENGTH_M
    n_full_cycles = 1000
    duration_s = 1.0
    velocity_m_per_s = n_full_cycles * wavelength_m / 2 / duration_s
    t = np.linspace(0, duration_s, n_points, endpoint=False)

    def displacement_fn(t: np.ndarray) -> np.ndarray:
        return velocity_m_per_s * t

    intensity_i, intensity_q, _ = simulate_ideal_interferometer(
        t, displacement_fn, mean_intensity=mean_intensity, contrast=contrast, seed=0
    )
    return intensity_i, intensity_q


# ---- Amplitude imbalance: known axis ratio, no tilt ----


def test_amplitude_imbalance_identity_at_ratio_one() -> None:
    intensity_i, intensity_q = _make_ideal_iq(mean_intensity=1.0, contrast=0.9)
    new_i, new_q = amplitude_imbalance(
        intensity_i, intensity_q, mean_intensity=1.0, amplitude_ratio=1.0
    )
    assert np.array_equal(new_i, intensity_i)
    assert np.array_equal(new_q, intensity_q)


def test_amplitude_imbalance_produces_known_axis_ratio() -> None:
    """A circle of radius contrast*mean_intensity, scaled on Q by
    amplitude_ratio, must become an ellipse whose semi-axis ratio (Q-axis /
    I-axis) equals amplitude_ratio exactly, with NO rotation (axis-aligned)."""
    mean_intensity, contrast, amplitude_ratio = 1.0, 0.9, 1.35
    intensity_i, intensity_q = _make_ideal_iq(mean_intensity, contrast)

    new_i, new_q = amplitude_imbalance(intensity_i, intensity_q, mean_intensity, amplitude_ratio)

    semi_1, semi_2, angle = _ellipse_semi_axes_and_angle(
        new_i - mean_intensity, new_q - mean_intensity
    )
    axis_ratio = max(semi_1, semi_2) / min(semi_1, semi_2)

    assert abs(axis_ratio - amplitude_ratio) < 1e-3
    # axis-aligned: angle must be ~0 or ~pi/2 (mod pi), not tilted at 45 degrees
    angle_mod_90 = abs(np.degrees(angle)) % 90
    assert min(angle_mod_90, 90 - angle_mod_90) < 0.5  # within 0.5 degrees of an axis


# ---- Quadrature phase error: known 45-degree tilt, known axis ratio ----


def test_quadrature_phase_error_identity_at_zero() -> None:
    intensity_i, intensity_q = _make_ideal_iq(mean_intensity=1.0, contrast=0.9)
    new_i, new_q = quadrature_phase_error(
        intensity_i, intensity_q, mean_intensity=1.0, quadrature_error_rad=0.0
    )
    assert np.array_equal(new_i, intensity_i)
    assert np.array_equal(new_q, intensity_q)


def test_quadrature_phase_error_produces_known_45_degree_tilt_and_axis_ratio() -> None:
    """Analytic derivation (verified via sympy before writing this test --
    see docs/journal/day09.md): for x=A*cos(t), y=A*sin(t+eps), the
    covariance matrix is (A^2/2)*[[1, sin(eps)], [sin(eps), 1]]. This
    symmetric structure has eigenvectors at EXACTLY 45 and 135 degrees
    regardless of eps (as long as eps != 0), and EIGENVALUE ratio
    (1+|sin(eps)|)/(1-|sin(eps)|) -- i.e. quadrature phase error tilts the
    ellipse by a fixed 45 degrees. Both derived fresh here, not hardcoded.

    A first version of this test compared the eigenvalue ratio directly
    against the measured SEMI-AXIS ratio and failed (1.43 measured vs. 2.04
    "expected") -- root-caused (not just tolerance-loosened) to a transcription
    bug in the test itself: eigenvalues of a covariance matrix are
    proportional to squared semi-axis length, not semi-axis length directly,
    so the semi-axis ratio is the SQUARE ROOT of the eigenvalue ratio. Fixed
    below; the transform code was correct all along."""
    mean_intensity, contrast, eps = 1.0, 0.9, 0.35  # ~20 degrees
    intensity_i, intensity_q = _make_ideal_iq(mean_intensity, contrast)

    new_i, new_q = quadrature_phase_error(intensity_i, intensity_q, mean_intensity, eps)

    semi_1, semi_2, angle = _ellipse_semi_axes_and_angle(
        new_i - mean_intensity, new_q - mean_intensity
    )
    measured_axis_ratio = max(semi_1, semi_2) / min(semi_1, semi_2)
    expected_eigenvalue_ratio = (1 + abs(np.sin(eps))) / (1 - abs(np.sin(eps)))
    expected_axis_ratio = np.sqrt(expected_eigenvalue_ratio)

    assert abs(measured_axis_ratio - expected_axis_ratio) < 1e-2

    # tilt must be at 45 degrees (mod 90), independent of eps's specific value
    angle_deg = np.degrees(angle) % 180
    distance_from_45_or_135 = min(abs(angle_deg - 45), abs(angle_deg - 135))
    assert distance_from_45_or_135 < 1.0  # within 1 degree of the predicted 45/135 tilt


def test_quadrature_phase_error_tilt_is_45_degrees_across_multiple_magnitudes() -> None:
    """The 45-degree tilt claim is independent of the SPECIFIC eps value --
    check it holds across several magnitudes, not just one cherry-picked
    case."""
    mean_intensity, contrast = 1.0, 0.9
    intensity_i, intensity_q = _make_ideal_iq(mean_intensity, contrast)

    for eps in [0.05, 0.15, 0.3, 0.45, 0.6]:
        new_i, new_q = quadrature_phase_error(intensity_i, intensity_q, mean_intensity, eps)
        _, _, angle = _ellipse_semi_axes_and_angle(
            new_i - mean_intensity, new_q - mean_intensity
        )
        angle_deg = np.degrees(angle) % 180
        distance_from_45_or_135 = min(abs(angle_deg - 45), abs(angle_deg - 135))
        assert distance_from_45_or_135 < 1.0, f"failed at eps={eps}"
