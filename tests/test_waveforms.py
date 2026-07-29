"""
Tests for hoqi_bench.waveforms.build_bidirectional_ramp -- Week 5 Task 4,
Day 32. See `docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 1 for the full,
pre-committed design specification these tests verify against; see that
module's own docstring for why the descending half samples the peak
exactly once (a genuine turning point, not `arc.build_arc_ramp`'s
wraparound duplicate).
"""

from __future__ import annotations

import numpy as np
import pytest

from hoqi_bench.arc import build_arc_ramp
from hoqi_bench.transforms import hysteresis
from hoqi_bench.waveforms import build_bidirectional_ramp


@pytest.mark.parametrize("n_points", [20, 60, 61, 100, 1000])
def test_matches_build_arc_ramp_on_total_sample_count(n_points: int) -> None:
    """The design constraint that makes the RQ3 comparison valid: same N
    as the preregistered monotonic waveform, differing only in path."""
    _, x_mono = build_arc_ramp(0.5, n_points)
    _, x_bi = build_bidirectional_ramp(0.5, n_points)
    assert len(x_mono) == len(x_bi) == n_points


@pytest.mark.parametrize("arc_fraction", [0.02, 0.1, 0.5, 1.0])
def test_peak_is_within_one_sample_step_of_the_nominal_phase_excursion(
    arc_fraction: float,
) -> None:
    """The peak displacement corresponds to phase arc_fraction*2*pi,
    within the one-sample-step tolerance the protocol documents (the
    descending half's first sample IS exactly the nominal peak; converted
    to displacement via the same phase-to-displacement relation
    arc.build_arc_ramp uses, so equality should be exact modulo floating
    point, not merely close)."""
    n_points = 60
    wavelength_m = 632.8e-9
    _, x_bi = build_bidirectional_ramp(arc_fraction, n_points, wavelength_m)
    expected_peak_displacement_m = (arc_fraction * 2 * np.pi) * wavelength_m / (4 * np.pi)
    assert x_bi.max() == pytest.approx(expected_peak_displacement_m, rel=1e-12)


@pytest.mark.parametrize("n_points", [20, 60, 100])
def test_direction_reverses_with_exactly_one_zero_sample_at_even_n(n_points: int) -> None:
    """Direct verification of the property RQ3's whole supplementary
    experiment depends on: unlike the monotonic ramp (direction is +1 at
    100% of samples, docs/PREREGISTRATION.md deviation D5), this waveform
    must contain BOTH +1 and -1 direction samples, roughly balanced."""
    _, x_bi = build_bidirectional_ramp(0.5, n_points)
    direction = np.sign(np.gradient(x_bi))

    assert 1.0 in direction
    assert -1.0 in direction
    frac_negative = float((direction == -1.0).mean())
    assert 0.35 < frac_negative < 0.55, f"direction is not balanced: frac(-1)={frac_negative}"

    # n_points is even in every parametrization above -- exactly one
    # symmetric turning-point sample, never a region.
    zero_indices = np.where(direction == 0.0)[0]
    assert len(zero_indices) == 1
    assert zero_indices[0] == n_points // 2


def test_no_zero_direction_sample_at_odd_n() -> None:
    """The asymmetric ascending/descending split at odd N means the
    turning point is never perfectly symmetric -- confirmed directly
    rather than assumed, per docs/SUPPLEMENTARY_PROTOCOLS.md's own
    statement of this fact."""
    _, x_bi = build_bidirectional_ramp(0.5, 61)
    direction = np.sign(np.gradient(x_bi))
    assert 0.0 not in direction


def test_zero_direction_sample_requires_no_change_to_hysteresis() -> None:
    """Confirms directly (not just asserted in the protocol doc) that
    transforms.hysteresis's EXISTING formula leaves a direction=0 sample
    exactly unperturbed -- the turning point needs no special-case code
    anywhere in this project."""
    n_points = 60
    _, x_bi_any = build_bidirectional_ramp(0.5, n_points)
    x_bi = np.asarray(x_bi_any, dtype=np.float64)  # hysteresis requires float64 strictly
    turning_point_index = n_points // 2

    # A synthetic (I, Q) pair with a nonzero AC radius at the turning
    # point index, everything else held simple.
    mean_intensity = 1.0
    contrast = 0.9
    phase = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    intensity_i = mean_intensity + contrast * np.cos(phase)
    intensity_q = mean_intensity + contrast * np.sin(phase)

    perturbed_i, perturbed_q = hysteresis(
        intensity_i, intensity_q, mean_intensity, hysteresis_magnitude=0.2, true_displacement=x_bi
    )

    assert perturbed_i[turning_point_index] == pytest.approx(
        intensity_i[turning_point_index], abs=1e-15
    )
    assert perturbed_q[turning_point_index] == pytest.approx(
        intensity_q[turning_point_index], abs=1e-15
    )
