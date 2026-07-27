"""
Tests for hoqi_bench.simulate: the single canonical condition -> signal path
(docs/WEEK3-4_PLAN.md Part 1, P1/P2).

Two acceptance properties, per that plan:
1. `simulate_condition` must be BIT-IDENTICAL to a manual reconstruction of
   the documented composition (pipeline.py's module docstring), for several
   real, named conditions -- not just "close," since this module exists
   specifically to be the one place that composition lives; a numerically-close
   but not-identical reimplementation would defeat the point.
2. Noise must be applied EXACTLY ONCE (closing audit finding B6 -- a silent
   double-application risk) -- verified empirically via variance, not just by
   code inspection, since B6's whole finding was that inspection missed it
   the first time.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.arc import build_arc_ramp
from hoqi_bench.config import load_sweep_config
from hoqi_bench.forward_model import simulate_ideal_interferometer
from hoqi_bench.noise import gaussian_noise, poisson_noise
from hoqi_bench.pipeline import apply_pipeline
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.seeds import derive_seed
from hoqi_bench.simulate import simulate_condition
from hoqi_bench.transforms import amplitude_imbalance, dc_offset, hysteresis, quadrature_phase_error

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"


def _manual_composition(
    resolved: dict[str, float], condition_name: str, seed_index: int
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Independent reconstruction of the documented pipeline order, NOT
    calling `simulate_condition` -- this is the oracle `simulate_condition`
    is checked against, so it must not share code with it."""
    t, x_true_any = build_arc_ramp(resolved["arc_fraction"], int(resolved["samples_per_fit"]))
    x_true: FloatArray = np.asarray(x_true_any, dtype=np.float64)
    i0, q0, _ = simulate_ideal_interferometer(
        t,
        lambda _t: x_true,
        mean_intensity=resolved["mean_intensity"],
        contrast=resolved["contrast"],
    )
    gaussian_seed = derive_seed(seed_index, condition_name, "gaussian_noise")
    poisson_seed = derive_seed(seed_index, condition_name, "poisson_noise")
    i, q = apply_pipeline(
        i0,
        q0,
        transforms=[
            lambda a, b: quadrature_phase_error(
                a, b, resolved["mean_intensity"], resolved["quadrature_error_rad"]
            ),
            lambda a, b: amplitude_imbalance(
                a, b, resolved["mean_intensity"], resolved["amplitude_ratio"]
            ),
            lambda a, b: dc_offset(a, b, resolved["dc_offset"], resolved["dc_offset"]),
            lambda a, b: poisson_noise(a, b, resolved["photon_scale"], seed=poisson_seed),
            lambda a, b: gaussian_noise(a, b, resolved["noise_std"], seed=gaussian_seed),
            lambda a, b: hysteresis(
                a, b, resolved["mean_intensity"], resolved["hysteresis_magnitude"], x_true
            ),
        ],
    )
    true_phase = 4 * np.pi * x_true / 632.8e-9
    return i, q, x_true, true_phase


def test_bit_identical_to_manual_composition_for_named_conditions() -> None:
    """P1's acceptance criterion: >=3 real, named conditions, bit-identical
    (np.array_equal, not np.allclose) against an independently reconstructed
    composition."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}

    named = [
        "axis:amplitude_ratio=1.3",  # classic distortion axis
        "axis:noise_std=0.05",  # nonzero-noise axis
        "axis:hysteresis_magnitude=0.1",  # path-dependent transform, new in v2
    ]
    assert all(name in conditions for name in named), "expected condition names not found"

    for name in named:
        resolved = conditions[name].resolved
        for seed_index in (0, 7):
            expected_i, expected_q, expected_x, expected_phase = _manual_composition(
                resolved, name, seed_index
            )
            actual = simulate_condition(resolved, name, seed_index)

            assert np.array_equal(actual.i, expected_i), f"{name} seed={seed_index}: i mismatch"
            assert np.array_equal(actual.q, expected_q), f"{name} seed={seed_index}: q mismatch"
            assert np.array_equal(
                actual.x_true, expected_x
            ), f"{name} seed={seed_index}: x_true mismatch"
            assert np.array_equal(
                actual.true_phase, expected_phase
            ), f"{name} seed={seed_index}: true_phase mismatch"


def test_noise_applied_exactly_once_not_twice() -> None:
    """Closes audit finding B6 empirically: measures the total variance
    `simulate_condition` actually produces across many seed_index draws and
    confirms it matches SINGLE gaussian_noise application (plus the
    campaign's negligible-but-nonzero poisson contribution at its OFAT
    baseline photon_scale), not double. A double-application bug would
    inflate variance by ~2x -- a 100% relative difference -- so a generous
    tolerance still cleanly distinguishes the two without being flaky."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = {c.name: c for c in iter_conditions(config)}
    resolved = conditions["axis:noise_std=0.05"].resolved
    expected_noise_std = resolved["noise_std"]
    assert expected_noise_std > 0.0, "test needs a genuinely noisy condition"

    n_draws = 300
    residuals_i = []
    for seed_index in range(n_draws):
        signal = simulate_condition(resolved, "axis:noise_std=0.05", seed_index)
        # Undistorted DC-centered ideal I at this condition has no per-seed
        # randomness of its own (arc/displacement is deterministic given the
        # condition) -- subtracting the mean-intensity-centered ideal isn't
        # available directly, so instead compare successive draws' spread
        # around their own mean at each sample, which isolates the
        # per-sample noise contribution regardless of the deterministic
        # oscillation underneath.
        residuals_i.append(signal.i)

    stacked = np.stack(residuals_i)  # shape (n_draws, n_samples)
    empirical_std = float(np.std(stacked, axis=0).mean())

    # Poisson's contribution at this condition's OFAT baseline photon_scale
    # (1e7, documented as "negligible, not literally off") is much smaller
    # than the swept noise_std -- a single-application total std should sit
    # close to expected_noise_std; a double-application bug would push it
    # toward sqrt(2)*expected_noise_std, ~41% higher, well outside this band.
    relative_error = abs(empirical_std - expected_noise_std) / expected_noise_std
    assert relative_error < 0.15, (
        f"empirical noise std {empirical_std:.6f} vs expected {expected_noise_std:.6f} "
        f"(relative error {relative_error:.3f}) -- suggests noise applied more than once"
    )
