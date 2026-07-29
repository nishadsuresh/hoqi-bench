"""
Tests for hoqi_bench.fisher_information -- Week 5 Task 5, Day 33.
Oracle-independent per this project's convention: reference values are
computed directly from the closed-form derivatives in this file, not
imported from the module under test.
"""

from __future__ import annotations

import numpy as np
import pytest

from hoqi_bench.fisher_information import (
    total_fisher_information_gaussian,
    total_fisher_information_poisson,
)

BASELINE_MEAN_INTENSITY = 1.0
BASELINE_CONTRAST = 0.9
BASELINE_AMPLITUDE_RATIO = 1.1
BASELINE_QUADRATURE_ERROR_RAD = 0.1


def test_gaussian_fisher_information_is_infinite_at_zero_noise() -> None:
    phi = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    fi = total_fisher_information_gaussian(
        phi,
        BASELINE_MEAN_INTENSITY,
        BASELINE_CONTRAST,
        BASELINE_AMPLITUDE_RATIO,
        BASELINE_QUADRATURE_ERROR_RAD,
        noise_std_absolute=0.0,
    )
    assert fi == float("inf")


def test_gaussian_fisher_information_scales_as_inverse_variance() -> None:
    """FI = sum((dI/dphi)^2 + (dQ/dphi)^2) / sigma^2 -- halving sigma must
    exactly quadruple FI, independent of the derivative terms."""
    phi = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    fi_sigma_1 = total_fisher_information_gaussian(
        phi,
        BASELINE_MEAN_INTENSITY,
        BASELINE_CONTRAST,
        BASELINE_AMPLITUDE_RATIO,
        BASELINE_QUADRATURE_ERROR_RAD,
        noise_std_absolute=0.02,
    )
    fi_sigma_half = total_fisher_information_gaussian(
        phi,
        BASELINE_MEAN_INTENSITY,
        BASELINE_CONTRAST,
        BASELINE_AMPLITUDE_RATIO,
        BASELINE_QUADRATURE_ERROR_RAD,
        noise_std_absolute=0.01,
    )
    assert fi_sigma_half == pytest.approx(4 * fi_sigma_1, rel=1e-9)


def test_gaussian_fisher_information_matches_direct_derivative_sum() -> None:
    """Reconstructs the reference sum directly (oracle-independent),
    rather than trusting the module's own internal arithmetic."""
    phi = np.array([0.0, np.pi / 4, np.pi / 2, np.pi, 3 * np.pi / 2])
    amplitude = BASELINE_MEAN_INTENSITY * BASELINE_CONTRAST
    di_dphi = -amplitude * np.sin(phi)
    dq_dphi = amplitude * BASELINE_AMPLITUDE_RATIO * np.cos(phi + BASELINE_QUADRATURE_ERROR_RAD)
    sigma = 0.03
    expected = float(np.sum((di_dphi**2 + dq_dphi**2) / sigma**2))

    actual = total_fisher_information_gaussian(
        phi,
        BASELINE_MEAN_INTENSITY,
        BASELINE_CONTRAST,
        BASELINE_AMPLITUDE_RATIO,
        BASELINE_QUADRATURE_ERROR_RAD,
        noise_std_absolute=sigma,
    )
    assert actual == pytest.approx(expected, rel=1e-12)


def test_poisson_fisher_information_matches_direct_derivative_sum() -> None:
    """Same oracle-independence check for the signal-dependent (Poisson)
    case -- the reference sum uses phi-DEPENDENT variance, reconstructed
    here from noise.py's own documented Var = intensity/photon_scale."""
    phi = np.array([0.0, np.pi / 4, np.pi / 2, np.pi, 3 * np.pi / 2])
    amplitude = BASELINE_MEAN_INTENSITY * BASELINE_CONTRAST
    intensity = BASELINE_MEAN_INTENSITY + amplitude * np.cos(phi)
    quadrature = BASELINE_MEAN_INTENSITY + amplitude * BASELINE_AMPLITUDE_RATIO * np.sin(
        phi + BASELINE_QUADRATURE_ERROR_RAD
    )
    di_dphi = -amplitude * np.sin(phi)
    dq_dphi = amplitude * BASELINE_AMPLITUDE_RATIO * np.cos(phi + BASELINE_QUADRATURE_ERROR_RAD)
    photon_scale = 5000.0
    expected = float(
        np.sum(di_dphi**2 / (intensity / photon_scale) + dq_dphi**2 / (quadrature / photon_scale))
    )

    actual = total_fisher_information_poisson(
        phi,
        BASELINE_MEAN_INTENSITY,
        BASELINE_CONTRAST,
        BASELINE_AMPLITUDE_RATIO,
        BASELINE_QUADRATURE_ERROR_RAD,
        photon_scale=photon_scale,
    )
    assert actual == pytest.approx(expected, rel=1e-12)


def test_poisson_fisher_information_increases_with_photon_scale() -> None:
    """More photons (higher photon_scale) means less relative shot noise,
    so Fisher information must increase monotonically."""
    phi = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    fi_values = [
        total_fisher_information_poisson(
            phi,
            BASELINE_MEAN_INTENSITY,
            BASELINE_CONTRAST,
            BASELINE_AMPLITUDE_RATIO,
            BASELINE_QUADRATURE_ERROR_RAD,
            photon_scale=p,
        )
        for p in [100, 1000, 10000, 100000]
    ]
    assert fi_values == sorted(fi_values)


def test_channels_stay_positive_at_the_rq4_shared_baseline() -> None:
    """Pins the fact this module's own docstring depends on: at
    amplitude_ratio=1.1 (RQ4's shared baseline, not swept by either noise
    axis), both I and Q stay strictly positive across a full cycle, so
    the Poisson variance (intensity/photon_scale) never goes non-positive
    -- verified here so a future baseline change that violates this is
    caught, not silently producing NaN Fisher information.
    """
    phi = np.linspace(0, 2 * np.pi, 1000)
    amplitude = BASELINE_MEAN_INTENSITY * BASELINE_CONTRAST
    intensity = BASELINE_MEAN_INTENSITY + amplitude * np.cos(phi)
    quadrature = BASELINE_MEAN_INTENSITY + amplitude * BASELINE_AMPLITUDE_RATIO * np.sin(
        phi + BASELINE_QUADRATURE_ERROR_RAD
    )
    assert (intensity > 0).all()
    assert (quadrature > 0).all()
