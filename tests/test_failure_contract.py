"""
Enforces `docs/WEEK3_METHOD_CONTRACT.md` §2.1 -- the Week 3 review's
binding extension to the fit-failure contract -- as a test rather than
prose.

§2.1's finding: the preregistered `failed` flag measures whether a method
DETECTS its own failure, not whether it failed. Measured over all 359
main-campaign conditions, Heydemann self-reports 24.51% failures and never
once returns an unusable answer; Fitzgibbon self-reports 0.00% and returns
an unusable answer 13.48% of the time. Reported as preregistered, without
the second number, that reads as Heydemann being the least reliable method
in the benchmark and Fitzgibbon being flawless -- the exact inverse of the
truth.

Why this needs a test and not just a document. The finding is an asymmetry
in which methods carry self-consistency guards, and every one of those
guards is a few lines inside a single method. Someone adding a plausibility
check to Kasa, or relaxing Heydemann's radius guard, would change what the
campaign's headline reliability numbers MEAN, in a diff that looks entirely
local and reasonable. Nothing else in the suite would notice: every
method's own tests would still pass. This file is what notices.

The assertions below are deliberately DIRECTIONAL, not exact rates -- the
claim being protected is "these two columns disagree, and here is which
way", not any specific percentage, which would make this a change-detector
rather than a test.

Cost: ~7,500 fits, measured at ~1.0s, so it is not gated behind a marker.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.config import load_sweep_config
from hoqi_bench.methods import METHOD_REGISTRY, fit_by_name
from hoqi_bench.metrics import wrapped_phase_error
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import simulate_condition

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"

# Fixed in `docs/WEEK3_METHOD_CONTRACT.md` §2.1 BEFORE the campaign runs,
# and not to be re-chosen after seeing results: a wrapped-phase RMSE above
# 0.5 rad is ~8% of a full cycle (~25 nm of a 316 nm HeNe half-wavelength
# range) -- an answer no practitioner could act on, whatever the method
# reports about itself.
GROSS_ERROR_RAD = 0.5

_N_SEEDS = 3


def _measure() -> dict[str, tuple[float, float]]:
    """Returns `{method: (self_reported_failure_rate, gross_error_rate)}`,
    where the second is the fraction of fits that returned `failed=False`
    while exceeding `GROSS_ERROR_RAD`."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = iter_conditions(config)
    failed = dict.fromkeys(METHOD_REGISTRY, 0)
    gross = dict.fromkeys(METHOD_REGISTRY, 0)
    total = 0

    for condition in conditions:
        for seed_index in range(_N_SEEDS):
            signal = simulate_condition(condition.resolved, condition.name, seed_index)
            total += 1
            for name in METHOD_REGISTRY:
                result = fit_by_name(
                    name,
                    signal.i,
                    signal.q,
                    mean_intensity=condition.resolved["mean_intensity"],
                )
                if result.failed:
                    failed[name] += 1
                    continue
                errors: FloatArray = wrapped_phase_error(
                    signal.true_phase, result.recovered_phase
                )
                if float(np.sqrt(np.mean(errors**2))) > GROSS_ERROR_RAD:
                    gross[name] += 1

    return {name: (failed[name] / total, gross[name] / total) for name in METHOD_REGISTRY}


def test_self_reported_failure_rate_is_not_a_reliability_ranking() -> None:
    """The core §2.1 claim, as a falsifiable statement: there exists a
    method that self-reports a HIGH failure rate while never producing an
    unusable answer, and a method that self-reports NO failures while
    producing unusable answers at a materially higher rate. If both of
    those stopped being true, §2.1's caption requirement on every
    failure-rate comparison would no longer be justified and should be
    revisited rather than left in place out of inertia."""
    rates = _measure()
    heydemann_failed, heydemann_gross = rates["heydemann"]
    fitzgibbon_failed, fitzgibbon_gross = rates["fitzgibbon"]

    assert heydemann_failed > 0.10, (
        f"heydemann self-reported failure rate {heydemann_failed:.2%} -- §2.1 measured 24.51%"
    )
    assert heydemann_gross == 0.0, (
        f"heydemann produced {heydemann_gross:.2%} unusable-but-unreported fits; §2.1's "
        "claim that its radius guard closes this mode entirely no longer holds"
    )
    assert fitzgibbon_failed < 0.01, (
        f"fitzgibbon now self-reports {fitzgibbon_failed:.2%} failures -- if a guard was "
        "added, fitzgibbon.py's 'deliberately not patched' docstring needs revisiting"
    )
    assert fitzgibbon_gross > heydemann_gross, (
        f"the §2.1 inversion no longer reproduces: fitzgibbon gross={fitzgibbon_gross:.2%}, "
        f"heydemann gross={heydemann_gross:.2%}"
    )


def test_the_naive_baseline_is_the_most_reliable_method() -> None:
    """§2.1's one genuinely non-tautological result, named there
    specifically so it cannot be invented post hoc: raw atan2 -- the
    deliberately naive floor every other method exists to beat on ACCURACY
    -- is the only method with zero on both reliability columns, because it
    fits nothing and so has nothing that can become ill-conditioned.

    `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` predicts raw atan2 will be
    the worst method on accuracy on every axis, and says nothing about
    reliability. That accuracy and reliability separate this cleanly is not
    a construction check."""
    rates = _measure()
    baseline_failed, baseline_gross = rates["raw_atan2"]
    assert baseline_failed == 0.0
    assert baseline_gross == 0.0

    correction_methods = [n for n in METHOD_REGISTRY if n != "raw_atan2"]
    assert any(rates[name][1] > 0.0 for name in correction_methods), (
        "no correction method produces unreported gross errors -- if true, the "
        "baseline is no longer distinctively reliable and §2.1 should be revisited"
    )


def test_every_method_returns_a_result_for_every_condition() -> None:
    """`docs/WEEK3_METHOD_CONTRACT.md` §2's primary rule, which §2.1
    extends rather than replaces: there is no (condition, seed) pair for
    which a method silently contributes zero rows. A failed fit is a row
    with `failed=True`, an all-NaN phase, and a SPECIFIC reason code --
    never a generic "failed", and never an absent row."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    for condition in iter_conditions(config)[::7]:
        signal = simulate_condition(condition.resolved, condition.name, seed_index=0)
        for name in METHOD_REGISTRY:
            result = fit_by_name(
                name, signal.i, signal.q, mean_intensity=condition.resolved["mean_intensity"]
            )
            assert result.recovered_phase.shape == signal.i.shape
            if result.failed:
                assert result.reason not in (None, "", "failed"), (
                    f"{name} at {condition.name}: reason={result.reason!r} is not specific"
                )
                assert np.all(np.isnan(result.recovered_phase))
            else:
                assert result.reason is None
                assert np.all(np.isfinite(result.recovered_phase))
