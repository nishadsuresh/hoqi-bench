"""
Day 21 -- the cross-validation gate (`docs/WEEK3-4_PLAN.md` Day 21,
`docs/WEEK3_METHOD_CONTRACT.md` §3). The one never-skip gate between Week
3's method zoo and Week 4's campaign.

Three tiers, in the order `docs/WEEK3-4_PLAN.md` §0.3 ranks them by
evidential strength -- deliberately NOT "the 7 methods agree with each
other," which §0.2 already established is near-worthless as evidence
(7 implementations by one author in one week are not independent samples,
so correlated authorship error survives duplication perfectly):

- **Tier 1a, the analytic oracle (strongest).** On noiseless data generated
  EXACTLY from `docs/experimental_design.md` Section 1's forward model,
  every method whose model can represent that data must recover it to
  machine precision. This re-asserts no method's own formula -- the
  reference is the generating equation, not another fit -- and it covers
  all 7 methods, unlike Day 19's Tier 2 external packages, which cover only
  Halir & Flusser and Fitzgibbon.
- **Tier 1b, the same oracle through the project's OWN pipeline.** Tier 1a
  generates its data analytically and so cannot see a defect that lives in
  `simulate.py`/`arc.py` rather than in a method. Tier 1b re-runs the same
  exactness claim on the signal `simulate_condition` actually produces for
  the cleanest condition the campaign's schema can express. **This is the
  test that failed when this gate was first run** -- see
  `docs/journal/day21.md` for the root cause (`build_arc_ramp`'s
  `endpoint=True` convention duplicated the phase-0 sample at
  `arc_fraction=1.0`, which biased exactly one method by exactly `1/N` rad
  and would have produced a spurious 1/N "sample-efficiency" curve for
  Heydemann across the whole preregistered `samples_per_fit` axis).
- **Tier 3, the internal falsifiable predictions** fixed in advance in
  `docs/WEEK3_METHOD_CONTRACT.md` §3.2-3.3. §3.3's Taubin<->Kasa half is
  already covered by `tests/test_taubin.py` (as narrowed by that
  section's 2026-07-27 deviation); what this file adds is §3.2's
  ILL-CONDITIONED half, which nothing tested before today -- and which is
  asserted here in the direction `docs/journal/day03.md` actually MEASURED,
  not the direction §3.2 originally claimed. See that section's 2026-07-27
  (Day 21) deviation note: the contract had the ordering backwards.

Tier 2 (external packages) lives in `tests/test_external_cross_validation.py`,
pulled forward to Day 19 on purpose so a disagreement had days of debugging
headroom rather than hours before this gate.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods import METHOD_REGISTRY
from hoqi_bench.methods._ellipse import conic_to_heydemann_params
from hoqi_bench.methods.fitzgibbon import _fit_ellipse_conic as fitzgibbon_conic
from hoqi_bench.methods.halir_flusser import _fit_ellipse_conic as halir_flusser_conic
from hoqi_bench.metrics import wrapped_phase_error
from hoqi_bench.simulate import simulate_condition

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"

# The four methods that fit a general conic and can therefore REPRESENT the
# forward model's tilted, off-center ellipse exactly. The other three
# (raw_atan2, kasa, taubin) structurally cannot -- raw_atan2 fits nothing,
# and Kasa/Taubin fit a 3-parameter CIRCLE with no free parameter for
# eccentricity or tilt (docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md). That is a
# prediction, so it is tested as one below, not just asserted in prose.
_GENERAL_CONIC_METHODS = ("heydemann", "halir_flusser", "fitzgibbon", "koning_wimmer_witkovsky")
_CIRCLE_ONLY_METHODS = ("raw_atan2", "kasa", "taubin")

# Tolerances measured before being written down (this project's convention
# for every threshold -- cf. heydemann.py's _RADIUS_CONSISTENCY_THRESHOLD),
# not chosen as round numbers and then hoped for:
#   Tier 1a, worst observed across N in {20, 60, 200, 1000}: 4.2e-14 on any
#   recovered parameter, 4.0e-14 rad on recovered phase. 1e-11 leaves ~3
#   orders of margin -- tight enough that a real regression cannot hide
#   inside it, loose enough not to fail on a different BLAS's summation
#   order.
_TIER1_TOL = 1e-11

# Tier 1b's floor is NOT floating point -- it is the residual Poisson shot
# noise the campaign's schema cannot switch off (see `_clean_condition`).
# At photon_scale=1e14 the six unaffected methods sit at 1.1e-7 rad RMS,
# flat in N. 1e-5 is ~100x above that floor and ~1000x below the 1.3e-2
# artifact this test was written to catch.
_TIER1B_TOL = 1e-5

# The preregistered gate tolerance (`configs/main_campaign.toml`'s own
# `tolerance = 0.01`, and docs/WEEK3_METHOD_CONTRACT.md §3.1). Used here
# EXACTLY as pre-committed. Note recorded in that section's Day 21
# deviation: this tolerance turns out to be ~750x too loose to have caught
# the real defect Tier 1b caught, which is precisely why §0.3 ranks the
# analytic oracle above method-agreement and why this is not the gate's
# load-bearing check.
_PREREGISTERED_TOLERANCE = 0.01


def _rmse(errors: FloatArray) -> float:
    return float(np.sqrt(np.mean(errors**2)))


# ---- 1. The analytic oracle's generator: docs/experimental_design.md
# Section 1's forward model, written out directly rather than called
# through src/ -- an oracle that shares code with the unit under test is
# not an oracle (this project's oracle-independence convention, cf.
# tests/test_kasa.py and tests/test_taubin.py's own reconstructions) ----


def _exact_signal(
    n_points: int, dc_i: float, dc_q: float, amplitude: float, g: float, eps: float
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """`I = I0 + A*cos(phi)`, `Q = Q0 + A*g*sin(phi + eps)` -- the forward
    model exactly, with no noise, no hysteresis and no sampling machinery.

    `endpoint=False` is REQUIRED here, not stylistic: a complete equispaced
    cycle is what makes `<cos^2(phi)> = 1/2` and `<cos(phi)*sin(phi)> = 0`
    hold EXACTLY rather than to O(1/N), and Heydemann's second-order-moment
    estimator (`heydemann.py`) is exact only under those identities.
    Including both endpoints samples phase 0 twice and is what Tier 1b
    below exists to detect in the real pipeline.
    """
    phase = np.linspace(0.0, 2 * np.pi, n_points, endpoint=False)
    intensity_i = dc_i + amplitude * np.cos(phase)
    intensity_q = dc_q + amplitude * g * np.sin(phase + eps)
    return (
        np.asarray(intensity_i, dtype=np.float64),
        np.asarray(intensity_q, dtype=np.float64),
        np.asarray(phase, dtype=np.float64),
    )


def _analytic_conic(
    dc_i: float, dc_q: float, amplitude: float, g: float, eps: float
) -> tuple[float, float, float, float, float, float]:
    """The conic `A*x^2+B*xy+C*y^2+D*x+E*y+F=0` that `_exact_signal`'s
    trajectory lies on, in closed form -- a SECOND, independent oracle,
    for the shared `conic_to_heydemann_params` conversion specifically.

    Derivation (from the forward model above, eliminating `phi`): with
    `u = (I-I0)/A` and `w = (Q-Q0)/(A*g)`, the model gives `u = cos(phi)`
    and `w = sin(phi)*cos(eps) + cos(phi)*sin(eps)`, so
    `w - u*sin(eps) = sin(phi)*cos(eps)`. Substituting into
    `cos^2(phi) + sin^2(phi) = 1` and clearing `cos^2(eps)`:

        u^2 + w^2 - 2*u*w*sin(eps) = cos^2(eps)

    Multiplying through by `A^2` and writing it in `(I-I0, Q-Q0)`:

        (I-I0)^2 + (Q-Q0)^2/g^2 - 2*(I-I0)*(Q-Q0)*sin(eps)/g
            = A^2 * cos^2(eps)

    which is expanded to uncentered `(I, Q)` below.
    """
    a = 1.0
    b = -2.0 * np.sin(eps) / g
    c = 1.0 / g**2
    d = -2.0 * a * dc_i - b * dc_q
    e = -2.0 * c * dc_q - b * dc_i
    f = a * dc_i**2 + b * dc_i * dc_q + c * dc_q**2 - amplitude**2 * np.cos(eps) ** 2
    return a, float(b), float(c), float(d), float(e), float(f)


def _clean_condition(**overrides: float) -> dict[str, float]:
    """The condition `docs/WEEK3_METHOD_CONTRACT.md` §3.1 specifies:
    noiseless, full-circle, and undistorted (`amplitude_ratio=1.0`,
    `quadrature_error_rad=0.0`, `dc_offset=0.0`).

    Built by hand rather than pulled from `configs/main_campaign.toml`
    because NO condition in that campaign is fully clean: its baseline
    carries `amplitude_ratio=1.1`, `quadrature_error_rad=0.1` and
    `dc_offset=0.02`, so each OFAT axis zeroes at most one of the three
    while the other two stay at their distorted baseline. Everything else
    here matches the campaign baseline exactly.

    `photon_scale` is the one parameter with no true "off" value --
    `noise.poisson_noise`'s own docstring records that any real detector
    receiving light has SOME shot noise, so the campaign uses `1e7` as a
    "negligible" placeholder rather than an off switch. §3.1's gate below
    uses that campaign value; Tier 1b overrides it far higher, since its
    claim is about STRUCTURAL exactness and shot noise would otherwise set
    the floor.
    """
    resolved = {
        "mean_intensity": 1.0,
        "contrast": 0.9,
        "amplitude_ratio": 1.0,
        "quadrature_error_rad": 0.0,
        "dc_offset": 0.0,
        "arc_fraction": 1.0,
        "noise_std": 0.0,
        "samples_per_fit": 60.0,
        "hysteresis_magnitude": 0.0,
        "photon_scale": 1.0e7,
    }
    resolved.update(overrides)
    return resolved


def _fit_all(
    intensity_i: FloatArray, intensity_q: FloatArray, mean_intensity: float
) -> dict[str, FloatArray]:
    """Every registered method's recovered phase, keyed by name -- with
    `raw_atan2`'s one method-specific keyword supplied, the same way
    `scripts/robustness_matrix.py` and Day 20's campaign smoke test do."""
    phases: dict[str, FloatArray] = {}
    for name, fit_fn in METHOD_REGISTRY.items():
        kwargs = {"mean_intensity": mean_intensity} if name == "raw_atan2" else {}
        result = fit_fn(intensity_i, intensity_q, **kwargs)
        assert not result.failed, f"{name} failed on a gate condition: {result.reason}"
        phases[name] = result.recovered_phase
    return phases


# ---- 2. Tier 1a -- the analytic oracle ----


def test_tier1a_general_conic_methods_recover_the_generating_ellipse() -> None:
    """The gate's strongest instrument (docs/WEEK3-4_PLAN.md §0.3): on
    data generated exactly from the forward model, every method that can
    REPRESENT that model must recover its four parameters to machine
    precision. Swept over N because a method could be exact at one sample
    count by coincidence and biased at another -- Heydemann's moment
    estimator in particular has an O(1/N) failure mode when the equispaced
    -cycle identities do not hold (see `_exact_signal`)."""
    truth = {
        "dc_offset_i": 1.05,
        "dc_offset_q": 0.97,
        "amplitude_ratio": 1.3,
        "quadrature_error_rad": 0.15,
    }
    for n_points in (20, 60, 200, 1000):
        intensity_i, intensity_q, _ = _exact_signal(
            n_points, dc_i=1.05, dc_q=0.97, amplitude=0.9, g=1.3, eps=0.15
        )
        for name in _GENERAL_CONIC_METHODS:
            result = METHOD_REGISTRY[name](intensity_i, intensity_q)
            assert not result.failed, f"{name} failed on exact data (N={n_points}): {result.reason}"
            assert result.params is not None
            for key, expected in truth.items():
                error = abs(result.params[key] - expected)
                assert error < _TIER1_TOL, (
                    f"{name} at N={n_points}: {key} off by {error:.3e} "
                    f"(got {result.params[key]!r}, expected {expected})"
                )


def test_tier1a_general_conic_methods_recover_the_generating_phase() -> None:
    """The same oracle at the level the benchmark actually reports --
    recovered phase, compared via the contract §1 wrapped-phase metric,
    against the phase that GENERATED the data (not against another
    method's fit)."""
    for n_points in (20, 60, 200):
        intensity_i, intensity_q, phase = _exact_signal(
            n_points, dc_i=1.05, dc_q=0.97, amplitude=0.9, g=1.3, eps=0.15
        )
        for name in _GENERAL_CONIC_METHODS:
            result = METHOD_REGISTRY[name](intensity_i, intensity_q)
            assert not result.failed
            error = _rmse(wrapped_phase_error(phase, result.recovered_phase))
            assert error < _TIER1_TOL, f"{name} at N={n_points}: phase RMSE {error:.3e} rad"


def test_tier1a_shared_conic_conversion_matches_its_closed_form() -> None:
    """`conic_to_heydemann_params` is the one piece of post-fit machinery
    all four general-conic methods share (`methods/_ellipse.py`), so a bug
    in it would move all four IDENTICALLY -- exactly the correlated error
    §0.2 warns method-agreement cannot detect. Checked here against the
    closed-form conic derived independently in `_analytic_conic`, which is
    algebra, not a fit."""
    dc_i, dc_q, amplitude, g, eps = 1.05, 0.97, 0.9, 1.3, 0.15
    recovered = conic_to_heydemann_params(*_analytic_conic(dc_i, dc_q, amplitude, g, eps))
    truth = (dc_i, dc_q, g, eps)
    for got, expected in zip(recovered, truth, strict=True):
        assert abs(got - expected) < _TIER1_TOL, f"got {recovered!r}, expected {truth!r}"


def test_tier1a_all_seven_methods_are_exact_on_an_undistorted_circle() -> None:
    """The one condition where all 7 methods' models CAN all represent the
    data: `g=1`, `eps=0`, and the DC offsets at the nominal `mean_intensity`
    raw_atan2 is allowed to assume. Contract §3.1's "any method failing
    this on the easiest possible condition is a bug in that method" applies
    at full strength here -- machine precision, not the 1% tolerance."""
    mean_intensity = 1.0
    intensity_i, intensity_q, phase = _exact_signal(
        60, dc_i=mean_intensity, dc_q=mean_intensity, amplitude=0.9, g=1.0, eps=0.0
    )
    for name, recovered_phase in _fit_all(intensity_i, intensity_q, mean_intensity).items():
        error = _rmse(wrapped_phase_error(phase, recovered_phase))
        assert error < _TIER1_TOL, f"{name}: phase RMSE {error:.3e} rad on an exact circle"


def test_tier1a_circle_only_methods_provably_cannot_fit_an_ellipse() -> None:
    """`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` predicts raw_atan2, Kasa
    and Taubin have NO free parameter for `amplitude_ratio` or
    `quadrature_error_rad`. Tested as a falsifiable prediction rather than
    left as prose: if one of them WERE somehow exact on ellipse data, that
    document's per-axis reasoning -- which Week 4's Day 28 reporting rule
    depends on to separate tautologies from findings -- would be wrong.
    The threshold is deliberately far from both regimes (observed: ~1.4e-1
    rad for all three, vs <1e-13 for the four conic fitters)."""
    intensity_i, intensity_q, phase = _exact_signal(
        60, dc_i=1.05, dc_q=0.97, amplitude=0.9, g=1.3, eps=0.15
    )
    for name in _CIRCLE_ONLY_METHODS:
        kwargs = {"mean_intensity": 1.0} if name == "raw_atan2" else {}
        result = METHOD_REGISTRY[name](intensity_i, intensity_q, **kwargs)
        assert not result.failed
        error = _rmse(wrapped_phase_error(phase, result.recovered_phase))
        assert error > 1e-2, (
            f"{name} recovered an ELLIPSE to {error:.3e} rad, but "
            "docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md says it structurally cannot"
        )


# ---- 3. Tier 1b -- the same oracle, through the project's own pipeline ----


def test_tier1b_exactness_survives_the_projects_own_simulation_path() -> None:
    """The bridge test, and the one that actually caught something.

    Tier 1a proves the four general-conic methods are exact on the forward
    model. `simulate_condition` at the clean condition produces (up to
    negligible shot noise) that same forward model. So all four must STILL
    be exact here -- and if one is not, the defect is in the pipeline, not
    in the method, because Tier 1a already cleared the method.

    Swept over the full preregistered `samples_per_fit` axis specifically:
    the defect this caught (`docs/journal/day21.md`) scaled as exactly
    `1/N`, which at a single N looks like an unremarkable small error and
    across the axis looks like a publishable sample-efficiency curve."""
    for n_points in (20, 60, 200, 1000):
        resolved = _clean_condition(samples_per_fit=float(n_points), photon_scale=1.0e14)
        signal = simulate_condition(resolved, "gate:clean", seed_index=0)
        for name in _GENERAL_CONIC_METHODS:
            result = METHOD_REGISTRY[name](signal.i, signal.q)
            assert not result.failed, f"{name} failed at N={n_points}: {result.reason}"
            error = _rmse(wrapped_phase_error(signal.true_phase, result.recovered_phase))
            assert error < _TIER1B_TOL, (
                f"{name} at N={n_points}: {error:.3e} rad RMSE through simulate_condition, "
                f"but Tier 1a shows it is exact on this same forward model -- "
                f"the defect is in the simulation path, not the method"
            )


# ---- 4. Contract §3.1 -- the seven-way agreement gate, as pre-committed ----


def test_gate_3_1_every_method_recovers_the_clean_condition_within_tolerance() -> None:
    """`docs/WEEK3_METHOD_CONTRACT.md` §3.1, applied exactly as written:
    on the noiseless, full-circle, undistorted condition, every method must
    recover to within the preregistered 1% relative RMS threshold of ground
    truth.

    Denominator fixed HERE, explicitly, because §3.1 says "within
    tolerance = 0.01 (the preregistered 1% relative RMS error threshold)"
    without naming what the error is relative to -- and leaving that open
    until after seeing results is exactly how a gate gets rationalized into
    passing. The record's full-scale phase excursion (`arc_fraction * 2*pi`)
    is used, so "1% relative" means 1% of the phase range the record
    actually traverses. This is the more conservative of the two readings
    considered (the alternative, dividing by the signal's RMS rather than
    its range, is ~1.7x more permissive)."""
    resolved = _clean_condition()
    signal = simulate_condition(resolved, "gate:clean", seed_index=0)
    full_scale_rad = resolved["arc_fraction"] * 2 * np.pi

    for name, recovered_phase in _fit_all(signal.i, signal.q, resolved["mean_intensity"]).items():
        relative_error = _rmse(wrapped_phase_error(signal.true_phase, recovered_phase)) / (
            full_scale_rad
        )
        assert relative_error < _PREREGISTERED_TOLERANCE, (
            f"{name}: {relative_error:.4%} relative RMS error vs ground truth "
            f"on the cleanest possible condition"
        )


def test_gate_3_1_every_pair_of_methods_agrees_within_tolerance() -> None:
    """§3.1's other half -- the 21 pairwise comparisons must ALSO agree,
    not just each method against truth. Weak evidence on its own (§0.2),
    but it is what the contract pre-committed to, and a method that agreed
    with truth while disagreeing with its peers would still be worth
    knowing about."""
    resolved = _clean_condition()
    signal = simulate_condition(resolved, "gate:clean", seed_index=0)
    full_scale_rad = resolved["arc_fraction"] * 2 * np.pi
    phases = _fit_all(signal.i, signal.q, resolved["mean_intensity"])

    names = list(phases)
    for first in range(len(names)):
        for second in range(first + 1, len(names)):
            disagreement = _rmse(
                wrapped_phase_error(phases[names[first]], phases[names[second]])
            ) / full_scale_rad
            assert disagreement < _PREREGISTERED_TOLERANCE, (
                f"{names[first]} vs {names[second]}: {disagreement:.4%} relative disagreement"
            )


# ---- 5. Tier 3 -- contract §3.2's ill-conditioned half, in the direction
# docs/journal/day03.md actually measured (see that section's Day 21
# deviation note: the contract stated the ordering backwards) ----

# Day 3's own `near_degenerate_15deg` regime, reconstructed here rather
# than imported (scripts/ is not on pytest's pythonpath, and the
# oracle-independence convention applies).
_DAY3_ELLIPSE = dict(center_x=2.0, center_y=-1.0, semi_major=8.0, rotation_rad=0.3)


def _sample_day3_regime(
    semi_minor: float, arc_end_deg: float, seed: int, n_points: int = 60
) -> tuple[FloatArray, FloatArray]:
    rng = np.random.default_rng(seed)
    theta = np.linspace(0.0, np.deg2rad(arc_end_deg), n_points)
    ex = float(_DAY3_ELLIPSE["semi_major"]) * np.cos(theta)
    ey = semi_minor * np.sin(theta)
    rotation = float(_DAY3_ELLIPSE["rotation_rad"])
    cos_r, sin_r = np.cos(rotation), np.sin(rotation)
    x = float(_DAY3_ELLIPSE["center_x"]) + ex * cos_r - ey * sin_r
    y = float(_DAY3_ELLIPSE["center_y"]) + ex * sin_r + ey * cos_r
    x = x + rng.normal(0, 0.001, size=n_points)
    y = y + rng.normal(0, 0.001, size=n_points)
    return np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)


def _failure_rates(semi_minor: float, arc_end_deg: float, n_seeds: int) -> tuple[float, float]:
    fitzgibbon_failures = halir_flusser_failures = 0
    for seed in range(n_seeds):
        x, y = _sample_day3_regime(semi_minor, arc_end_deg, seed)
        if fitzgibbon_conic(x, y) is None:
            fitzgibbon_failures += 1
        if halir_flusser_conic(x, y) is None:
            halir_flusser_failures += 1
    return fitzgibbon_failures / n_seeds, halir_flusser_failures / n_seeds


def test_gate_3_2_the_two_conic_fitters_diverge_when_ill_conditioned() -> None:
    """§3.2 requires the ill-conditioned regime to show DIVERGENCE, and to
    reproduce `docs/journal/day03.md`'s ordering. Day 3 measured that
    ordering as Fitzgibbon 0% / Halir & Flusser 60% at
    `near_degenerate_15deg` -- Halir & Flusser failing MORE, because its
    block decomposition must invert `S3` (cond ~1.2e8 here), a failure mode
    the 1998 paper does not analyse. Asserted in that measured direction.
    """
    fitzgibbon_rate, halir_flusser_rate = _failure_rates(
        semi_minor=0.05, arc_end_deg=15.0, n_seeds=30
    )
    assert halir_flusser_rate > 0.3, (
        f"Halir & Flusser failed {halir_flusser_rate:.0%}, but docs/journal/day03.md "
        "measured ~60% here -- its S3-conditioning failure mode is not reproducing"
    )
    assert halir_flusser_rate > fitzgibbon_rate, (
        f"ordering inverted vs docs/journal/day03.md: fitzgibbon={fitzgibbon_rate:.0%}, "
        f"halir_flusser={halir_flusser_rate:.0%}"
    )


def test_gate_3_2_fitzgibbons_own_fragility_is_still_present_unpatched() -> None:
    """The other half of the same claim, and the one that protects Day 19's
    scientific point: Fitzgibbon's singular-`C` ambiguity must actually
    still be there. If a future change quietly added a tie-break rule or
    relaxed the `a^T*C*a > 0` tolerance, `fitzgibbon.py`'s "deliberately
    not patched" docstring would become false and the Fitzgibbon <-> Halir
    & Flusser comparison would lose its meaning -- with nothing failing.

    Uses the thinner (`semi_minor=0.001`) ellipse from Day 3's own
    `demonstrate_clean_divergence`, where the ambiguity is reachable at
    double precision; at `semi_minor=0.05` Fitzgibbon does not fail at all
    (the test above). Measured over 200 seeds while writing this: 12%
    Fitzgibbon failures (24/200, of which 24 are the AMBIGUOUS mode) vs 42%
    for Halir & Flusser."""
    fitzgibbon_rate, halir_flusser_rate = _failure_rates(
        semi_minor=0.001, arc_end_deg=15.0, n_seeds=60
    )
    assert fitzgibbon_rate > 0.0, (
        "Fitzgibbon did not fail once in the regime where Day 3 found genuine "
        "eigenvector ambiguity -- its fragility may have been patched away, which "
        "fitzgibbon.py's module docstring forbids"
    )
    assert halir_flusser_rate > fitzgibbon_rate, (
        f"fitzgibbon={fitzgibbon_rate:.0%}, halir_flusser={halir_flusser_rate:.0%}"
    )
