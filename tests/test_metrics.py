"""
Tests for hoqi_bench.metrics.wrapped_phase_error: the case a naive linear
difference gets wrong is the whole point of this module, so it's the first
thing tested.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench.metrics import wrapped_phase_error


def test_naive_difference_would_overstate_error_across_the_wrap_boundary() -> None:
    """true=pi-0.01, recovered=-pi+0.01: these are actually 0.02 rad apart
    (adjacent across the wrap), but a naive linear difference reports
    ~2*pi. This is the exact failure the council's peer review flagged."""
    true_phase = np.array([np.pi - 0.01])
    recovered_phase = np.array([-np.pi + 0.01])

    naive_diff = recovered_phase - true_phase
    assert abs(naive_diff[0]) > 6.0  # the wrong answer, ~2*pi

    correct_error = wrapped_phase_error(true_phase, recovered_phase)
    assert abs(correct_error[0] - 0.02) < 1e-9


def test_zero_error_when_phases_match_exactly() -> None:
    true_phase = np.array([0.0, 1.5, -2.7, np.pi])
    assert np.allclose(wrapped_phase_error(true_phase, true_phase), 0.0)


def test_error_is_signed_not_absolute() -> None:
    true_phase = np.array([0.0, 0.0])
    recovered_phase = np.array([0.1, -0.1])
    error = wrapped_phase_error(true_phase, recovered_phase)
    assert error[0] > 0
    assert error[1] < 0


def test_output_is_always_within_the_wrapped_range() -> None:
    """For arbitrary large differences (simulating a badly wrong method),
    the wrapped error must always land in (-pi, pi]."""
    rng = np.random.default_rng(0)
    true_phase = rng.uniform(-100, 100, size=1000)
    recovered_phase = rng.uniform(-100, 100, size=1000)
    error = wrapped_phase_error(true_phase, recovered_phase)
    assert np.all(error > -np.pi - 1e-9)
    assert np.all(error <= np.pi + 1e-9)


def test_small_errors_away_from_the_wrap_boundary_are_unaffected() -> None:
    """Confirms wrapping doesn't distort ordinary, non-boundary errors --
    away from +-pi, wrapped error must equal the naive linear difference."""
    true_phase = np.array([0.0, 1.0, -1.5])
    recovered_phase = true_phase + np.array([0.05, -0.02, 0.01])
    error = wrapped_phase_error(true_phase, recovered_phase)
    assert np.allclose(error, np.array([0.05, -0.02, 0.01]))
