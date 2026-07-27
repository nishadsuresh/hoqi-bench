"""
Method 6 -- Taubin (1991) bias-corrected algebraic circle fit.

Core idea (`notes/taubin_1991.md`, `docs/WEEK3_METHOD_CONTRACT.md` sec3.3):
Kasa's fit (Day 16) minimizes unweighted ALGEBRAIC residual
`|I^2+Q^2-2aI-2bQ-c|`, which is systematically biased for real (noisy,
finite-sample) data -- points scattered outward from the true circle
contribute disproportionately, pulling the fit toward a smaller circle.
Taubin corrects this by normalizing the residual by an APPROXIMATION to
the true geometric (orthogonal) distance -- the gradient norm of the
implicit circle equation `F(x,y)=A(x^2+y^2)+Bx+Cy+D`, `|grad F|^2 ~=
4A^2(x^2+y^2)` in expectation over the data -- turning the fit into a
generalized eigenvalue problem `M*a = eta*N*a` (`M` the same scatter
matrix Kasa's normal equations imply, `N` the gradient-norm-approximation
constraint matrix) instead of Kasa's plain linear least squares.

**A real numerical subtlety, verified before trusting it, not assumed**:
`N` is singular by construction (constant terms have no gradient
contribution), which makes the generalized eigenproblem have a spurious
near-zero eigenvalue as a numerical artifact of the SAME kind Fitzgibbon's
singular `C` produces (`fitzgibbon.py`'s own module docstring). Verified
directly: for noiseless data exactly on a circle, the CORRECT solution's
eigenvalue is exactly 0 (Taubin's residual, by construction, is exactly
zero for a perfect algebraic fit), so the selection rule is the smallest
`|eigenvalue|` among the REAL candidates -- NOT "smallest strictly
positive, excluding near-zero," which was tried first and silently
selected a wrong eigenvector (recovered center exactly right, radius
negative-under-the-square-root -- caught immediately by checking against
a known synthetic circle before writing any implementation code, not
discovered later).

**Why this is a CIRCLE fit, not an ellipse fit, like Kasa** (unlike
Heydemann/Halir & Flusser/Fitzgibbon, Days 17-19): `docs/WEEK3_METHOD_CONTRACT.md`
sec3.3 frames the Kasa<->Taubin relationship as "both solve a similar
linear system" -- Taubin's bias correction operates on the SAME
3-parameter circle model Kasa fits, not the 5-parameter general ellipse
the other three methods target. Per
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`, this means Taubin, like Kasa,
has no free parameter for `amplitude_ratio`/`quadrature_error_rad` and
should track raw atan2's error on those axes while correcting `dc_offset`.

**A prediction tested and narrowed, per `docs/WEEK3_METHOD_CONTRACT.md`
sec3.3's 2026-07-27 deviation note**: the classic literature's "Taubin
reduces bias relative to Kasa" claim is specifically about RADIUS
estimation, and verified true here (matched estimators, 200 seeds,
`axis:noise_std=0.1`: Taubin's radius bias `-0.0095` vs. Kasa's `+0.0535`
-- ~5.6x smaller, confirming this implementation is correct). It does
NOT transfer to phase-recovery RMSE: `atan2`-based phase recovery depends
only on the fitted CENTER, never the radius, and center bias shows no
such improvement (if anything, marginally worse for Taubin at this
condition). Tested directly in `tests/test_taubin.py` as two separate,
now-correctly-scoped claims, not one.

Pipeline position: `methods/__init__.py`'s registry entry `"taubin"`.
"""

from __future__ import annotations

import numpy as np
import scipy.linalg

from hoqi_bench._types import FloatArray
from hoqi_bench.methods.base import FitResult, failed_result

NAME = "taubin"


def _fit_circle_taubin(
    intensity_i: FloatArray, intensity_q: FloatArray
) -> tuple[float, float, float] | None:
    """The bias-corrected circle fit -- see module docstring for the
    selection-rule subtlety this was verified against before being
    trusted. Returns `(center_i, center_q, radius)`, or `None` on a real
    failure: no real eigenvalue candidate, the selected candidate's
    leading coefficient is zero (a degenerate line-like fit, not a
    circle), or the resulting radius-squared is negative (also
    degenerate). `radius` is returned even though `fit()` doesn't need it
    for phase recovery -- it's this method's actual point of comparison
    against Kasa (module docstring's deviation note), so callers checking
    THAT claim need it directly rather than recomputing the fit."""
    mean_i, mean_q = float(np.mean(intensity_i)), float(np.mean(intensity_q))
    u, v = intensity_i - mean_i, intensity_q - mean_q
    z = u**2 + v**2

    mz = float(np.mean(z))
    m_uu, m_vv, m_uv = float(np.mean(u**2)), float(np.mean(v**2)), float(np.mean(u * v))
    m_uz, m_vz = float(np.mean(u * z)), float(np.mean(v * z))
    m_zz = float(np.mean(z**2))

    scatter = np.array(
        [
            [m_zz, m_uz, m_vz, mz],
            [m_uz, m_uu, m_uv, 0.0],
            [m_vz, m_uv, m_vv, 0.0],
            [mz, 0.0, 0.0, 1.0],
        ]
    )
    constraint = np.array(
        [
            [4 * mz, 0.0, 0.0, 2 * mz],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [2 * mz, 0.0, 0.0, 0.0],
        ]
    )

    try:
        eigvals, eigvecs = scipy.linalg.eig(scatter, constraint)
    except (np.linalg.LinAlgError, ValueError):
        return None

    real_mask = np.abs(eigvals.imag) < 1e-9
    if not np.any(real_mask):
        return None
    real_vals = eigvals.real[real_mask]
    real_vecs = eigvecs[:, real_mask].real

    idx = int(np.argmin(np.abs(real_vals)))
    a, b, c, d = real_vecs[:, idx]
    if a == 0.0:
        return None

    center_u, center_v = -b / (2 * a), -c / (2 * a)
    radius_squared = (b**2 + c**2 - 4 * a * d) / (4 * a**2)
    if radius_squared < 0.0:
        return None

    return mean_i + center_u, mean_q + center_v, float(np.sqrt(radius_squared))


def fit(intensity_i: FloatArray, intensity_q: FloatArray) -> FitResult:
    """Fits the circle center via Taubin's bias-corrected linear system,
    then recovers phase via `atan2` about that center -- same structure
    as `kasa.fit`, different (bias-corrected) estimation of the center.

    Failure mode: `"degenerate_circle_fit"` when `_fit_circle_taubin`
    finds no valid real solution -- e.g. no real eigenvalue candidate, or
    the selected candidate's leading coefficient is exactly zero.
    """
    n = intensity_i.shape[0]

    result = _fit_circle_taubin(intensity_i, intensity_q)
    if result is None:
        return failed_result(n, "degenerate_circle_fit")
    center_i, center_q, radius = result

    recovered_phase = np.arctan2(intensity_q - center_q, intensity_i - center_i).astype(
        np.float64
    )
    return FitResult(
        recovered_phase=recovered_phase,
        params={"center_i": center_i, "center_q": center_q, "radius": radius},
    )
