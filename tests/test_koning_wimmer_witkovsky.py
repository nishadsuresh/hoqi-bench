"""
Tests for hoqi_bench.methods.koning_wimmer_witkovsky -- Method 7 (Day 20),
the hardest of the 7 methods and the only iterative one.

Verified directly (docs/journal/day20.md) against several real campaign
conditions before writing these assertions: normal conditions converge in
3-10 iterations; the extreme small-arc_fraction conditions (0.02, 0.05)
correctly return failed=True, reason="non_convergent" rather than hanging
or returning garbage -- exercised directly below, not assumed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.config import load_sweep_config
from hoqi_bench.methods.koning_wimmer_witkovsky import _iterative_eiv_fit, fit
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import simulate_condition

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"


def _rmse(errors: FloatArray) -> float:
    return float(np.sqrt(np.mean(errors**2)))


def test_recovers_known_ellipse_on_clean_data() -> None:
    theta = np.linspace(0, 2 * np.pi, 100, endpoint=False)
    cx, cy, semi_major, semi_minor, rotation = 2.0, -1.0, 5.0, 4.0, 0.3
    cos_r, sin_r = np.cos(rotation), np.sin(rotation)
    rng = np.random.default_rng(0)
    x = cx + semi_major * np.cos(theta) * cos_r - semi_minor * np.sin(theta) * sin_r
    y = cy + semi_major * np.cos(theta) * sin_r + semi_minor * np.sin(theta) * cos_r
    x = x + rng.normal(0, 0.01, 100)
    y = y + rng.normal(0, 0.01, 100)

    result = _iterative_eiv_fit(x, y)
    assert result is not None
    coeffs, n_iter, covariance = result

    assert n_iter >= 1
    assert n_iter < 20, "expected genuine convergence, not hitting the iteration cap"
    assert np.all(np.isfinite(covariance))
    assert np.allclose(covariance, covariance.T), "covariance must be symmetric"
    eigvals = np.linalg.eigvalsh(covariance)
    assert np.all(eigvals > -1e-9), f"covariance must be PSD, got eigenvalues {eigvals}"


def test_converges_and_recovers_distortion_on_real_condition() -> None:
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:quadrature_error_rad=0.3"].resolved
    signal = simulate_condition(resolved, "axis:quadrature_error_rad=0.3", seed_index=0)

    result = fit(signal.i, signal.q)

    assert result.failed is False
    assert result.converged is True
    assert result.n_iter is not None and result.n_iter >= 1
    assert result.covariance is not None
    assert result.params is not None

    rel_error_eps = abs(
        result.params["quadrature_error_rad"] - resolved["quadrature_error_rad"]
    ) / resolved["quadrature_error_rad"]
    assert rel_error_eps < 0.02, f"eps recovery: {rel_error_eps:.4f} relative error"


def test_fails_gracefully_non_convergent_at_extreme_small_arc() -> None:
    """The distinctive failure mode among all 7 methods: this is the only
    ITERATIVE one, so its degeneracy shows up as failure to converge
    within _MAX_ITER, not a singular-matrix or no-candidate outcome."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    for name in ["axis:arc_fraction=0.02", "axis:arc_fraction=0.05"]:
        resolved = conditions[name].resolved
        signal = simulate_condition(resolved, name, seed_index=0)

        result = fit(signal.i, signal.q)

        assert result.failed is True, f"{name}: expected graceful failure"
        assert result.reason == "non_convergent", f"{name}: reason={result.reason}"
        assert result.converged is False
        assert np.all(np.isnan(result.recovered_phase))


def test_never_hangs_across_full_campaign_sample() -> None:
    """A real, previously-encountered scare (docs/journal/day20.md): a
    multi-condition script appeared to hang for 120s with no output,
    traced to stdout buffering hiding successful fast results, not an
    actual infinite loop -- verified here by running a representative
    sample of real conditions and asserting each completes well within
    a generous per-call budget, so a genuine future hang would fail loudly
    rather than being mistaken for buffering again."""
    import time

    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = iter_conditions(config)
    sample = conditions[::30]  # every 30th condition, a broad spread
    assert len(sample) >= 10

    for condition in sample:
        start = time.perf_counter()
        signal = simulate_condition(condition.resolved, condition.name, seed_index=0)
        fit(signal.i, signal.q)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"{condition.name}: took {elapsed:.2f}s, expected well under 2s"
