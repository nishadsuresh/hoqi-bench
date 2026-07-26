"""Tests for gaussian_noise: empirical variance matches specified sigma,
determinism under a fixed seed, independence between I and Q channels, and
exact identity at noise_std=0."""

from __future__ import annotations

import numpy as np

from hoqi_bench.noise import gaussian_noise, poisson_noise


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


# ---- Poisson shot noise: the physically correct, signal-dependent model ----


def test_poisson_identity_at_none() -> None:
    intensity_i = np.full(1000, 1.0)
    intensity_q = np.full(1000, 1.0)
    new_i, new_q = poisson_noise(intensity_i, intensity_q, photon_scale=None, seed=0)
    assert np.array_equal(new_i, intensity_i)
    assert np.array_equal(new_q, intensity_q)


def test_poisson_variance_is_proportional_to_intensity() -> None:
    """THE defining physical property of shot noise, checked directly: at a
    fixed photon_scale, the noise variance (in intensity units) must scale
    LINEARLY with intensity -- i.e. variance/intensity must be
    approximately constant (equal to 1/photon_scale) across several
    different intensity levels, not just correct at one arbitrarily chosen
    level."""
    photon_scale = 1_000_000.0
    n_samples = 50_000
    intensity_levels = [0.2, 0.5, 1.0, 1.5, 1.9]  # spans this simulator's realistic I/Q range

    measured_variance_over_intensity = []
    for level in intensity_levels:
        baseline = np.full(n_samples, level)
        new_i, _ = poisson_noise(baseline, baseline, photon_scale=photon_scale, seed=7)
        added_noise = new_i - baseline
        measured_variance_over_intensity.append(np.var(added_noise) / level)

    expected_ratio = 1.0 / photon_scale
    for level, ratio in zip(intensity_levels, measured_variance_over_intensity, strict=True):
        rel_error = abs(ratio - expected_ratio) / expected_ratio
        assert rel_error < 0.05, f"failed at intensity={level}: rel_error={rel_error:.3f}"


def test_poisson_noise_deterministic_given_the_same_seed() -> None:
    baseline = np.full(500, 1.0)
    result_a = poisson_noise(baseline, baseline, photon_scale=10_000.0, seed=42)
    result_b = poisson_noise(baseline, baseline, photon_scale=10_000.0, seed=42)
    assert np.array_equal(result_a[0], result_b[0])
    assert np.array_equal(result_a[1], result_b[1])


def test_poisson_noise_converges_to_gaussian_shape_at_high_photon_count() -> None:
    """A real physics check, not just a code-ran check: the Central Limit
    Theorem guarantees Poisson(lambda) approaches a Gaussian SHAPE as
    lambda grows (its skewness is exactly 1/sqrt(lambda), which -> 0).
    Confirms the implementation genuinely behaves like Poisson noise --
    not, for instance, a fixed-shape noise source that happens to have the
    right variance scaling but the wrong distribution shape -- by checking
    skewness actually decreases as photon_scale (and therefore lambda)
    increases, across several increasing scales."""
    from scipy.stats import skew

    n_samples = 200_000
    intensity_level = 1.0
    baseline = np.full(n_samples, intensity_level)

    photon_scales = [10.0, 100.0, 1_000.0, 100_000.0]
    measured_skewness = []
    for scale in photon_scales:
        new_i, _ = poisson_noise(baseline, baseline, photon_scale=scale, seed=11)
        added_noise = new_i - baseline
        measured_skewness.append(abs(skew(added_noise)))

    # skewness must be monotonically (non-strictly) decreasing as lambda grows,
    # with small slack for finite-sample noise in the skewness estimate itself.
    # NOT strict=True: consecutive-pair zip is intentionally offset by one.
    for earlier, later in zip(measured_skewness, measured_skewness[1:]):  # noqa: B905
        assert later <= earlier * 1.1

    # and the largest photon_scale must be close to Gaussian (skewness ~ 0)
    assert measured_skewness[-1] < 0.05
