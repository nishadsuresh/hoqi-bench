"""
Tests for the hysteresis transform: verifies the two defining properties
directly -- a phase sweep up and back down does NOT retrace the same
(I,Q) path, and the enclosed loop area scales with the hysteresis
magnitude (confirmed empirically, via a direct numerical check outside
pytest, to be exactly LINEAR before writing the linearity assertion below
-- see docs/journal/day14.md).
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray
from hoqi_bench.forward_model import simulate_ideal_interferometer
from hoqi_bench.transforms import hysteresis


def _up_and_down_iq(
    mean_intensity: float, contrast: float, n_points: int = 5000
) -> tuple[FloatArray, FloatArray]:
    """A displacement that sweeps phase up then back down (two full
    oscillation cycles) -- the minimal case needed to have a genuine
    'direction of travel' to be direction-dependent about."""
    t = np.linspace(0, 1.0, n_points)

    def displacement_fn(t: AnyFloatArray) -> AnyFloatArray:
        return np.asarray(2e-6 * np.sin(2 * np.pi * 2 * t))

    intensity_i, intensity_q, _ = simulate_ideal_interferometer(
        t, displacement_fn, mean_intensity=mean_intensity, contrast=contrast
    )
    return intensity_i, intensity_q


def _shoelace_area(x: FloatArray, y: FloatArray) -> float:
    """Standard polygon-area formula, applied to the closed (I,Q) path --
    a perfectly retraced path (up then down over the SAME points) has zero
    signed area by construction; any real enclosed loop has nonzero area."""
    return float(0.5 * abs(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))


def test_identity_at_zero_hysteresis() -> None:
    mean_intensity, contrast = 1.0, 0.9
    intensity_i, intensity_q = _up_and_down_iq(mean_intensity, contrast)
    new_i, new_q = hysteresis(intensity_i, intensity_q, mean_intensity, hysteresis_magnitude=0.0)
    assert np.array_equal(new_i, intensity_i)
    assert np.array_equal(new_q, intensity_q)


def test_zero_hysteresis_gives_zero_loop_area() -> None:
    """Confirms the shoelace-area method itself is sound: with NO
    hysteresis, the up-and-down path retraces itself exactly, so the
    enclosed area must be exactly (or essentially) zero."""
    mean_intensity, contrast = 1.0, 0.9
    intensity_i, intensity_q = _up_and_down_iq(mean_intensity, contrast)
    area = _shoelace_area(intensity_i - mean_intensity, intensity_q - mean_intensity)
    assert area < 1e-6


def test_nonzero_hysteresis_produces_a_real_loop_area() -> None:
    mean_intensity, contrast = 1.0, 0.9
    intensity_i, intensity_q = _up_and_down_iq(mean_intensity, contrast)
    new_i, new_q = hysteresis(intensity_i, intensity_q, mean_intensity, hysteresis_magnitude=0.05)
    area = _shoelace_area(new_i - mean_intensity, new_q - mean_intensity)
    assert area > 1.0  # a real, substantial enclosed area, not numerical noise near zero


def test_loop_area_scales_linearly_with_hysteresis_magnitude() -> None:
    """Verified empirically (outside pytest, before writing this assertion
    -- docs/journal/day14.md) that loop_area/magnitude is constant across
    several magnitudes for this transform's specific radial-perturbation
    model -- i.e. area scales exactly LINEARLY with magnitude, not just
    monotonically. Checked here across 5 magnitudes, not just two points."""
    mean_intensity, contrast = 1.0, 0.9
    intensity_i, intensity_q = _up_and_down_iq(mean_intensity, contrast)

    magnitudes = [0.01, 0.02, 0.04, 0.08, 0.16]
    areas = []
    for h in magnitudes:
        new_i, new_q = hysteresis(intensity_i, intensity_q, mean_intensity, h)
        areas.append(_shoelace_area(new_i - mean_intensity, new_q - mean_intensity))

    ratios = [area / h for area, h in zip(areas, magnitudes, strict=True)]
    mean_ratio = np.mean(ratios)
    for ratio in ratios:
        assert abs(ratio - mean_ratio) / mean_ratio < 1e-3  # tight: exactly linear by construction


def test_up_pass_and_down_pass_visit_different_iq_points_at_the_same_phase() -> None:
    """The defining property stated most directly: at the SAME phase value,
    reached once on the way up and once on the way down, the (I,Q) point
    must be measurably different when hysteresis is active."""
    mean_intensity, contrast = 1.0, 0.9
    intensity_i, intensity_q = _up_and_down_iq(mean_intensity, contrast)
    new_i, new_q = hysteresis(intensity_i, intensity_q, mean_intensity, hysteresis_magnitude=0.05)

    i_ac = new_i - mean_intensity
    q_ac = new_q - mean_intensity
    phase = np.unwrap(np.arctan2(q_ac, i_ac))
    direction = np.sign(np.gradient(phase))

    radius = np.sqrt(i_ac**2 + q_ac**2)
    # among samples with nearly the same phase, radius should differ
    # depending on direction -- check overall: mean radius when going up
    # vs. mean radius when going down must differ by ~2*hysteresis_magnitude
    up_radius_mean = np.mean(radius[direction > 0])
    down_radius_mean = np.mean(radius[direction < 0])
    assert abs((up_radius_mean - down_radius_mean) - 2 * 0.05) < 0.01
