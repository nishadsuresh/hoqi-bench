"""
Tests for hoqi_bench.harmonics -- Day 23's cyclic-error estimator.

Oracle-independence: the reference residual is BUILT here from known
amplitudes rather than imported from the module under test, so a shared
sign or normalisation error cannot cancel out between the two.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.harmonics import cyclic_error


def _phase_and_residual(
    n_points: int,
    arc_fraction: float,
    amp1: float,
    amp2: float,
    noise_std: float = 0.0,
    seed: int = 0,
) -> tuple[FloatArray, FloatArray]:
    """A true phase ramp plus a residual with KNOWN cyclic amplitudes."""
    rng = np.random.default_rng(seed)
    true_phase = np.linspace(0.0, arc_fraction * 2 * np.pi, n_points, endpoint=False)
    residual = amp1 * np.sin(true_phase + 0.4) + amp2 * np.sin(2 * true_phase + 1.1)
    residual = residual + rng.normal(0.0, noise_std, n_points)
    return np.asarray(true_phase, dtype=np.float64), np.asarray(residual, dtype=np.float64)


def test_recovers_known_amplitudes_to_machine_precision() -> None:
    """Noiseless, full circle: this is algebra, so it must be exact."""
    for amp1, amp2 in ((0.05, 0.0), (0.0, 0.03), (0.05, 0.03), (0.001, 0.002)):
        true_phase, residual = _phase_and_residual(60, 1.0, amp1, amp2)
        result = cyclic_error(true_phase, true_phase + residual)
        assert abs(result.first_order_rad - amp1) < 1e-12, f"A1: {result.first_order_rad}"
        assert abs(result.second_order_rad - amp2) < 1e-12, f"A2: {result.second_order_rad}"
        assert result.well_conditioned


def test_null_case_does_not_manufacture_a_peak() -> None:
    """No injected cyclic error must not produce one. The bound is the
    estimator's real noise floor, measured at 0.096*sigma (first order) and
    0.128*sigma (second) -- the projection of white noise onto two basis
    functions, which is a property of the estimator and not a defect. A
    test demanding exactly zero at nonzero noise would be wrong."""
    true_phase, residual = _phase_and_residual(60, 1.0, 0.0, 0.0, noise_std=0.0)
    result = cyclic_error(true_phase, true_phase + residual)
    assert result.first_order_rad == 0.0
    assert result.second_order_rad == 0.0

    for noise_std in (0.001, 0.01):
        true_phase, residual = _phase_and_residual(60, 1.0, 0.0, 0.0, noise_std=noise_std, seed=1)
        result = cyclic_error(true_phase, true_phase + residual)
        assert result.first_order_rad < 0.3 * noise_std, (
            f"spurious A1={result.first_order_rad:.3e} at noise={noise_std}"
        )
        assert result.second_order_rad < 0.3 * noise_std, (
            f"spurious A2={result.second_order_rad:.3e} at noise={noise_std}"
        )


def _as_pair(pair: tuple[FloatArray, FloatArray]) -> tuple[FloatArray, FloatArray]:
    """(true_phase, residual) -> (true_phase, recovered_phase)."""
    true_phase, residual = pair
    return true_phase, true_phase + residual


def test_conditioning_flags_the_small_arc_regime() -> None:
    """The guard that stops 99 of the campaign's 359 conditions from
    silently reporting a confident, wrong harmonic amplitude. Thresholds
    are the module's own measured calibration, checked in both directions
    so the limit cannot drift without a test noticing."""
    well = cyclic_error(*_as_pair(_phase_and_residual(60, 1.0, 0.05, 0.03)))
    assert well.well_conditioned
    assert well.conditioning < 1.5

    marginal = cyclic_error(*_as_pair(_phase_and_residual(60, 0.35, 0.05, 0.03)))
    assert marginal.conditioning > 9.0
    assert marginal.conditioning < 12.0

    degenerate = cyclic_error(*_as_pair(_phase_and_residual(60, 0.15, 0.05, 0.03)))
    assert not degenerate.well_conditioned
    assert degenerate.conditioning > 100.0


def test_exact_at_small_arc_when_noiseless() -> None:
    """The distinction that justifies reporting conditioning rather than
    just refusing: the estimator is ALGEBRAICALLY exact even at
    arc_fraction=0.02. Small arc is not a correctness problem, it is a
    noise-amplification problem -- so the right response is a flag, not a
    failure."""
    true_phase, residual = _phase_and_residual(60, 0.02, 0.05, 0.03)
    result = cyclic_error(true_phase, true_phase + residual)
    assert abs(result.first_order_rad - 0.05) < 1e-9
    assert abs(result.second_order_rad - 0.03) < 1e-9
    assert not result.well_conditioned


def test_detects_uncorrected_distortion_on_a_real_condition() -> None:
    """End-to-end: raw_atan2 leaves a large first-order cyclic error on a
    condition with real quadrature error, and heydemann -- whose correction
    model IS this distortion -- leaves far less. Not a ranking claim (that
    ordering is tautological per docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md);
    this asserts the ESTIMATOR responds to real uncorrected nonlinearity,
    which a synthetic-residual test alone cannot show."""
    from pathlib import Path

    from hoqi_bench.config import load_sweep_config
    from hoqi_bench.methods import fit_by_name
    from hoqi_bench.resolve import iter_conditions
    from hoqi_bench.simulate import simulate_condition

    config = load_sweep_config(Path(__file__).parent.parent / "configs" / "main_campaign.toml")
    conditions = {c.name: c for c in iter_conditions(config)}
    name = "axis:quadrature_error_rad=0.3"
    resolved = conditions[name].resolved
    signal = simulate_condition(resolved, name, seed_index=0)

    raw = fit_by_name("raw_atan2", signal.i, signal.q, mean_intensity=resolved["mean_intensity"])
    corrected = fit_by_name(
        "heydemann", signal.i, signal.q, mean_intensity=resolved["mean_intensity"]
    )
    assert not raw.failed and not corrected.failed

    raw_cyclic = cyclic_error(signal.true_phase, raw.recovered_phase)
    corrected_cyclic = cyclic_error(signal.true_phase, corrected.recovered_phase)

    assert raw_cyclic.well_conditioned
    assert raw_cyclic.first_order_rad > 10 * corrected_cyclic.first_order_rad, (
        f"raw={raw_cyclic.first_order_rad:.4e}, corrected={corrected_cyclic.first_order_rad:.4e}"
    )
