"""
Method 4 -- Halir & Flusser (1998) numerically stable direct least-squares
ellipse fit. The core algebra matches this project's own Day 3 exploration
(`scripts/explore_ellipse_constraints.py`'s `fit_ellipse_halir_flusser`),
promoted into the package proper -- not a port of
`quadrature-interferometer-sim`'s cruder same-named function (see
`_fit_ellipse_conic`'s own docstring for exactly why: the two are
mathematically identical, but the exploration script's version has real
failure-handling the sibling project's does not, and Day 18's task is
specifically to confirm survival of Day 3's degenerate regimes).

Why the block decomposition, not the naive form (`notes/halir_flusser_1998.md`):
Fitzgibbon et al.'s (1999) original direct ellipse-specific fit poses
`min ||Da||^2 s.t. a^T*C*a=1` as a 6x6 generalized eigenvalue problem
(`S*a = lambda*C*a`, `D` the `Nx6` design matrix `[x^2,xy,y^2,x,y,1]`,
`C` all-zero except `C[0,2]=C[2,0]=2, C[1,1]=-1`). `C` is singular, which
forces identifying the one eigenvector with a POSITIVE `4ac-b^2` by
scanning signs -- ambiguous or wrong under floating-point roundoff on
scattered/noisy data (Day 3's own finding,
`scripts/explore_ellipse_constraints.py`). Halir & Flusser split `a` into
a quadratic part `a1=[a,b,c]` and linear part `a2=[d,e,f]`, and `S`/`C`
into matching 3x3 sub-blocks, reducing the eigenproblem to size 3 with no
sign-scanning ambiguity -- the entire point of the paper, per its own
title. Implementing the NAIVE (unstable) form here would defeat the reason
this method exists in the benchmark at all.

**A real, stated limitation, not glossed over** (`notes/halir_flusser_1998.md`'s
own conclusion): minimizing ALGEBRAIC distance (not true geometric/
orthogonal distance) means fitted ellipses are systematically biased
toward being SMALLER than the true ellipse, and the paper states this
"cannot be simply corrected." Relevant to interpreting Day 21's
method-agreement check: don't expect bit-identical agreement with a
geometric-distance method even in the well-conditioned regime, a small
systematic bias is expected and is not itself a bug.

**Post-fit phase recovery is SHARED, deliberately** (`methods/_ellipse.py`):
converting a validated ellipse into a phase value is mechanical, not part
of this paper's own contribution (it says nothing about interferometry or
phase recovery at all) -- see that module's docstring for why sharing
this specific step does not compromise Day 21's independence check, unlike
sharing the actual conic-fitting algorithm would.

Pipeline position: `methods/__init__.py`'s registry entry
`"halir_flusser"`.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods._ellipse import apply_heydemann_correction, conic_to_heydemann_params
from hoqi_bench.methods.base import FitResult, failed_result

NAME = "halir_flusser"


def _fit_ellipse_conic(
    intensity_i: FloatArray, intensity_q: FloatArray
) -> tuple[float, float, float, float, float, float] | None:
    """The block-decomposition direct least-squares ellipse fit.

    Design decision -- matches `scripts/explore_ellipse_constraints.py`'s
    `fit_ellipse_halir_flusser`, NOT `quadrature-interferometer-sim`'s
    cruder `fit_ellipse_conic`: the two are mathematically identical
    (`inv(C1) @ M_reduced`, computed via an explicit inverse here vs. a
    hand-derived row-shuffle shortcut there -- verified algebraically
    equal), but the exploration script's version has real, necessary
    failure handling the sibling project's does not: (a) an explicit
    `try/except` around the `S3` inverse (singular on sufficiently
    degenerate input); (b) an explicit `(cond.real > eps) & (|cond.imag| <
    eps)` check rather than a bare `cond > 0`. VERIFIED DIRECTLY (not
    assumed) that the bare comparison is a real, silent hazard: numpy
    compares a complex array to `0` using ONLY the real part, with no
    warning at any Python warning level -- `np.array([1+2j]) > 0`
    succeeds silently. Since Day 18's task is specifically to confirm this
    implementation survives Day 3's degenerate regimes (not just to port
    the sibling project's version verbatim), this project's OWN
    already-more-careful prior work is the right reference.

    Returns `None` (rather than raising) on either failure: `S3` singular,
    or no eigenvector satisfies the ellipse-specific condition
    `4ac-b^2 > 0` within tolerance -- both real, possible outcomes on
    sufficiently degenerate input (Day 3's own finding), left to the
    caller to convert into a specific `failed_result` reason.
    """
    x, y = intensity_i, intensity_q
    d1 = np.column_stack([x**2, x * y, y**2])
    d2 = np.column_stack([x, y, np.ones_like(x)])
    s1, s2, s3 = d1.T @ d1, d1.T @ d2, d2.T @ d2

    try:
        s3_inv = np.linalg.inv(s3)
    except np.linalg.LinAlgError:
        return None

    t_matrix = -s3_inv @ s2.T
    m_reduced = s1 + s2 @ t_matrix

    c1 = np.array([[0, 0, 2], [0, -1, 0], [2, 0, 0]], dtype=float)
    m_final = np.linalg.inv(c1) @ m_reduced

    eigvals, eigvecs = np.linalg.eig(m_final)
    cond = 4 * eigvecs[0, :] * eigvecs[2, :] - eigvecs[1, :] ** 2
    valid = (cond.real > 1e-9) & (np.abs(cond.imag) < 1e-9)

    if not np.any(valid):
        return None

    a1 = eigvecs[:, valid][:, 0].real
    if not np.all(np.isfinite(a1)):
        return None

    a2 = t_matrix @ a1
    a, b, c, d, e, f = np.concatenate([a1, a2])
    return float(a), float(b), float(c), float(d), float(e), float(f)


def fit(intensity_i: FloatArray, intensity_q: FloatArray) -> FitResult:
    """Fits the ellipse conic, converts it to `(dc_i, dc_q, g, eps)` via
    the shared `conic_to_heydemann_params`, applies the shared correction,
    and recovers phase via `atan2`.

    Failure modes (`docs/WEEK3_METHOD_CONTRACT.md` §2):
    - `"no_valid_ellipse_eigenvector"`: `_fit_ellipse_conic` found no
      eigenvector satisfying the ellipse-specific constraint -- the
      degenerate case that motivated the block decomposition in the first
      place can still occur on sufficiently bad input.
    - `"singular_conic_center"`: `conic_to_heydemann_params`'s center-solve
      is singular (a degenerate conic with no well-defined center).
    - `"invalid_quadrature_estimate"`: the resulting `g`/`eps` are
      non-finite (`conic_to_heydemann_params` can produce NaN rather than
      raising, if the fitted conic is inconsistent with this project's
      `g>0, cos(eps)>0` structural assumption -- see that function's own
      docstring).
    """
    n = intensity_i.shape[0]

    conic = _fit_ellipse_conic(intensity_i, intensity_q)
    if conic is None:
        return failed_result(n, "no_valid_ellipse_eigenvector")
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
