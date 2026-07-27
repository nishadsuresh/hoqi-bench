"""
Method 5 -- Fitzgibbon, Pilu & Fisher (1999) direct ellipse-specific
least-squares fit, implemented FAITHFULLY -- including its known
numerical fragility, deliberately preserved rather than patched.

Core algebra matches this project's own Day 3 exploration
(`scripts/explore_ellipse_constraints.py`'s `fit_ellipse_fitzgibbon`),
promoted into the package proper, per `notes/fitzgibbon_1999.md`: poses
`min ||Da||^2 s.t. a^T*C*a=1` as ONE 6x6 generalized eigenvalue problem
`S*a = lambda*C*a` (`S` the scatter matrix `D^T*D`, `D` the `Nx6` design
matrix `[x^2,xy,y^2,x,y,1]`, `C` all-zero except `C[0,2]=C[2,0]=2,
C[1,1]=-1`) -- no block decomposition, no dimensionality reduction. This
IS the method Halir & Flusser (Day 18) exists to fix; the comparison
between them is scientifically meaningful only if this implementation is
allowed to actually be fragile where the paper says it is, not quietly
patched into a second Halir & Flusser.

**Why this matters enough to say twice**: it would be easy to "improve"
this method by adding a fallback, a tolerance relaxation, or a tie-break
rule for its known ambiguity below -- and each of those would misrepresent
BOTH papers. Fitzgibbon's own contribution (first non-iterative,
ellipse-guaranteed direct fit) and Halir & Flusser's own contribution
(fixing exactly this fragility) both depend on this implementation
faithfully having the failure mode the second paper was written to solve.

**The failure mode, concretely** (`C` is singular, rank 3 -- Day 3's own
finding, `docs/journal/day03.md`): a generalized eigenproblem with
singular `C` produces infinite eigenvalues along `C`'s null-space
directions; under floating-point roundoff on ill-conditioned data, the
FINITE eigenvectors that remain can have (a) NONE satisfying the actual
ellipse constraint `a^T*C*a > 0` (no valid candidate), or (b) MORE THAN
ONE satisfying it (genuine ambiguity -- no principled way to pick between
them without additional information the algebra itself doesn't provide).
Both were observed empirically in Day 3's study, not assumed -- see that
day's journal for the specific regimes each occurs in.

Selection rule: the ACTUAL constraint `a^T*C*a > 0` (eq. 6/9), NOT
"pick the eigenvector with the negative eigenvalue" -- a convention-
dependent folklore rule Day 3 found and fixed (wrong for this specific
sign convention of `C`, making this method look far more broken than it
actually is before that fix). Using a wrong-but-common selection rule
would itself be a subtle form of NOT implementing this method faithfully.

Post-fit phase recovery is shared (`methods/_ellipse.py`) -- see that
module's docstring for why sharing this specific step does not compromise
Day 21's independence check.

Pipeline position: `methods/__init__.py`'s registry entry `"fitzgibbon"`.
"""

from __future__ import annotations

import numpy as np
import scipy.linalg

from hoqi_bench._types import FloatArray
from hoqi_bench.methods._ellipse import apply_heydemann_correction, conic_to_heydemann_params
from hoqi_bench.methods.base import FitResult, failed_result

NAME = "fitzgibbon"


def _design_matrix(intensity_i: FloatArray, intensity_q: FloatArray) -> FloatArray:
    """The `Nx6` design matrix `[x^2, xy, y^2, x, y, 1]` (eq. 8), shared by
    `_fit_ellipse_conic` and `_classify_failure` so the two don't drift
    apart on how they build it."""
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


def _fit_ellipse_conic(
    intensity_i: FloatArray, intensity_q: FloatArray
) -> tuple[float, float, float, float, float, float] | None:
    """The single 6x6 generalized eigenvalue solve, unreduced -- see module
    docstring for why this is deliberately NOT the block-decomposed form.

    Returns `None` on any of Fitzgibbon's own real failure modes: the
    solve itself raising, no eigenvector satisfying `a^T*C*a > 0`, or MORE
    THAN ONE satisfying it (genuine ambiguity -- the caller distinguishes
    these into specific reason codes, per
    `docs/WEEK3_METHOD_CONTRACT.md` sec2).
    """
    design = _design_matrix(intensity_i, intensity_q)
    scatter = design.T @ design

    constraint = np.zeros((6, 6))
    constraint[0, 2] = constraint[2, 0] = 2
    constraint[1, 1] = -1

    try:
        eigvals, eigvecs = scipy.linalg.eig(scatter, constraint)
    except (np.linalg.LinAlgError, ValueError):
        return None

    real_eigvecs = eigvecs.real
    a_t_c_a = np.array(
        [real_eigvecs[:, i] @ constraint @ real_eigvecs[:, i] for i in range(6)]
    )
    finite = np.all(np.isfinite(real_eigvecs), axis=0) & np.isfinite(eigvals.real)
    valid = finite & (a_t_c_a > 1e-9)

    n_candidates = int(np.sum(valid))
    if n_candidates != 1:
        return None

    a, b, c, d, e, f = real_eigvecs[:, valid][:, 0]
    return float(a), float(b), float(c), float(d), float(e), float(f)


def _classify_failure(intensity_i: FloatArray, intensity_q: FloatArray) -> str:
    """Re-derives WHICH of Fitzgibbon's two known failure modes actually
    occurred, for a specific reason code (contract sec2) -- `_fit_ellipse_conic`
    itself only returns None/coefficients, since distinguishing "no
    candidate" from "ambiguous" needs the same computation redone; kept
    separate rather than having the hot path always compute a reason
    string it discards on success."""
    design = _design_matrix(intensity_i, intensity_q)
    scatter = design.T @ design
    constraint = np.zeros((6, 6))
    constraint[0, 2] = constraint[2, 0] = 2
    constraint[1, 1] = -1
    try:
        eigvals, eigvecs = scipy.linalg.eig(scatter, constraint)
    except (np.linalg.LinAlgError, ValueError):
        return "generalized_eigenvalue_solve_failed"
    real_eigvecs = eigvecs.real
    a_t_c_a = np.array(
        [real_eigvecs[:, i] @ constraint @ real_eigvecs[:, i] for i in range(6)]
    )
    finite = np.all(np.isfinite(real_eigvecs), axis=0) & np.isfinite(eigvals.real)
    valid = finite & (a_t_c_a > 1e-9)
    n_candidates = int(np.sum(valid))
    if n_candidates == 0:
        return "no_valid_ellipse_candidate"
    return "ambiguous_ellipse_candidates"


def fit(intensity_i: FloatArray, intensity_q: FloatArray) -> FitResult:
    """Fits the ellipse conic via Fitzgibbon's unreduced formulation,
    converts to `(dc_i, dc_q, g, eps)` via the shared
    `conic_to_heydemann_params`, applies the shared correction, and
    recovers phase via `atan2`.

    Failure modes (`docs/WEEK3_METHOD_CONTRACT.md` sec2):
    - `"generalized_eigenvalue_solve_failed"`, `"no_valid_ellipse_candidate"`,
      `"ambiguous_ellipse_candidates"`: Fitzgibbon's own known fragility
      (module docstring) -- DELIBERATELY not patched or relaxed.
    - `"singular_conic_center"`, `"invalid_quadrature_estimate"`: the
      shared post-fit conversion's own failure modes, same as Halir &
      Flusser's (Day 18) -- these can occur even when a valid ellipse
      CANDIDATE was found, if that candidate is itself geometrically
      degenerate.
    """
    n = intensity_i.shape[0]

    conic = _fit_ellipse_conic(intensity_i, intensity_q)
    if conic is None:
        return failed_result(n, _classify_failure(intensity_i, intensity_q))
    a, b, c, d, e, f = conic

    try:
        dc_i, dc_q, g, eps = conic_to_heydemann_params(a, b, c, d, e, f)
    except np.linalg.LinAlgError:
        return failed_result(n, "singular_conic_center")

    if not (np.isfinite(dc_i) and np.isfinite(dc_q) and np.isfinite(g) and np.isfinite(eps)):
        return failed_result(n, "invalid_quadrature_estimate")
    if g <= 0.0:
        return failed_result(n, "invalid_quadrature_estimate")

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
    )
