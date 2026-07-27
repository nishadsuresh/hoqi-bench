"""
Tests for hoqi_bench.methods.kasa -- Method 2 (Day 16).

Acceptance criterion, corrected from the original build plan (see
kasa.py's own module docstring for the full reasoning): bit-identical port
fidelity against an independent reconstruction of
`quadrature-interferometer-sim`'s `fit_circle_center`, not a percentage
match on that project's downstream end-to-end pipeline (a composite this
project's method interface doesn't build).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.config import load_sweep_config
from hoqi_bench.methods.kasa import fit
from hoqi_bench.methods.raw_atan2 import fit as fit_raw_atan2
from hoqi_bench.metrics import wrapped_phase_error
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import simulate_condition

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"


def _reference_fit_circle_center(
    intensity_i: FloatArray, intensity_q: FloatArray
) -> tuple[float, float]:
    """Independent reconstruction of quadrature-interferometer-sim's
    src/analysis.py fit_circle_center, copied (not imported -- that sibling
    repo is not a dependency of this project) for direct bit-identity
    comparison. Deliberately NOT calling kasa.py's own
    _fit_circle_center -- this is the oracle that function is checked
    against, so it must not share code with it."""
    design = np.column_stack([intensity_i, intensity_q, np.ones_like(intensity_i)])
    target = intensity_i**2 + intensity_q**2
    coeffs, *_ = np.linalg.lstsq(design, target, rcond=None)
    a = coeffs[0] / 2
    b = coeffs[1] / 2
    return float(a), float(b)


def _rmse(errors: FloatArray) -> float:
    return float(np.sqrt(np.mean(errors**2)))


def test_bit_identical_port_of_fit_circle_center() -> None:
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}

    named = ["axis:dc_offset=0.1", "axis:amplitude_ratio=1.3", "axis:noise_std=0.05"]
    for name in named:
        resolved = conditions[name].resolved
        signal = simulate_condition(resolved, name, seed_index=0)

        result = fit(signal.i, signal.q)
        expected_center = _reference_fit_circle_center(signal.i, signal.q)

        assert result.params is not None
        assert result.params["center_i"] == expected_center[0], f"{name}: center_i mismatch"
        assert result.params["center_q"] == expected_center[1], f"{name}: center_q mismatch"


def _rmse_pair(resolved: dict[str, float], name: str) -> tuple[float, float]:
    signal = simulate_condition(resolved, name, seed_index=0)
    kasa_rmse = _rmse(
        wrapped_phase_error(signal.true_phase, fit(signal.i, signal.q).recovered_phase)
    )
    atan2_rmse = _rmse(
        wrapped_phase_error(
            signal.true_phase,
            fit_raw_atan2(
                signal.i, signal.q, mean_intensity=resolved["mean_intensity"]
            ).recovered_phase,
        )
    )
    return kasa_rmse, atan2_rmse


def test_outperforms_raw_atan2_on_dc_offset_for_a_true_circle() -> None:
    """On a TRUE circle (no baseline ellipse eccentricity), Kasa's fitted
    center should recover dc_offset almost exactly -- Kasa's whole
    mechanism is a circle-center fit, and dc_offset IS a circle's center."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = dict(conditions["axis:dc_offset=0.2"].resolved)
    resolved["amplitude_ratio"] = 1.0
    resolved["quadrature_error_rad"] = 0.0

    kasa_rmse, atan2_rmse = _rmse_pair(resolved, "dc_offset_true_circle")
    assert kasa_rmse < 0.01 * atan2_rmse, (
        f"kasa RMSE={kasa_rmse:.4e}, raw_atan2 RMSE={atan2_rmse:.4e} "
        f"-- expected near-exact dc_offset recovery on a true circle"
    )


def test_dc_offset_correction_degrades_with_baseline_ellipse_eccentricity() -> None:
    """The real campaign's dc_offset OFAT axis holds amplitude_ratio=1.1,
    quadrature_error_rad=0.1 constant at their (nonzero) baseline while
    sweeping dc_offset -- that baseline eccentricity biases Kasa's
    circle-fit center estimate, so the real improvement over raw atan2 is
    genuine but much weaker than the true-circle case above. First found
    by running this test with an ungrounded >=10x expectation and getting
    only 2.8x -- verified as real behavior (not a bug) by comparing
    against the true-circle case directly, not just loosening the bound."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:dc_offset=0.2"].resolved

    kasa_rmse, atan2_rmse = _rmse_pair(resolved, "axis:dc_offset=0.2")
    assert kasa_rmse < 0.5 * atan2_rmse, (
        f"kasa RMSE={kasa_rmse:.4e}, raw_atan2 RMSE={atan2_rmse:.4e} "
        f"-- expected a real, if weaker, improvement over raw atan2"
    )


def test_no_structural_advantage_over_raw_atan2_on_amplitude_ratio() -> None:
    """Per docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md: a circle has no free
    parameter for eccentricity, so amplitude_ratio distortion should pass
    through Kasa roughly as uncorrected as it does through raw atan2 --
    this is the Kasa "partial exception" prediction, checked empirically,
    not assumed."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:amplitude_ratio=1.3"].resolved
    signal = simulate_condition(resolved, "axis:amplitude_ratio=1.3", seed_index=0)

    kasa_errors = wrapped_phase_error(signal.true_phase, fit(signal.i, signal.q).recovered_phase)
    atan2_errors = wrapped_phase_error(
        signal.true_phase,
        fit_raw_atan2(
            signal.i, signal.q, mean_intensity=resolved["mean_intensity"]
        ).recovered_phase,
    )

    # Same order of magnitude, NOT the >=10x gap the dc_offset case shows --
    # a circle fit's center estimate is nudged by the ellipse's eccentricity,
    # so a modest (not large) improvement is plausible; the prediction being
    # tested is the ABSENCE of a structural correction, not zero difference.
    ratio = _rmse(kasa_errors) / _rmse(atan2_errors)
    assert ratio > 0.3, (
        f"kasa RMSE={_rmse(kasa_errors):.4e} vs atan2 RMSE={_rmse(atan2_errors):.4e} "
        f"(ratio={ratio:.3f}) -- expected no strong structural correction on this axis"
    )
