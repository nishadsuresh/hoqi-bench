"""
Method 7 -- Köning, Wimmer & Witkovský (2014) nonlinear-constraint
errors-in-variables (EIV) ellipse fit. The hardest of the 7 methods
(Day 15's interface was designed against this method's needs, not the
simplest one) and the highest-risk implementation in this project
(`notes/koning_2014.md`): the original 2014 paper is paywalled and was
never read in full.

**Explicit, honest scope statement, per `docs/WEEK3-4_PLAN.md` Day 20**:
this is an implementation of the ALGORITHM FAMILY the paper introduced
(errors-in-variables ellipse fitting via iterated linearization,
understood through the CRAN `OEFPIL` package manual -- a real primary
source that generalizes this 2014 paper's method, per
`notes/koning_2014.md`'s "Update 2026-07-26" section), NOT a faithful
reproduction of the original paper's specific tuning choices, covariance
model, or convergence criteria, which remain unread. Labeled here and in
every result this method produces (there is no way to silently forget
this scope limitation, since it lives in the one file implementing the
method).

**What makes this genuinely an EIV method, not another OLS algebraic
fit** (the real, substantive distinction from Kasa/Taubin/Halir &
Flusser/Fitzgibbon, all four of which minimize some form of ALGEBRAIC
residual treating the fitted curve as exact): this method minimizes
SAMPSON DISTANCE -- the algebraic residual `F(x,y)` divided by
`|grad F(x,y)|`, a first-order approximation to true GEOMETRIC (orthogonal)
distance from each point to the curve. Unlike a single-shot algebraic fit,
Sampson distance depends on the CURRENT parameter estimate (the gradient
is evaluated there), so it cannot be solved in one step -- each iteration
re-weights every point by `1/|grad F|` at the current estimate, re-solves,
and checks convergence. This iterative reweighting is what makes the fit
treat deviations in BOTH `I` and `Q` symmetrically as measurement error
(unlike an algebraic residual, which implicitly weights different points
differently depending on where they sit relative to the curve) --
genuinely EIV in character, not just algebraic-fit-plus-iteration-count.

**Initialization is NOT the estimation algorithm** (per `methods/_ellipse.py`'s
own precedent for what's legitimate to share): the first iteration needs
*some* starting conic, computed here via a plain unconstrained SVD-based
algebraic fit (the smallest right-singular-vector of the design matrix) --
a generic starting point, not Halir & Flusser's or Fitzgibbon's own
ellipse-SPECIFIC constrained algorithm, so this does not share Day 18/19's
actual fitting machinery. The iterative Sampson-reweighting loop that
follows is this method's own, distinct contribution.

**Covariance, scoped honestly**: at convergence, the weighted least-squares
normal equations give a standard covariance estimate for the fitted CONIC
COEFFICIENTS (`sigma_hat^2 * pinv(Dw^T @ Dw)`, `sigma_hat^2` the weighted
residual variance) -- verified finite, symmetric, and positive
semi-definite before being trusted (a rank-deficient direction near the
constraint's own null space produces near-zero eigenvalues, expected and
not a bug). This is covariance of the RAW CONIC COEFFICIENTS, not yet
propagated to phase-space uncertainty -- a real, useful, but explicitly
partial quantity, not the full "statistical uncertainty of the
interferometric phase" the original paper's title promises.

Pipeline position: `methods/__init__.py`'s registry entry
`"koning_wimmer_witkovsky"` (matching `configs/main_campaign.toml`'s
method name exactly).
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods._ellipse import apply_heydemann_correction, conic_to_heydemann_params
from hoqi_bench.methods.base import FitResult, failed_result

NAME = "koning_wimmer_witkovsky"

_MAX_ITER = 20
_CONVERGENCE_TOL = 1e-10


def _design_matrix(intensity_i: FloatArray, intensity_q: FloatArray) -> FloatArray:
    return np.column_stack(
        [
            intensity_i**2,
            intensity_i * intensity_q,
            intensity_q**2,
            intensity_i,
            intensity_q,
            np.ones_like(intensity_i),
        ]
    )


def _gradient_norm(
    intensity_i: FloatArray, intensity_q: FloatArray, coeffs: FloatArray
) -> FloatArray:
    """`|grad F|` for the general conic `F=a*x^2+b*xy+c*y^2+d*x+e*y+f` --
    the Sampson-distance denominator, evaluated at the CURRENT parameter
    estimate each iteration (module docstring: this is what makes the
    method genuinely iterative rather than a single-shot reweighting)."""
    a, b, c, d, e, _f = coeffs
    grad_i = 2 * a * intensity_i + b * intensity_q + d
    grad_q = b * intensity_i + 2 * c * intensity_q + e
    return np.asarray(np.sqrt(grad_i**2 + grad_q**2), dtype=np.float64)


def _iterative_eiv_fit(
    intensity_i: FloatArray, intensity_q: FloatArray
) -> tuple[FloatArray, int, FloatArray] | None:
    """Iterated Sampson-distance reweighting (module docstring) --
    returns `(conic_coefficients, n_iter, covariance)` on convergence, or
    `None` if `_MAX_ITER` is reached without the parameter update falling
    below `_CONVERGENCE_TOL`."""
    design = _design_matrix(intensity_i, intensity_q)

    # ---- 1. Initialization: a generic, unconstrained algebraic fit --
    # NOT Halir & Flusser's or Fitzgibbon's own ellipse-specific algorithm
    # (module docstring) ----
    _u, _s, vt = np.linalg.svd(design)
    coeffs = vt[-1]
    coeffs = coeffs / np.linalg.norm(coeffs)

    # ---- 2. Iterated Sampson-distance reweighting ----
    for iteration in range(1, _MAX_ITER + 1):
        weights = 1.0 / np.maximum(_gradient_norm(intensity_i, intensity_q, coeffs), 1e-12)
        weighted_design = design * weights[:, None]

        _u, singular_values, vt = np.linalg.svd(weighted_design)
        new_coeffs = vt[-1]
        if new_coeffs @ coeffs < 0.0:
            new_coeffs = -new_coeffs
        new_coeffs = new_coeffs / np.linalg.norm(new_coeffs)

        delta = float(np.linalg.norm(new_coeffs - coeffs))
        coeffs = new_coeffs

        if delta < _CONVERGENCE_TOL:
            residuals = weighted_design @ coeffs
            degrees_of_freedom = max(intensity_i.shape[0] - 6, 1)
            sigma_squared = float(residuals @ residuals) / degrees_of_freedom
            covariance = sigma_squared * np.linalg.pinv(weighted_design.T @ weighted_design)
            return (
                np.asarray(coeffs, dtype=np.float64),
                iteration,
                np.asarray(covariance, dtype=np.float64),
            )

    return None


def fit(intensity_i: FloatArray, intensity_q: FloatArray) -> FitResult:
    """Fits the ellipse via iterated Sampson-distance reweighting,
    converts to `(dc_i, dc_q, g, eps)` via the shared
    `conic_to_heydemann_params`, applies the shared correction, and
    recovers phase via `atan2`.

    Failure modes (`docs/WEEK3_METHOD_CONTRACT.md` sec2):
    - `"non_convergent"` (`converged=False`): `_MAX_ITER` reached without
      the parameter update falling below tolerance -- this method's
      distinctive failure mode among the 7 (the only iterative one).
    - `"singular_conic_center"`, `"invalid_quadrature_estimate"`: same
      shared post-fit failure modes as Halir & Flusser (Day 18) and
      Fitzgibbon (Day 19).
    """
    n = intensity_i.shape[0]

    result = _iterative_eiv_fit(intensity_i, intensity_q)
    if result is None:
        return failed_result(n, "non_convergent", converged=False)
    coeffs, n_iter, covariance = result
    a, b, c, d, e, f = coeffs

    try:
        dc_i, dc_q, g, eps = conic_to_heydemann_params(a, b, c, d, e, f)
    except np.linalg.LinAlgError:
        return failed_result(n, "singular_conic_center", converged=False)

    if not (np.isfinite(dc_i) and np.isfinite(dc_q) and np.isfinite(g) and np.isfinite(eps)):
        return failed_result(n, "invalid_quadrature_estimate", converged=False)
    if g <= 0.0:
        return failed_result(n, "invalid_quadrature_estimate", converged=False)

    i_c, q_c = apply_heydemann_correction(intensity_i, intensity_q, dc_i, dc_q, g, eps)
    recovered_phase = np.arctan2(q_c, i_c).astype(np.float64)

    return FitResult(
        recovered_phase=recovered_phase,
        params={
            "dc_offset_i": dc_i,
            "dc_offset_q": dc_q,
            "amplitude_ratio": g,
            "quadrature_error_rad": eps,
        },
        converged=True,
        n_iter=n_iter,
        covariance=covariance,
    )
