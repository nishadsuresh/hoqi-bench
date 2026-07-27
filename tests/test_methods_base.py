"""
Tests for hoqi_bench.methods.base: FitResult, failed_result, timed_fit.

Day 15's key acceptance property (docs/WEEK3-4_PLAN.md Day 15): FitResult
is designed against the HARDEST method's needs (Day 20's iterative Köning
EIV fit -- convergence status, iteration count, parameter covariance) so
that Days 16-19's tests are not invalidated by a forced interface refactor
once Day 20 arrives. Verified directly below by constructing a FitResult
with every "iterative method" field populated, without any modification to
the dataclass itself.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench.methods.base import FitResult, failed_result, timed_fit


def test_fit_result_accommodates_a_hypothetical_iterative_method() -> None:
    """The dataclass must already support convergence status, iteration
    count, and a covariance matrix -- Day 20's Köning fit's needs -- with
    zero changes, since this interface is designed against that method
    now, on Day 15, before it exists."""
    phase = np.array([0.1, 0.2, 0.3])
    covariance = np.eye(2)

    result = FitResult(
        recovered_phase=phase,
        failed=False,
        params={"center_i": 1.0, "center_q": 1.0},
        converged=True,
        n_iter=7,
        covariance=covariance,
        runtime_s=0.0123,
    )

    assert np.array_equal(result.recovered_phase, phase)
    assert result.converged is True
    assert result.n_iter == 7
    assert result.covariance is not None
    assert np.array_equal(result.covariance, covariance)
    assert result.params == {"center_i": 1.0, "center_q": 1.0}


def test_fit_result_non_iterative_fields_default_to_none() -> None:
    """A non-iterative method (6 of the 7 planned) should be able to
    construct a FitResult supplying ONLY recovered_phase -- converged/
    n_iter/covariance/params must all default to None, not require a
    non-iterative method to fabricate values for fields that don't apply
    to it (per FitResult's own docstring)."""
    result = FitResult(recovered_phase=np.array([0.0, 1.0]))
    assert result.failed is False
    assert result.reason is None
    assert result.converged is None
    assert result.n_iter is None
    assert result.covariance is None
    assert result.params is None


def test_failed_result_fills_nan_and_sets_contract_fields() -> None:
    """docs/WEEK3_METHOD_CONTRACT.md sec2: on failure, EVERY numeric field
    NaN, failed=True, and a specific (not generic) reason code."""
    result = failed_result(10, "singular_scatter_matrix")

    assert result.recovered_phase.shape == (10,)
    assert np.all(np.isnan(result.recovered_phase))
    assert result.failed is True
    assert result.reason == "singular_scatter_matrix"
    assert result.reason != "failed", "reason code must be specific, not generic"


def test_failed_result_records_convergence_false_for_iterative_failure() -> None:
    """An iterative method's non-convergence should be distinguishable
    from a non-iterative method's failure -- converged=False (a concrete
    fact) vs. converged=None (does not apply) are different claims."""
    non_convergent = failed_result(5, "non_convergent", converged=False)
    assert non_convergent.converged is False

    non_iterative_failure = failed_result(5, "singular_scatter_matrix")
    assert non_iterative_failure.converged is None


def test_timed_fit_populates_runtime_without_altering_other_fields() -> None:
    """timed_fit is the ONE place runtime is measured (per FitResult's own
    docstring) -- confirms it fills runtime_s and leaves everything else
    from the wrapped fit_fn's own return value untouched."""
    expected_phase = np.array([0.5, 1.5, 2.5])

    def stub_fit(intensity_i: object, intensity_q: object) -> FitResult:
        return FitResult(recovered_phase=expected_phase, params={"x": 42.0})

    result = timed_fit(stub_fit, np.zeros(3), np.zeros(3))

    assert result.runtime_s is not None
    assert result.runtime_s >= 0.0
    assert np.array_equal(result.recovered_phase, expected_phase)
    assert result.params == {"x": 42.0}
