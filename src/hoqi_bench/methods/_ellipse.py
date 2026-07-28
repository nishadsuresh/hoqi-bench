"""
Shared post-fit machinery for every ellipse-based method (Days 17-20):
converting a fitted ellipse into a recovered phase.

Why this is legitimate to share, per Day 15's own design decision
(`docs/WEEK3-4_PLAN.md` Day 15 notes): what's benchmarked for independence
at Day 21 is the numerical PATH from raw (I, Q) to a fitted ellipse --
Heydemann's second-order-statistics estimator, Halir & Flusser's
block-decomposition eigenproblem, Fitzgibbon's constrained eigenproblem,
Taubin's bias-corrected algebraic fit, and Köning's iterative EIV solve are
all genuinely different there, and that is where each method's own
`fit()` keeps its own, non-shared code. What happens AFTER a fit --
turning validated ellipse parameters into a phase value -- is mechanical,
not part of any paper's own contribution (Halir & Flusser's paper, e.g.,
does not address phase recovery or interferometry at all,
`notes/halir_flusser_1998.md`), and sharing it here is no different from
every method sharing `numpy` or this project's own `metrics.py`.

`conic_to_heydemann_params`: ported from `quadrature-interferometer-sim`'s
identically-named function (`src/analysis.py`) -- a closed-form,
BRANCH-FREE conversion from a general conic's 6 coefficients to this
project's `(dc_i, dc_q, g, eps)` parameterization, exploiting a known
structural fact about THIS project's forward model (I is always the
unscaled `cos(phi)` reference channel, so `g > 0` and
`cos(quadrature_error_rad) > 0` are the only physically consistent sign
choices -- see that function's own docstring, ported verbatim below, for
the full derivation). This is a shared PHYSICAL FACT about the regime
every method here operates in, not shared numerical fitting machinery.

`apply_heydemann_correction`: the Section 7 closed-form transform from
`docs/derivations/heydemann.md` -- given ANY correctly-estimated
`(dc_i, dc_q, g, eps)`, regardless of which method produced them, maps
`(I, Q)` back onto the ideal circle. Factored out here so Day 17's
Heydemann (which estimates these params via moments) and this ellipse
module's conic-fitting callers (which estimate them via a conic fit) both
call the identical, once-verified correction step rather than each
reimplementing it.

Pipeline position: imported by `heydemann.py` and (from Day 18 on) every
conic-fitting method.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray


def apply_heydemann_correction(
    intensity_i: FloatArray, intensity_q: FloatArray, dc_i: float, dc_q: float, g: float, eps: float
) -> tuple[FloatArray, FloatArray]:
    """`docs/derivations/heydemann.md` Section 7: `I_c = I - dc_i`,
    `Q_c = (Q - dc_q - g*sin(eps)*I_c) / (g*cos(eps))`. Requires `g != 0`
    and `cos(eps) != 0` (Section 8) -- callers are responsible for
    validating their own estimated params before calling this (this
    function does not itself guard against those, since a caller's
    specific failure-reason code should reflect ITS OWN estimation
    method's failure mode, not a generic one raised here)."""
    i_c = intensity_i - dc_i
    q_c = (intensity_q - dc_q - g * np.sin(eps) * i_c) / (g * np.cos(eps))
    return i_c, q_c


def conic_to_heydemann_params(
    A: float, B: float, C: float, D: float, E: float, F: float
) -> tuple[float, float, float, float]:
    """Converts a general ellipse conic `A*x^2+B*x*y+C*y^2+D*x+E*y+F=0`
    into `(dc_i, dc_q, g, eps)` -- ported from
    `quadrature-interferometer-sim`'s `conic_to_heydemann_params`
    (`src/analysis.py`), itself derived and validated in that earlier,
    separate project (see that project's log for the derivation history,
    including a caught bug where an early draft silently assumed unit
    amplitude scale).

    Unlike a generic conic-to-ellipse-axes conversion (center, semi-major,
    semi-minor, rotation via eigendecomposition), which has an inherent
    +/-90-degree branch/sign ambiguity in assigning major vs. minor axis,
    this conversion is closed-form and branch-free: it exploits that this
    project's forward distortion model always has `I` as the unscaled
    `cos(phi)` reference channel and `Q` as `g*sin(phi+eps)`, which fixes
    `g > 0` and `cos(eps) > 0` (valid since `|eps| < pi/2` for any
    physically realistic quadrature error) as the correct sign choices --
    there is no other solution consistent with the forward model, so no
    branch to get wrong.

    Failure mode: raises `numpy.linalg.LinAlgError` if the 2x2 center-solve
    system is singular (a degenerate conic with no well-defined center) --
    callers must catch this and convert it to a `failed_result`, per
    `docs/WEEK3_METHOD_CONTRACT.md` sec2 (not caught here, so each caller's
    reason code can reflect its own context).

    Second failure mode, measured 2026-07-27 (Week 3 review) and
    deliberately NOT guarded: a NEAR-singular center-solve does not raise,
    and can return a finite but physically absurd center that passes every
    caller's `np.isfinite` check. Confirmed directly --
    `conic_to_heydemann_params(1e-18, 0, 1e-18, 1, 1, 1)` returns a center
    of `-5e17` with `all_finite=True`, and every caller would report
    `failed=False` on it.

    Left unguarded because it is unreachable from the campaign, which was
    checked rather than assumed: across all 359 conditions x 3 seeds, every
    single gross-error fit from all four conic-fitting callers recovered a
    center within 0.16 of the data's own span (median 0.03) -- these are
    plausible fits that are simply wrong at small `arc_fraction`, which is a
    real result, not this pathology. Adding a plausibility bound would
    therefore change no campaign number while adding a threshold with
    nothing to calibrate it against, which `docs/DOCUMENTATION_STANDARD.md`
    explicitly rules out ("don't guard against calls this codebase never
    makes"). Recorded here so a future config exploring more extreme
    geometry knows the path exists.
    """
    x0, y0 = np.linalg.solve(np.array([[2 * A, B], [B, 2 * C]]), np.array([-D, -E]))

    # A degenerate fitted conic (module docstring below) can make f0, or
    # later c_n/g, exactly zero -- both "invalid" (0/0, sqrt-of-negative)
    # and "divide" (x/0 -> inf) numpy warning categories are possible
    # from this point on, and every caller checks np.isfinite() afterward
    # and converts the resulting NaN/inf into a proper failed_result
    # (docs/WEEK3_METHOD_CONTRACT.md sec2) -- an EXPECTED, handled
    # outcome, silenced deliberately rather than left as an unexplained
    # RuntimeWarning (found via scripts/robustness_matrix.py's
    # all_identical_points cell, which legitimately hits this path).
    with np.errstate(invalid="ignore", divide="ignore"):
        f0 = A * x0**2 + B * x0 * y0 + C * y0**2 + D * x0 + E * y0 + F
        a_n, b_n, c_n = A / (-f0), B / (-f0), C / (-f0)

        g = float(np.sqrt(a_n / c_n))
        sin_eps = -(b_n / c_n) / (2 * g)
        cos_eps = float(np.sqrt(1.0 - sin_eps**2))
    eps = float(np.arctan2(sin_eps, cos_eps))

    return float(x0), float(y0), g, eps
