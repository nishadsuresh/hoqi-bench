"""
Tests for hoqi_bench.arc.build_arc_ramp: verifies the actual defining
property -- the resulting (I, Q) trajectory, generated via
forward_model.simulate_ideal_interferometer, spans exactly
`arc_fraction * 2*pi` radians of phase -- not just that the ramp's own
formula is self-consistent.

Weeks 1-2 audit (2026-07-26, finding F5): arc_fraction was called "the
single most consequential axis for numerical stability" (Day 3) and appears
in 99 of 359 main-campaign conditions, but had zero implementation anywhere
in src/.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray
from hoqi_bench.arc import build_arc_ramp
from hoqi_bench.forward_model import HENE_WAVELENGTH_M, simulate_ideal_interferometer


def _measured_phase_span(arc_fraction: float, n_points: int = 2000) -> float:
    """Generates the (I, Q) trajectory for a given arc_fraction and measures
    the phase WINDOW it covers, via unwrap(atan2(...)) -- an INDEPENDENT
    measurement of the property build_arc_ramp claims to produce, not a
    restatement of its own formula.

    "Window covered" rather than "last sample minus first sample", updated
    2026-07-27 with `build_arc_ramp`'s `endpoint=False` change (Day 21 --
    see that function's own docstring for why the duplicated full-circle
    sample had to go): the N samples now sit at the left edge of N equal
    sub-intervals, so the window they cover is the first-to-last distance
    PLUS one more sample step. Every assertion below is unchanged and still
    exact -- `arc_fraction` still means exactly what it always meant, and
    the covered window is still exactly `arc_fraction * 2*pi`.
    """
    t, x_true = build_arc_ramp(arc_fraction, n_points)

    def displacement_fn(t_: AnyFloatArray) -> AnyFloatArray:
        return x_true

    intensity_i, intensity_q, _ = simulate_ideal_interferometer(
        t, displacement_fn, mean_intensity=1.0, contrast=0.9
    )
    phase = np.unwrap(np.arctan2(intensity_q - 1.0, intensity_i - 1.0))
    first_to_last = float(phase[-1] - phase[0])
    sample_step = first_to_last / (n_points - 1)
    return first_to_last + sample_step


def test_full_circle_spans_exactly_2pi() -> None:
    span = _measured_phase_span(arc_fraction=1.0)
    assert abs(span - 2 * np.pi) < 1e-6


def test_18_degree_arc_matches_005_fraction() -> None:
    """docs/experimental_design.md's own worked example: arc_fraction=0.05
    is stated to be an 18-degree arc (0.05 * 360 = 18)."""
    span = _measured_phase_span(arc_fraction=0.05)
    assert abs(np.degrees(span) - 18.0) < 1e-6


def test_phase_span_scales_linearly_with_arc_fraction() -> None:
    """Checked across several magnitudes, not just one value -- span/fraction
    must be constant (exactly 2*pi) for every arc_fraction, matching this
    project's documentation standard for verifying linearity claims."""
    fractions = [0.02, 0.1, 0.25, 0.5, 0.75, 1.0]
    for fraction in fractions:
        span = _measured_phase_span(fraction)
        assert abs(span / fraction - 2 * np.pi) < 1e-6


def test_n_points_does_not_change_the_phase_span() -> None:
    """arc_fraction controls how much phase is covered; samples_per_fit (N,
    finding F4) controls how densely that span is sampled -- the two are
    independent axes, and this confirms build_arc_ramp doesn't conflate them."""
    span_60 = _measured_phase_span(arc_fraction=0.5, n_points=60)
    span_1000 = _measured_phase_span(arc_fraction=0.5, n_points=1000)
    assert abs(span_60 - span_1000) < 1e-6


def test_returned_t_and_x_true_have_matching_shape() -> None:
    t, x_true = build_arc_ramp(arc_fraction=0.3, n_points=50)
    assert t.shape == (50,)
    assert x_true.shape == (50,)


def test_custom_wavelength_still_produces_the_requested_arc_fraction() -> None:
    """The phase-excursion property must hold regardless of wavelength_m,
    since arc_fraction is defined in phase (radians), not displacement
    (meters) -- confirms the wavelength inversion in build_arc_ramp is
    exact, not an approximation that happens to work at the HeNe default."""
    custom_wavelength = 1550e-9  # a telecom-band wavelength, not the HeNe default
    n_points = 2000
    t, x_true = build_arc_ramp(
        arc_fraction=0.4, n_points=n_points, wavelength_m=custom_wavelength
    )

    def displacement_fn(t_: AnyFloatArray) -> AnyFloatArray:
        return x_true

    intensity_i, intensity_q, _ = simulate_ideal_interferometer(
        t, displacement_fn, wavelength_m=custom_wavelength, mean_intensity=1.0, contrast=0.9
    )
    phase = np.unwrap(np.arctan2(intensity_q - 1.0, intensity_i - 1.0))
    first_to_last = float(phase[-1] - phase[0])
    covered_window = first_to_last + first_to_last / (n_points - 1)
    assert abs(covered_window - 0.4 * 2 * np.pi) < 1e-6


def test_default_wavelength_matches_forward_model_constant() -> None:
    """build_arc_ramp's default must stay in sync with forward_model's --
    a divergence here would silently produce the wrong arc_fraction for any
    caller relying on the default."""
    assert build_arc_ramp(1.0, 10)[1] is not None  # sanity: doesn't raise
    _, x_true_default = build_arc_ramp(arc_fraction=1.0, n_points=10)
    _, x_true_explicit = build_arc_ramp(
        arc_fraction=1.0, n_points=10, wavelength_m=HENE_WAVELENGTH_M
    )
    assert np.array_equal(x_true_default, x_true_explicit)
