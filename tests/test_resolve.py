"""
Tests for hoqi_bench.resolve: fraction-to-absolute conversion and per-condition
manifest enumeration.

Weeks 1-2 audit (2026-07-26, finding F2): docs/experimental_design.md
specifies dc_offset/noise_std/hysteresis_magnitude as fractions of amplitude
A = mean_intensity*contrast, but transforms.dc_offset/noise.gaussian_noise
take absolute values, with nothing previously converting between the two --
a silent 1.11x error at the campaign's baseline A=0.9. These tests confirm
the conversion is now real and exact, not just present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hoqi_bench.config import SweepConfig, load_sweep_config
from hoqi_bench.resolve import ResolutionError, iter_conditions

# ---- 1. Fraction-to-absolute conversion, on a minimal hand-built config ----


def _minimal_config(**axis_overrides: list[float]) -> SweepConfig:
    baseline = {
        "mean_intensity": 1.0,
        "contrast": 0.9,
        "amplitude_ratio": 1.1,
        "quadrature_error_rad": 0.1,
        "dc_offset": 0.02,
        "arc_fraction": 1.0,
        "noise_std": 0.05,
        "samples_per_fit": 60,
        "hysteresis_magnitude": 0.1,
        "photon_scale": 1.0e7,
    }
    return SweepConfig(
        axes=dict(axis_overrides) or {"amplitude_ratio": [1.1]},
        grids={},
        baseline=baseline,
        methods=["kasa"],
        n_seeds=1,
        tolerance=0.01,
    )


def test_fraction_of_amplitude_params_are_converted_to_absolute() -> None:
    """A = mean_intensity*contrast = 1.0*0.9 = 0.9. dc_offset=0.02 (fraction)
    must resolve to 0.02*0.9=0.018 (absolute), not the literal 0.02 the
    config file writes -- the exact 1.11x gap the audit measured."""
    config = _minimal_config()
    conditions = iter_conditions(config)

    resolved = conditions[0].resolved
    amplitude = 1.0 * 0.9
    assert resolved["dc_offset"] == pytest.approx(0.02 * amplitude)
    assert resolved["noise_std"] == pytest.approx(0.05 * amplitude)
    assert resolved["hysteresis_magnitude"] == pytest.approx(0.1 * amplitude)


def test_non_fraction_params_pass_through_unchanged() -> None:
    """amplitude_ratio, quadrature_error_rad, arc_fraction, samples_per_fit,
    and photon_scale are NOT fractions of A -- resolution must leave them
    exactly as given, not accidentally scale them too."""
    config = _minimal_config()
    resolved = iter_conditions(config)[0].resolved

    assert resolved["amplitude_ratio"] == 1.1
    assert resolved["quadrature_error_rad"] == 0.1
    assert resolved["arc_fraction"] == 1.0
    assert resolved["samples_per_fit"] == 60
    assert resolved["photon_scale"] == 1.0e7


def test_swept_axis_value_overrides_baseline_in_resolved_output() -> None:
    """The condition for amplitude_ratio=1.3 must resolve amplitude_ratio to
    1.3 (the swept value), not the baseline's 1.1 -- while every OTHER
    parameter stays at baseline."""
    config = _minimal_config(amplitude_ratio=[1.0, 1.3])
    conditions = iter_conditions(config)

    values = {c.resolved["amplitude_ratio"] for c in conditions}
    assert values == {1.0, 1.3}
    # every other parameter stays at baseline regardless of which value swept
    for c in conditions:
        assert c.resolved["quadrature_error_rad"] == 0.1


def test_resolution_error_when_required_param_missing() -> None:
    """Defense at the point of use: a SweepConfig missing a required model
    parameter (constructed directly, bypassing config.py's own load-time
    check) must fail loudly here too, not silently resolve a partial dict."""
    incomplete = SweepConfig(
        axes={"amplitude_ratio": [1.1]},
        grids={},
        baseline={"amplitude_ratio": 1.1},  # missing everything else
        methods=["kasa"],
        n_seeds=1,
        tolerance=0.01,
    )
    with pytest.raises(ResolutionError, match="missing resolved value"):
        iter_conditions(incomplete)


# ---- 2. Condition enumeration matches total_runs()'s n_conditions term ----


def test_condition_count_matches_total_runs_n_conditions_for_main_campaign() -> None:
    config_path = Path(__file__).resolve().parent.parent / "configs" / "main_campaign.toml"
    config = load_sweep_config(config_path)

    conditions = iter_conditions(config)
    n_conditions = config.total_runs() // (len(config.methods) * config.n_seeds)
    assert len(conditions) == n_conditions


def test_condition_count_matches_total_runs_n_conditions_for_smoke() -> None:
    config_path = Path(__file__).resolve().parent.parent / "configs" / "smoke.toml"
    config = load_sweep_config(config_path)

    conditions = iter_conditions(config)
    n_conditions = config.total_runs() // (len(config.methods) * config.n_seeds)
    assert len(conditions) == n_conditions


def test_every_resolved_condition_covers_every_required_param() -> None:
    """No condition should ever come back partially resolved -- every one
    must carry a value for every REQUIRED_MODEL_PARAMS key."""
    from hoqi_bench.config import REQUIRED_MODEL_PARAMS

    config_path = Path(__file__).resolve().parent.parent / "configs" / "main_campaign.toml"
    config = load_sweep_config(config_path)

    for condition in iter_conditions(config):
        assert set(condition.resolved.keys()) >= REQUIRED_MODEL_PARAMS
