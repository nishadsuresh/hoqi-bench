"""
Tests for hoqi_bench.methods.raw_atan2 -- Method 1, the deliberately naive
baseline (Day 15).

Day 15's acceptance criterion (docs/WEEK3-4_PLAN.md): near-exact on clean
data, measurably degrades under injected distortion.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.config import load_sweep_config
from hoqi_bench.methods.raw_atan2 import fit
from hoqi_bench.metrics import wrapped_phase_error
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import simulate_condition

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"

# Every REQUIRED_MODEL_PARAMS entry at its true identity value -- no
# distortion, no noise, no path-dependence. Not built via iter_conditions,
# since even the amplitude_ratio=1.0 "no-distortion control" axis point
# holds every OTHER parameter at its (nonzero) baseline -- this dict is the
# fully clean condition Day 21's cross-validation gate will also need.
FULLY_CLEAN_CONDITION = {
    "mean_intensity": 1.0,
    "contrast": 0.9,
    "amplitude_ratio": 1.0,
    "quadrature_error_rad": 0.0,
    "dc_offset": 0.0,
    "arc_fraction": 1.0,
    "noise_std": 0.0,
    "samples_per_fit": 200,
    "hysteresis_magnitude": 0.0,
    "photon_scale": 1.0e7,
}


def _rmse(errors: FloatArray) -> float:
    return float(np.sqrt(np.mean(errors**2)))


def test_near_exact_on_clean_data() -> None:
    signal = simulate_condition(FULLY_CLEAN_CONDITION, "fully_clean", seed_index=0)
    result = fit(signal.i, signal.q, mean_intensity=FULLY_CLEAN_CONDITION["mean_intensity"])

    assert result.failed is False
    errors = wrapped_phase_error(signal.true_phase, result.recovered_phase)

    # Not bit-exact: photon_scale=1e7's negligible-but-real Poisson noise
    # (noise.py's own documented Var(intensity_domain_noise) = intensity/
    # photon_scale) contributes a real, derivable phase-error floor, not
    # numerical error. Tolerance is DERIVED from that formula, not guessed:
    # intensity-domain noise std ~ sqrt(mean_intensity/photon_scale), and a
    # small radial perturbation of that size on a circle of amplitude
    # ~contrast produces a phase error of roughly noise_std/contrast
    # radians. A first attempt at this test used an ungrounded 1e-4 bound
    # and failed at the actual (correct) 3.98e-4 RMSE -- this bound is
    # derived instead, with a generous 5x margin for the approximation's
    # own looseness (it ignores exact two-channel geometry).
    c = FULLY_CLEAN_CONDITION
    expected_noise_std = (c["mean_intensity"] / c["photon_scale"]) ** 0.5
    expected_phase_error = expected_noise_std / c["contrast"]
    tolerance = 5 * expected_phase_error

    assert _rmse(errors) < tolerance, (
        f"raw atan2 on clean data: RMSE={_rmse(errors):.2e} rad, "
        f"expected ~{expected_phase_error:.2e} rad from documented Poisson noise, "
        f"tolerance={tolerance:.2e} rad"
    )


def test_degrades_under_amplitude_ratio_distortion() -> None:
    """raw_atan2 has no correction model at all -- injecting a real,
    preregistered amplitude_ratio value must measurably increase its
    phase error relative to the clean case above, confirming this baseline
    actually responds to distortion rather than being accidentally
    insensitive to it."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:amplitude_ratio=1.3"].resolved

    signal = simulate_condition(resolved, "axis:amplitude_ratio=1.3", seed_index=0)
    result = fit(signal.i, signal.q, mean_intensity=resolved["mean_intensity"])

    assert result.failed is False
    errors = wrapped_phase_error(signal.true_phase, result.recovered_phase)
    distorted_rmse = _rmse(errors)

    clean_signal = simulate_condition(FULLY_CLEAN_CONDITION, "fully_clean", seed_index=0)
    clean_result = fit(
        clean_signal.i, clean_signal.q, mean_intensity=FULLY_CLEAN_CONDITION["mean_intensity"]
    )
    clean_errors = wrapped_phase_error(clean_signal.true_phase, clean_result.recovered_phase)

    assert distorted_rmse > 10 * _rmse(clean_errors), (
        f"expected clear degradation: clean RMSE={_rmse(clean_errors):.2e}, "
        f"distorted RMSE={distorted_rmse:.2e}"
    )


def test_never_fails() -> None:
    """atan2 is defined for every real input, including (0, 0) -- confirms
    this structurally (module docstring), not just by assertion, using a
    degenerate all-zero input a real method might otherwise choke on."""
    zeros = np.zeros(10)
    result = fit(zeros, zeros, mean_intensity=1.0)
    assert result.failed is False
    assert np.all(np.isfinite(result.recovered_phase))
