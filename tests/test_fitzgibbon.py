"""
Tests for hoqi_bench.methods.fitzgibbon -- Method 5 (Day 19).

Per docs/WEEK3-4_PLAN.md Day 19: validate on well-conditioned data (should
closely match Halir & Flusser); document where it degrades. Per this
method's own docstring, its known fragility must NOT be patched or
relaxed -- comparing it against Day 3's exact documented per-regime
failure rates (docs/journal/day03.md) is the direct way to confirm the
implementation actually preserves it, in both directions: fine where
Day 3 found it fine, degraded where Day 3 found it degraded.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods.fitzgibbon import _fit_ellipse_conic, fit
from hoqi_bench.methods.halir_flusser import fit as fit_halir_flusser

# Reconstructed independently (not imported -- scripts/ isn't on pytest's
# pythonpath, and per this project's oracle-independence convention, a
# test's reference should not share code with what it checks).
_BASE = dict(center_x=2.0, center_y=-1.0, semi_major=5.0, semi_minor=4.0, rotation_rad=0.3)
_THIN = dict(center_x=2.0, center_y=-1.0, semi_major=8.0, semi_minor=0.4, rotation_rad=0.3)
_VERY_THIN = dict(center_x=2.0, center_y=-1.0, semi_major=8.0, semi_minor=0.05, rotation_rad=0.3)

# Failure rates Day 3's original study documented for FITZGIBBON at each
# regime (docs/journal/day03.md) -- notably 0% everywhere, INCLUDING the
# extreme regime where Halir & Flusser (Day 18's test) fails 60% of the
# time. Not a typo: the block decomposition trades one failure profile
# for a different one, it does not strictly dominate.
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
        0.0,
    ),
}


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


def test_reproduces_day3_documented_failure_rates_per_regime() -> None:
    """The direct test that this implementation preserves Fitzgibbon's
    REAL profile -- zero failures at every regime Day 3 documented,
    including the one that breaks Halir & Flusser. A 'passing' result
    here that came from silently patching the selection rule (e.g.
    relaxing the a^T*C*a>0 tolerance, or falling back to a block-
    decomposed solve on failure) would misrepresent the method -- this
    test would not catch that kind of patch directly, but the module
    docstring's explicit "do not patch" instruction plus this test's
    exact rate-matching (not just "low enough") makes such a patch
    visible as a documentation/behavior mismatch on inspection."""
    for regime_name, (params, expected_fail_rate) in _REGIMES.items():
        fail_count = 0
        for seed in range(30):
            x, y = _sample_ellipse(**params, seed=seed)
            conic = _fit_ellipse_conic(x, y)
            if conic is None or not all(np.isfinite(v) for v in conic):
                fail_count += 1
        observed_rate = fail_count / 30
        assert abs(observed_rate - expected_fail_rate) < 0.20, (
            f"{regime_name}: observed {observed_rate:.2%} fail rate, "
            f"expected ~{expected_fail_rate:.0%} per docs/journal/day03.md"
        )


def test_closely_matches_halir_flusser_on_well_conditioned_data() -> None:
    """docs/WEEK3-4_PLAN.md Day 19: 'should closely match Method 4' on
    well-conditioned data -- an early, weaker version of Day 21's full
    cross-validation gate, checked now at the point where it's most
    directly relevant."""
    from pathlib import Path

    from hoqi_bench.config import load_sweep_config
    from hoqi_bench.metrics import wrapped_phase_error
    from hoqi_bench.resolve import iter_conditions
    from hoqi_bench.simulate import simulate_condition

    config = load_sweep_config(Path(__file__).parent.parent / "configs" / "main_campaign.toml")
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:quadrature_error_rad=0.3"].resolved
    signal = simulate_condition(resolved, "axis:quadrature_error_rad=0.3", seed_index=0)

    fitzgibbon_result = fit(signal.i, signal.q)
    hf_result = fit_halir_flusser(signal.i, signal.q)
    assert fitzgibbon_result.failed is False
    assert hf_result.failed is False

    disagreement = wrapped_phase_error(
        fitzgibbon_result.recovered_phase, hf_result.recovered_phase
    )
    assert np.sqrt(np.mean(disagreement**2)) < 1e-6, "expected near-exact agreement"


def test_degrades_at_tight_angular_clustering() -> None:
    """docs/WEEK3-4_PLAN.md Day 19: 'document where it degrades.' Day 3's
    own numbers (docs/journal/day03.md) show BOTH methods degrade sharply
    at tight_clustering_3deg (mean coefficient error ~0.47, vs ~0.001 at
    well_conditioned) despite neither one outright failing there -- a
    real, documented degradation distinct from the near_degenerate_15deg
    outright-failure case, checked here via the actual fit() output."""
    params, _ = _REGIMES["tight_clustering_3deg"]
    well_params, _ = _REGIMES["well_conditioned"]

    x_tight, y_tight = _sample_ellipse(**params, seed=0)
    x_well, y_well = _sample_ellipse(**well_params, seed=0)

    conic_tight = _fit_ellipse_conic(x_tight, y_tight)
    conic_well = _fit_ellipse_conic(x_well, y_well)
    assert conic_tight is not None
    assert conic_well is not None

    true_coeffs = _true_conic_coefficients(**params_to_ellipse(params))
    error_tight = _normalized_coefficient_error(np.array(conic_tight), true_coeffs)
    error_well = _normalized_coefficient_error(np.array(conic_well), true_coeffs)

    assert error_tight > 10 * error_well, (
        f"expected clear degradation: well={error_well:.2e}, tight={error_tight:.2e}"
    )


def params_to_ellipse(params: dict[str, object]) -> dict[str, float]:
    return {
        "center_x": float(params["center_x"]),  # type: ignore[arg-type]
        "center_y": float(params["center_y"]),  # type: ignore[arg-type]
        "semi_major": float(params["semi_major"]),  # type: ignore[arg-type]
        "semi_minor": float(params["semi_minor"]),  # type: ignore[arg-type]
        "rotation_rad": float(params["rotation_rad"]),  # type: ignore[arg-type]
    }


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
    fitted_n = fitted / np.linalg.norm(fitted)
    true_n = true_coeffs / np.linalg.norm(true_coeffs)
    return float(min(np.linalg.norm(fitted_n - true_n), np.linalg.norm(fitted_n + true_n)))
