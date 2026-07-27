"""
Tests for hoqi_bench.methods.halir_flusser -- Method 4 (Day 18).

Per docs/WEEK3-4_PLAN.md Day 18: validate against synthetic ellipses with
known analytic parameters (center, semi-axes, tilt must match to near
machine precision on well-conditioned data), then re-run Day 3's
degenerate cases (scripts/explore_ellipse_constraints.py) and confirm this
implementation survives the conditioning that broke the naive Fitzgibbon
formulation.

The ellipse generator and conic-coefficient comparison below are
independent reconstructions of scripts/explore_ellipse_constraints.py's
own TrueEllipse/true_conic_coefficients/normalized_coefficient_error (not
imported -- scripts/ isn't on pytest's pythonpath, and per this project's
own oracle-independence convention, a test's reference should not share
code with what it's checking anyway).
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods.halir_flusser import _fit_ellipse_conic, fit


def _sample_ellipse(
    center_x: float,
    center_y: float,
    semi_major: float,
    semi_minor: float,
    rotation_rad: float,
    n_points: int,
    arc_start_rad: float,
    arc_end_rad: float,
    noise_std: float,
    seed: int,
) -> tuple[FloatArray, FloatArray]:
    rng = np.random.default_rng(seed)
    theta = np.linspace(arc_start_rad, arc_end_rad, n_points)
    ex = semi_major * np.cos(theta)
    ey = semi_minor * np.sin(theta)
    cos_r, sin_r = np.cos(rotation_rad), np.sin(rotation_rad)
    x = center_x + ex * cos_r - ey * sin_r
    y = center_y + ex * sin_r + ey * cos_r
    x = x + rng.normal(0, noise_std, size=n_points)
    y = y + rng.normal(0, noise_std, size=n_points)
    return x, y


def _true_conic_coefficients(
    center_x: float, center_y: float, semi_major: float, semi_minor: float, rotation_rad: float
) -> FloatArray:
    cos_r, sin_r = np.cos(rotation_rad), np.sin(rotation_rad)
    p, q = 1 / semi_major**2, 1 / semi_minor**2
    a = p * cos_r**2 + q * sin_r**2
    b = 2 * (p - q) * cos_r * sin_r
    c = p * sin_r**2 + q * cos_r**2
    d = -2 * a * center_x - b * center_y
    e = -b * center_x - 2 * c * center_y
    f = a * center_x**2 + b * center_x * center_y + c * center_y**2 - 1
    return np.array([a, b, c, d, e, f])


def _normalized_coefficient_error(fitted: FloatArray, true_coeffs: FloatArray) -> float:
    """Ellipse conics are defined only up to an overall scale -- normalize
    both to unit norm before comparing, matching Day 3's own methodology."""
    fitted_n = fitted / np.linalg.norm(fitted)
    true_n = true_coeffs / np.linalg.norm(true_coeffs)
    # Sign is also ambiguous (a and -a represent the same conic) -- pick
    # whichever sign minimizes the distance.
    return float(min(np.linalg.norm(fitted_n - true_n), np.linalg.norm(fitted_n + true_n)))


# Day 3's exact five-regime conditioning spectrum
# (scripts/explore_ellipse_constraints.py's build_conditioning_spectrum),
# reconstructed here rather than imported.
_BASE = dict(center_x=2.0, center_y=-1.0, semi_major=5.0, semi_minor=4.0, rotation_rad=0.3)
_THIN = dict(center_x=2.0, center_y=-1.0, semi_major=8.0, semi_minor=0.4, rotation_rad=0.3)
_VERY_THIN = dict(center_x=2.0, center_y=-1.0, semi_major=8.0, semi_minor=0.05, rotation_rad=0.3)

# Failure rates Day 3's original study documented at each regime
# (docs/journal/day03.md), reproduced here as the grounded expectation --
# NOT "zero everywhere," which a first draft of this test assumed and was
# wrong about (see test_survives_day3_degenerate_regimes's own docstring).
_REGIMES = {
    "well_conditioned": (
        dict(**_BASE, n_points=60, arc_start_rad=0, arc_end_rad=2 * np.pi, noise_std=0.02),
        0.0,
    ),
    "high_eccentricity": (
        dict(**_THIN, n_points=60, arc_start_rad=0, arc_end_rad=2 * np.pi, noise_std=0.02),
        0.0,
    ),
    "partial_arc_30deg": (
        dict(**_BASE, n_points=60, arc_start_rad=0, arc_end_rad=np.pi / 6, noise_std=0.02),
        0.0,
    ),
    "tight_clustering_3deg": (
        dict(**_BASE, n_points=60, arc_start_rad=0.7, arc_end_rad=0.75, noise_std=0.02),
        0.0,
    ),
    "near_degenerate_15deg": (
        dict(
            **_VERY_THIN, n_points=60, arc_start_rad=0, arc_end_rad=np.deg2rad(15), noise_std=0.001
        ),
        0.60,
    ),
}


def test_recovers_known_ellipse_to_near_machine_precision() -> None:
    """Well-conditioned regime: fitted conic coefficients (normalized)
    must match the true ellipse's conic coefficients to near machine
    precision -- this IS the "center, semi-axes, tilt match" claim, since
    the full conic uniquely determines all three."""
    x, y = _sample_ellipse(
        **_BASE, n_points=200, arc_start_rad=0, arc_end_rad=2 * np.pi, noise_std=0.0, seed=0
    )
    conic = _fit_ellipse_conic(x, y)
    assert conic is not None

    true_coeffs = _true_conic_coefficients(
        _BASE["center_x"],
        _BASE["center_y"],
        _BASE["semi_major"],
        _BASE["semi_minor"],
        _BASE["rotation_rad"],
    )
    error = _normalized_coefficient_error(np.array(conic), true_coeffs)
    assert error < 1e-6, f"normalized coefficient error: {error:.2e}"


def test_survives_day3_degenerate_regimes() -> None:
    """Re-runs Day 3's exact conditioning spectrum (30 seeds/regime,
    matching the original study) and confirms this implementation's
    failure rate REPRODUCES Day 3's own documented numbers
    (docs/journal/day03.md), not a naive "zero everywhere" assumption.

    A first draft of this test assumed Halir & Flusser should never fail,
    reasoning "fixing the sign-scanning ambiguity is the whole point of
    the paper" -- and got 18/30 (60%) failures at near_degenerate_15deg,
    which looked like a bug. It is not: Day 3's ORIGINAL study documented
    the exact same 60% H&F failure rate at this exact regime (Fitzgibbon
    was actually BETTER there, 0% -- WEEK3_METHOD_CONTRACT.md sec3.2
    already anticipates methods diverging in ill-conditioned regimes, not
    H&F uniformly winning). The block decomposition fixes the SPECIFIC
    sign-scanning bug that made Fitzgibbon look worse than it truly is
    (Day 3's main finding) -- it does not make ellipse fitting itself
    robust at 15 degrees of a 160:1-eccentricity ellipse under any
    formulation. Reproducing 60% here is confirmation of a known result,
    not a new defect."""
    for regime_name, (params, expected_fail_rate) in _REGIMES.items():
        fail_count = 0
        for seed in range(30):
            x, y = _sample_ellipse(**params, seed=seed)
            conic = _fit_ellipse_conic(x, y)
            if conic is None or not all(np.isfinite(v) for v in conic):
                fail_count += 1
        observed_rate = fail_count / 30
        # +-20 percentage points: real margin for seed-count variability
        # while still confirming the documented order of magnitude.
        assert abs(observed_rate - expected_fail_rate) < 0.20, (
            f"{regime_name}: observed {observed_rate:.2%} fail rate, "
            f"expected ~{expected_fail_rate:.0%} per docs/journal/day03.md"
        )


def test_recovers_known_distortion_via_full_fit() -> None:
    """End-to-end sanity check through the real fit() (not just the conic
    stage): on a real campaign-shaped distorted signal, recovered params
    should be close to the true amplitude_ratio/quadrature_error_rad --
    same axis and same expected residual bias documented in Day 17's
    Heydemann journal entry (this method shares the identical post-fit
    conversion, so the same build_arc_ramp endpoint=True bias applies)."""
    from pathlib import Path

    from hoqi_bench.config import load_sweep_config
    from hoqi_bench.resolve import iter_conditions
    from hoqi_bench.simulate import simulate_condition

    config = load_sweep_config(Path(__file__).parent.parent / "configs" / "main_campaign.toml")
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:quadrature_error_rad=0.3"].resolved

    signal = simulate_condition(resolved, "axis:quadrature_error_rad=0.3", seed_index=0)
    result = fit(signal.i, signal.q)

    assert result.failed is False
    assert result.params is not None
    rel_error_eps = abs(
        result.params["quadrature_error_rad"] - resolved["quadrature_error_rad"]
    ) / resolved["quadrature_error_rad"]
    assert rel_error_eps < 0.02, f"eps recovery: {rel_error_eps:.4f} relative error"
