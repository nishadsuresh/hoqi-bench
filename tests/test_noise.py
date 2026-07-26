"""Tests for gaussian_noise: empirical variance matches specified sigma,
determinism under a fixed seed, independence between I and Q channels, and
exact identity at noise_std=0."""

from __future__ import annotations

import numpy as np

from hoqi_bench.noise import gaussian_noise


def test_identity_at_zero_noise() -> None:
    intensity_i = np.full(1000, 1.0)
    intensity_q = np.full(1000, 1.0)
    new_i, new_q = gaussian_noise(intensity_i, intensity_q, noise_std=0.0, seed=0)
    assert np.array_equal(new_i, intensity_i)
    assert np.array_equal(new_q, intensity_q)


def test_empirical_variance_matches_specified_sigma() -> None:
    """Over many samples, the ADDED noise's empirical std must match
    noise_std within the statistical tolerance expected for this sample
    size -- the standard error of a sample standard deviation estimate is
    approximately sigma/sqrt(2N), so a 5-sigma tolerance on that quantity is
    a real statistical bound, not an arbitrary tolerance."""
    n_samples = 200_000
    noise_std = 0.05
    baseline = np.ones(n_samples)

    new_i, new_q = gaussian_noise(baseline, baseline, noise_std=noise_std, seed=1)
    added_noise_i = new_i - baseline
    added_noise_q = new_q - baseline

    measured_std_i = np.std(added_noise_i)
    measured_std_q = np.std(added_noise_q)

    standard_error_of_std = noise_std / np.sqrt(2 * n_samples)
    tolerance = 5 * standard_error_of_std

    assert abs(measured_std_i - noise_std) < tolerance
    assert abs(measured_std_q - noise_std) < tolerance


def test_deterministic_given_the_same_seed() -> None:
    baseline = np.ones(500)
    result_a = gaussian_noise(baseline, baseline, noise_std=0.1, seed=42)
    result_b = gaussian_noise(baseline, baseline, noise_std=0.1, seed=42)
    assert np.array_equal(result_a[0], result_b[0])
    assert np.array_equal(result_a[1], result_b[1])


def test_different_seeds_give_different_noise() -> None:
    """A determinism check alone can't catch a bug where the seed is
    silently ignored -- confirm two different seeds actually produce
    different output."""
    baseline = np.ones(500)
    result_a = gaussian_noise(baseline, baseline, noise_std=0.1, seed=1)
    result_b = gaussian_noise(baseline, baseline, noise_std=0.1, seed=2)
    assert not np.array_equal(result_a[0], result_b[0])


def test_i_and_q_noise_are_independent() -> None:
    """I and Q must be perturbed by INDEPENDENT noise draws, not the same
    draw applied to both -- a real bug this specifically guards against:
    accidentally reusing one rng.normal() call's output for both channels,
    which would silently correlate them."""
    n_samples = 100_000
    baseline = np.ones(n_samples)
    new_i, new_q = gaussian_noise(baseline, baseline, noise_std=0.1, seed=3)

    added_noise_i = new_i - baseline
    added_noise_q = new_q - baseline

    correlation = np.corrcoef(added_noise_i, added_noise_q)[0, 1]
    # for independent Gaussian noise, sample correlation ~ N(0, 1/sqrt(N));
    # 5-sigma bound at this sample size
    tolerance = 5 / np.sqrt(n_samples)
    assert abs(correlation) < tolerance
