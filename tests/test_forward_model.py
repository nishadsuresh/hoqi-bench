"""
Day 7 ACCEPTANCE test: the ported ideal forward model must reproduce
quadrature-interferometer-sim's exact Phase 1 result (0.000000% error vs.
lambda/2) on an equivalent test case. If this fails, either the port or the
original is wrong -- investigated, not silently worked around.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks

from hoqi_bench._types import AnyFloatArray
from hoqi_bench.forward_model import HENE_WAVELENGTH_M, simulate_ideal_interferometer


def test_fringe_spacing_matches_lambda_over_2_analytically() -> None:
    """Ported verbatim from quadrature-interferometer-sim's tests/test_phase1.py:
    a known linear displacement ramp (no noise) must produce fringe spacing
    in I(t) matching lambda/2 to well within numerical/discretization
    tolerance."""
    velocity_m_per_s = 5e-6  # 5 um/s
    duration_s = 2.0
    fs = 100_000  # sample rate high enough to resolve fringes cleanly
    t = np.arange(0, duration_s, 1 / fs)

    def displacement_fn(t: AnyFloatArray) -> AnyFloatArray:
        return velocity_m_per_s * t

    intensity_i, _, x_true = simulate_ideal_interferometer(
        t, displacement_fn, contrast=0.9
    )
    # no noise for this test -- checking the clean physics, not noise robustness

    peaks, _ = find_peaks(intensity_i)
    peak_displacements = x_true[peaks]
    fringe_spacings = np.diff(peak_displacements)

    expected_spacing = HENE_WAVELENGTH_M / 2
    mean_spacing = np.mean(fringe_spacings)
    rel_error = abs(mean_spacing - expected_spacing) / expected_spacing

    print(f"Expected fringe spacing (lambda/2): {expected_spacing * 1e9:.4f} nm")
    print(
        f"Measured mean fringe spacing:       {mean_spacing * 1e9:.4f} nm  "
        f"({len(peaks)} fringes)"
    )
    print(f"Relative error: {rel_error:.6%}")

    # quadrature-interferometer-sim's own acceptance bar was <0.1%; this port
    # is held to the same bar, not a looser one.
    assert rel_error < 0.001


def test_ideal_signal_is_a_perfect_circle_in_iq_plane() -> None:
    """A property the original project's own analysis pipeline depends on
    (Kasa circle fit, later ellipse fits): with no distortion, (I,Q) traces
    an exact circle of radius `contrast` centered at (1,1) (given
    mean_intensity=1), for ANY displacement waveform -- not just a ramp."""
    t = np.linspace(0, 1.0, 5000)

    def displacement_fn(t: AnyFloatArray) -> AnyFloatArray:
        return np.asarray(200e-9 * np.sin(2 * np.pi * 3 * t))  # a few fringes of oscillation

    contrast = 0.9
    intensity_i, intensity_q, _ = simulate_ideal_interferometer(
        t, displacement_fn, contrast=contrast
    )

    radius = np.sqrt((intensity_i - 1) ** 2 + (intensity_q - 1) ** 2)
    assert np.allclose(radius, contrast, atol=1e-9)


def test_zero_displacement_gives_constant_phase() -> None:
    """A sanity/degeneracy check the original project didn't have but this
    one should: zero displacement must give a constant, well-defined phase
    (not NaN, not drifting) -- the trivial case every later distortion
    transform's "identity at zero" test builds on."""
    t = np.linspace(0, 1.0, 1000)

    def zero_displacement(t: AnyFloatArray) -> AnyFloatArray:
        return np.zeros_like(t)

    intensity_i, intensity_q, x_true = simulate_ideal_interferometer(
        t, zero_displacement, contrast=0.9
    )
    assert np.all(x_true == 0.0)
    assert np.allclose(intensity_i, 1.9)  # mean_intensity*(1+contrast*cos(0)) = 1*(1+0.9)
    assert np.allclose(intensity_q, 1.0)  # mean_intensity*(1+contrast*sin(0)) = 1*(1+0)
