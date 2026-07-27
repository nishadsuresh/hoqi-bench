"""
Tests for hoqi_bench.methods.taubin -- Method 6 (Day 20).

Per docs/WEEK3_METHOD_CONTRACT.md sec3.3, AS NARROWED by that section's
2026-07-27 deviation note: Taubin and Kasa should agree closely at low
noise, and Taubin's bias correction should measurably reduce RADIUS bias
relative to Kasa as noise rises -- NOT phase-recovery RMSE, which the
first draft of this test suite assumed and found false (200-seed check:
Taubin's phase RMSE was statistically indistinguishable from, if anything
marginally worse than, Kasa's). Root cause, verified before accepting it
as a real finding rather than assuming a bug: the classic Taubin-vs-Kasa
bias-reduction result is specifically about radius estimation, and
`atan2`-based phase recovery depends only on the fitted CENTER, never the
radius -- so the textbook effect is real (confirmed: Taubin's radius bias
is ~5.6x smaller than Kasa's at the same condition) but doesn't transfer
to this project's actual downstream metric.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.config import load_sweep_config
from hoqi_bench.methods.kasa import fit as fit_kasa
from hoqi_bench.methods.taubin import _fit_circle_taubin, fit
from hoqi_bench.metrics import wrapped_phase_error
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import simulate_condition

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"


def _rmse(errors: FloatArray) -> float:
    return float(np.sqrt(np.mean(errors**2)))


def test_recovers_known_circle_to_near_machine_precision() -> None:
    theta = np.linspace(0, 2 * np.pi, 100, endpoint=False)
    x = 3.0 + 5.0 * np.cos(theta)
    y = -2.0 + 5.0 * np.sin(theta)

    result = _fit_circle_taubin(x, y)
    assert result is not None
    center_i, center_q, radius = result
    assert abs(center_i - 3.0) < 1e-9
    assert abs(center_q - (-2.0)) < 1e-9
    assert abs(radius - 5.0) < 1e-9


def test_agrees_with_kasa_at_low_noise() -> None:
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:noise_std=0.005"].resolved
    signal = simulate_condition(resolved, "axis:noise_std=0.005", seed_index=0)

    taubin_phase = fit(signal.i, signal.q).recovered_phase
    kasa_phase = fit_kasa(signal.i, signal.q).recovered_phase

    disagreement = _rmse(wrapped_phase_error(taubin_phase, kasa_phase))
    assert disagreement < 0.01, f"disagreement at low noise: {disagreement:.4e} rad"


def _kasa_center_and_radius(
    intensity_i: FloatArray, intensity_q: FloatArray
) -> tuple[float, float, float]:
    """Independent reconstruction of Kasa's own algebraic radius (not
    imported from kasa.py, matching this project's oracle-independence
    convention) -- needed here because kasa.fit() itself only returns
    phase, not radius, and this test's actual claim is about radius."""
    design = np.column_stack([intensity_i, intensity_q, np.ones_like(intensity_i)])
    target = intensity_i**2 + intensity_q**2
    coeffs, *_ = np.linalg.lstsq(design, target, rcond=None)
    center_i, center_q = coeffs[0] / 2, coeffs[1] / 2
    radius_squared = coeffs[2] + center_i**2 + center_q**2
    return float(center_i), float(center_q), float(np.sqrt(max(radius_squared, 0.0)))


def test_reduces_radius_bias_relative_to_kasa_as_noise_rises() -> None:
    """The REAL, verified WEEK3_METHOD_CONTRACT.md sec3.3 claim (per that
    section's 2026-07-27 deviation note): Taubin's RADIUS bias should be
    measurably smaller than Kasa's at the top of the swept noise range --
    checked over 100 seeds (bias is a property of an estimator's mean
    behavior, not a single draw) with MATCHED radius formulas for both."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:noise_std=0.1"].resolved
    true_radius = resolved["mean_intensity"] * resolved["contrast"]

    taubin_radii, kasa_radii = [], []
    for seed in range(100):
        signal = simulate_condition(resolved, "axis:noise_std=0.1", seed_index=seed)
        taubin_result = _fit_circle_taubin(signal.i, signal.q)
        assert taubin_result is not None
        taubin_radii.append(taubin_result[2])
        _, _, kasa_radius = _kasa_center_and_radius(signal.i, signal.q)
        kasa_radii.append(kasa_radius)

    taubin_bias = abs(float(np.mean(taubin_radii)) - true_radius)
    kasa_bias = abs(float(np.mean(kasa_radii)) - true_radius)
    assert taubin_bias < kasa_bias, (
        f"expected Taubin's radius bias to be smaller: "
        f"taubin={taubin_bias:.4e}, kasa={kasa_bias:.4e}"
    )


def test_phase_rmse_stays_comparable_to_kasa_at_high_noise() -> None:
    """The corrected companion claim: since Taubin's advantage is
    radius-specific (test above) and phase recovery only uses the center,
    Taubin should NOT be dramatically worse than Kasa for phase RMSE
    either -- checked as a parity bound, not an improvement claim."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:noise_std=0.1"].resolved
    signal = simulate_condition(resolved, "axis:noise_std=0.1", seed_index=0)

    taubin_rmse = _rmse(
        wrapped_phase_error(signal.true_phase, fit(signal.i, signal.q).recovered_phase)
    )
    kasa_rmse = _rmse(
        wrapped_phase_error(signal.true_phase, fit_kasa(signal.i, signal.q).recovered_phase)
    )
    ratio = taubin_rmse / kasa_rmse
    assert 0.5 < ratio < 2.0, f"expected comparable phase RMSE, got ratio={ratio:.3f}"


def test_no_structural_advantage_over_kasa_on_amplitude_ratio() -> None:
    """Both Taubin and Kasa fit only a circle -- neither has a free
    parameter for amplitude_ratio, so they should behave similarly on
    this axis (docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md)."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:amplitude_ratio=1.3"].resolved
    signal = simulate_condition(resolved, "axis:amplitude_ratio=1.3", seed_index=0)

    taubin_rmse = _rmse(
        wrapped_phase_error(signal.true_phase, fit(signal.i, signal.q).recovered_phase)
    )
    kasa_rmse = _rmse(
        wrapped_phase_error(signal.true_phase, fit_kasa(signal.i, signal.q).recovered_phase)
    )
    ratio = taubin_rmse / kasa_rmse
    assert 0.5 < ratio < 2.0, f"expected similar magnitude, got ratio={ratio:.3f}"
