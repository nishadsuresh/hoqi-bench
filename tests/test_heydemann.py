"""
Tests for hoqi_bench.methods.heydemann -- Method 3 (Day 17).

Per docs/WEEK3-4_PLAN.md Day 17: inject known distortion and verify
recovery to a stated tolerance; a degeneracy test (tiny phase excursion)
verifying graceful failure with a reason code, not a throw or silent
garbage.

All tolerances below are DERIVED from direct numerical investigation
(see heydemann.py's own module docstring for the full account), not
guessed -- a first draft of the amplitude_ratio=1.3 test assumed
near-machine-precision recovery and was wrong; the real, understood cause
(build_arc_ramp's endpoint=True convention plus noise.poisson_noise's
negative-intensity clamp interacting with this variance-based estimator)
is documented and tested for directly, not hidden behind a loosened
tolerance.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.config import load_sweep_config
from hoqi_bench.methods.heydemann import fit
from hoqi_bench.methods.kasa import fit as fit_kasa
from hoqi_bench.methods.raw_atan2 import fit as fit_raw_atan2
from hoqi_bench.metrics import wrapped_phase_error
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import simulate_condition

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"


def _rmse(errors: FloatArray) -> float:
    return float(np.sqrt(np.mean(errors**2)))


def _conditions() -> dict[str, object]:
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    return {c.name: c for c in iter_conditions(config)}


def test_recovers_known_distortion_at_full_arc() -> None:
    """quadrature_error_rad=0.3 (a real preregistered value, with zero
    negative-intensity samples at this condition -- well away from
    amplitude_ratio's clamp interaction) at full arc coverage: g/eps
    should be recovered to within 2%, not the near-machine-precision an
    idealized (infinite-sample, endpoint-symmetric) synthetic check
    suggests. The residual ~1.6% is real and understood: build_arc_ramp
    uses np.linspace(..., endpoint=True), so phi=0 and phi=2*pi coincide
    at one duplicated sample out of samples_per_fit=60 -- a small,
    deterministic bias in any moment-based (variance/covariance) estimator
    reading from it, verified directly by comparing against an
    endpoint=False synthetic reconstruction (heydemann.py's own module
    docstring). Not fixed in build_arc_ramp itself: that function is
    deeply embedded in already-validated Weeks 1-2 results (Day 7's
    "31 fringes, 0.000000% error" check, the v2 samples_per_fit design
    table) and changing it now risks silently invalidating locked prior
    findings to smooth over a bias only THIS estimator is sensitive to."""
    conditions = _conditions()
    resolved = conditions["axis:quadrature_error_rad=0.3"].resolved  # type: ignore[attr-defined]
    signal = simulate_condition(resolved, "axis:quadrature_error_rad=0.3", seed_index=0)

    result = fit(signal.i, signal.q)
    assert result.failed is False
    assert result.params is not None

    rel_error_g = abs(result.params["amplitude_ratio"] - resolved["amplitude_ratio"]) / resolved[
        "amplitude_ratio"
    ]
    rel_error_eps = abs(
        result.params["quadrature_error_rad"] - resolved["quadrature_error_rad"]
    ) / resolved["quadrature_error_rad"]
    assert rel_error_g < 0.02, f"g recovery: {rel_error_g:.4f} relative error"
    assert rel_error_eps < 0.02, f"eps recovery: {rel_error_eps:.4f} relative error"

    heydemann_rmse = _rmse(wrapped_phase_error(signal.true_phase, result.recovered_phase))
    atan2_rmse = _rmse(
        wrapped_phase_error(
            signal.true_phase,
            fit_raw_atan2(
                signal.i, signal.q, mean_intensity=resolved["mean_intensity"]
            ).recovered_phase,
        )
    )
    # Measured ratio ~0.066 (15x) at this condition, not the 100x a first
    # guess assumed -- the residual ~1.6% endpoint=True bias above still
    # applies to Heydemann's own phase output, not just its reported g/eps.
    assert heydemann_rmse < 0.1 * atan2_rmse, f"h/a ratio={heydemann_rmse / atan2_rmse:.4f}"


def test_recovers_known_distortion_at_extreme_amplitude_ratio() -> None:
    """amplitude_ratio=1.3 is a real swept value chosen specifically to
    probe breakdown (docs/experimental_design.md). At this condition, Q
    dips negative for ~17% of the record even before noise, and
    noise.poisson_noise's negative-intensity clamp interacts with this
    variance-based estimator to produce a real, understood ~4% bias in
    recovered g (see heydemann.py's module docstring for the full,
    numerically-verified account) -- tested for directly here, not hidden."""
    conditions = _conditions()
    resolved = conditions["axis:amplitude_ratio=1.3"].resolved  # type: ignore[attr-defined]
    signal = simulate_condition(resolved, "axis:amplitude_ratio=1.3", seed_index=0)

    result = fit(signal.i, signal.q)
    assert result.failed is False
    assert result.params is not None

    rel_error_g = abs(result.params["amplitude_ratio"] - resolved["amplitude_ratio"]) / resolved[
        "amplitude_ratio"
    ]
    # Grounded at ~4.24% (verified directly against this exact condition,
    # seed-independent since the dominant cause -- the clamp -- is
    # deterministic); 6% gives real margin without hiding the real effect.
    assert rel_error_g < 0.06, f"g recovery: {rel_error_g:.4f} relative error"


def test_degenerate_small_arc_fraction_fails_gracefully() -> None:
    """Verified directly (heydemann.py's module docstring): at
    arc_fraction<=0.05, the moment estimator's underlying <cos^2>~1/2
    assumption breaks down badly, and WITHOUT this method's own
    self-consistency guard would silently return a wrong phase estimate
    rather than raising or failing -- exactly the silent-garbage failure
    mode docs/WEEK3-4_PLAN.md Day 17 calls out."""
    conditions = _conditions()
    for name in ["axis:arc_fraction=0.02", "axis:arc_fraction=0.05"]:
        resolved = conditions[name].resolved  # type: ignore[attr-defined]
        signal = simulate_condition(resolved, name, seed_index=0)

        result = fit(signal.i, signal.q)

        assert result.failed is True, f"{name}: expected graceful failure"
        assert result.reason == "unstable_ellipse_estimate", f"{name}: reason={result.reason}"
        assert np.all(np.isnan(result.recovered_phase)), f"{name}: expected all-NaN phase"


def test_dramatically_outperforms_atan2_and_kasa_on_classic_axes() -> None:
    """docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md Category 1: Heydemann's
    correction model IS the forward model's own distortion, so it should
    dramatically outperform both raw atan2 (no correction) and Kasa
    (circle-only -- no correction for EITHER amplitude_ratio or
    quadrature_error_rad) on the interaction grid condition combining both
    at their most extreme swept values -- a construction check, not a
    finding (per that document's Day 28 reporting rule).

    NOT tested against a dc_offset-only condition: Day 16 established Kasa
    has REAL (if baseline-eccentricity-degraded) partial correction there,
    since dc_offset IS a circle's center -- that would understate
    Heydemann's actual structural advantage, which is clearest on the two
    axes Kasa has literally zero free parameters for.

    Threshold 0.15, not the rounder 0.1 first tried: this specific
    condition includes amplitude_ratio=1.3, so the same real, understood
    ~4% clamp-interaction bias from the extreme-amplitude_ratio test above
    applies here too, measured directly at ratio~0.112 -- 0.15 keeps real
    margin without hiding that known effect."""
    conditions = _conditions()
    name = "grid:amplitude_x_quadrature:amplitude_ratio=1.3,quadrature_error_rad=0.3"
    resolved = conditions[name].resolved  # type: ignore[attr-defined]
    signal = simulate_condition(resolved, name, seed_index=0)

    heydemann_rmse = _rmse(
        wrapped_phase_error(signal.true_phase, fit(signal.i, signal.q).recovered_phase)
    )
    kasa_rmse = _rmse(
        wrapped_phase_error(signal.true_phase, fit_kasa(signal.i, signal.q).recovered_phase)
    )
    atan2_rmse = _rmse(
        wrapped_phase_error(
            signal.true_phase,
            fit_raw_atan2(
                signal.i, signal.q, mean_intensity=resolved["mean_intensity"]
            ).recovered_phase,
        )
    )

    assert heydemann_rmse < 0.15 * kasa_rmse, f"h/k ratio={heydemann_rmse / kasa_rmse:.4f}"
    assert heydemann_rmse < 0.15 * atan2_rmse, f"h/a ratio={heydemann_rmse / atan2_rmse:.4f}"
