"""
Tests for hoqi_bench.methods's registry-level dispatch: `fit_by_name` and
`timed_fit_by_name`.

Added Week 5 Task 3, Day 31 (`docs/WEEK5_PREFLIGHT_AUDIT.md` finding P3's
fix): `timed_fit_by_name` did not exist before this task. `_resolve_fit_call`
is the shared dispatch helper both wrap -- these tests confirm the ONE
place the registry's non-uniform calling convention is handled (raw_atan2
alone takes `mean_intensity`) behaves identically whether reached through
the timed or untimed entry point, and that only `timed_fit_by_name`
populates `runtime_s`.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench.methods import fit_by_name, timed_fit_by_name

_I = np.array([1.0, 0.0, -1.0, 0.0])
_Q = np.array([0.0, 1.0, 0.0, -1.0])


def test_fit_by_name_does_not_populate_runtime() -> None:
    """The untimed entry point must stay untimed -- runner.py's own fix
    (Day 31) specifically switched to timed_fit_by_name BECAUSE fit_by_name
    never measures runtime; this pins that fact so a future edit can't
    silently make fit_by_name start timing (which would then make this
    project's TWO method-dispatch entry points behave inconsistently)."""
    result = fit_by_name("raw_atan2", _I, _Q, mean_intensity=0.0)
    assert result.runtime_s is None


def test_timed_fit_by_name_populates_runtime_and_is_positive() -> None:
    result = timed_fit_by_name("raw_atan2", _I, _Q, mean_intensity=0.0)
    assert result.runtime_s is not None
    assert result.runtime_s >= 0.0


def test_timed_fit_by_name_agrees_with_fit_by_name_on_every_registered_method() -> None:
    """Both entry points share `_resolve_fit_call`'s dispatch, so for every
    registered method (not just raw_atan2's kwarg-taking special case) the
    RECOVERED PHASE must be identical between the timed and untimed calls
    -- timing must never change what is actually computed."""
    from hoqi_bench.methods import METHOD_REGISTRY

    for method_name in METHOD_REGISTRY:
        untimed = fit_by_name(method_name, _I, _Q, mean_intensity=0.5)
        timed = timed_fit_by_name(method_name, _I, _Q, mean_intensity=0.5)
        assert untimed.failed == timed.failed, method_name
        if not untimed.failed:
            assert np.array_equal(untimed.recovered_phase, timed.recovered_phase), method_name
        assert untimed.runtime_s is None, method_name
        assert timed.runtime_s is not None, method_name


def test_timed_fit_by_name_passes_mean_intensity_only_to_raw_atan2() -> None:
    """The one non-uniform branch `_resolve_fit_call` exists to handle,
    confirmed through the TIMED entry point specifically (Task 3's own
    reason for existing): a wrong mean_intensity reaching raw_atan2 (or
    reaching a method that doesn't want it) would previously have only
    been caught if fit_by_name itself was tested -- this exercises the
    same dispatch through timed_fit_by_name, which runner.py actually
    calls in production."""
    # A center-far-from-zero mean_intensity changes raw_atan2's recovered
    # phase relative to mean_intensity=0.0 -- confirms the kwarg actually
    # reached the method, not just that the call didn't raise.
    default_center = timed_fit_by_name("raw_atan2", _I, _Q, mean_intensity=0.0)
    shifted_center = timed_fit_by_name("raw_atan2", _I, _Q, mean_intensity=0.3)
    assert not np.array_equal(default_center.recovered_phase, shifted_center.recovered_phase)
