"""
Tests for fit_power_law_exponent. Since Days 15-20's phase-recovery methods
don't exist yet, real error-vs-distortion-magnitude sweep data can't be
generated -- these tests construct SYNTHETIC data with a KNOWN exponent
(matching this day's instruction to "verify error growth follows the
expected power-law relationship... fit the exponent numerically, check
against the specified value") rather than waiting for Week 3-4's methods.
The real check against Lehmann's actual reported ~3 exponent, on real
recovery-error data, is Day 30's job (RQ3 analysis).
"""

from __future__ import annotations

import numpy as np
import pytest

from hoqi_bench.power_law import fit_power_law_exponent


def test_recovers_known_exponent_from_clean_synthetic_data() -> None:
    """error = 2.5 * magnitude^3.0, no noise -- the fit must recover
    exponent=3.0 and coefficient=2.5 essentially exactly, and r_squared
    must be ~1.0 (a perfect power-law relationship by construction)."""
    magnitudes = np.linspace(0.1, 2.0, 50)
    true_exponent, true_coefficient = 3.0, 2.5
    errors = true_coefficient * magnitudes**true_exponent

    exponent, coefficient, r_squared = fit_power_law_exponent(magnitudes, errors)

    assert abs(exponent - true_exponent) < 1e-6
    assert abs(coefficient - true_coefficient) < 1e-6
    assert r_squared > 0.9999


def test_recovers_known_exponent_with_realistic_noise() -> None:
    """Same known relationship, but with realistic multiplicative noise on
    the errors (errors are always positive and typically noisy
    multiplicatively, not additively, in this kind of data) -- the fit
    should still recover the true exponent within a reasonable tolerance,
    not exactly."""
    rng = np.random.default_rng(0)
    magnitudes = np.linspace(0.1, 2.0, 200)
    true_exponent, true_coefficient = 3.0, 2.5
    clean_errors = true_coefficient * magnitudes**true_exponent
    noisy_errors = clean_errors * rng.lognormal(mean=0, sigma=0.05, size=magnitudes.shape)

    exponent, coefficient, r_squared = fit_power_law_exponent(magnitudes, noisy_errors)

    assert abs(exponent - true_exponent) < 0.1
    assert r_squared > 0.95


def test_recovers_lehmann_reported_exponent_of_approximately_3() -> None:
    """A direct check against the specific value this project's forward
    model is meant to characterize: Lehmann et al. 2025 reports residual
    nonlinearity 'close to power of 3' (notes/lehmann_2025.md). Synthetic
    data built with exponent=3.0 must be correctly identified as
    approximately 3, the actual number this project checks its own sweep
    results against on Day 30."""
    magnitudes = np.geomspace(0.05, 3.0, 40)
    errors = 1.2 * magnitudes**3.0

    exponent, _, r_squared = fit_power_law_exponent(magnitudes, errors)

    assert abs(exponent - 3.0) < 0.05
    assert r_squared > 0.999


def test_rejects_nonpositive_magnitudes_or_errors() -> None:
    """The zero-distortion condition (magnitude=0, and often error=0 too)
    must be excluded by the caller -- this function fails loudly rather
    than silently producing NaN/-inf from log(0)."""
    magnitudes = np.array([0.0, 1.0, 2.0])
    errors = np.array([0.5, 1.0, 2.0])
    with pytest.raises(ValueError, match="strictly positive"):
        fit_power_law_exponent(magnitudes, errors)

    magnitudes2 = np.array([0.5, 1.0, 2.0])
    errors2 = np.array([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="strictly positive"):
        fit_power_law_exponent(magnitudes2, errors2)


def test_flat_relationship_is_correctly_identified_as_not_power_law() -> None:
    """The 'no clean power-law relationship' edge case this project's
    fallback plan depends on being detectable: if error is CONSTANT
    regardless of magnitude (no real relationship at all), the fit must
    report an exponent near 0 (not a spurious ~3) and a low r_squared --
    the actual trigger condition for falling back to the injected-mechanism
    approach (docs/PREREGISTRATION.md revision item 3), not something this
    function should paper over by reporting a falsely confident exponent."""
    rng = np.random.default_rng(1)
    magnitudes = np.linspace(0.1, 2.0, 100)
    # constant error with a little noise -- no real dependence on magnitude
    errors = 1.0 * rng.lognormal(mean=0, sigma=0.3, size=magnitudes.shape)

    exponent, _, r_squared = fit_power_law_exponent(magnitudes, errors)

    assert abs(exponent) < 0.5  # nowhere near Lehmann's reported ~3
    assert r_squared < 0.5  # a poor fit, correctly signaling "not a power law"
