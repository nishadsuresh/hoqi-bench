"""
Method 3 -- the Heydemann (1981) correction, applied via `docs/derivations/heydemann.md`
Sections 3-7's closed-form transform.

**Structural note, stated here per `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` §1**:
`forward_model`'s distortion IS `I=I0+A*cos(phi)`, `Q=Q0+A*g*sin(phi+eps)` --
exactly the model this correction is derived to invert. On the three
classic axes (`amplitude_ratio`, `quadrature_error_rad`, `dc_offset`),
near-ceiling accuracy from this method is GUARANTEED by construction, not
a finding -- see that document's binding Day 28 reporting rule.

**A real design decision, not a port of the "obvious" prior implementation**:
`quadrature-interferometer-sim`'s own `fit_ellipse_and_normalize` estimates
`(dc_i, dc_q, g, eps)` via `fit_ellipse_conic`, which its own docstring
names explicitly as "Halir & Flusser (1998) direct least-squares ellipse
fit." Porting that pipeline verbatim as "Heydemann" here would make this
method and Day 18's Halir & Flusser share the SAME generalized-eigenvalue
solve under the hood, differing only in output formatting -- violating Day
15's "no shared code below fit()" rule and making Day 21's cross-validation
gate evidentially empty (the two wouldn't be independently agreeing, they'd
be the same computation twice).

Implemented instead via **second-order statistics (moments)** -- a
genuinely different, and historically more appropriate, estimation
principle (Heydemann 1981 predates the generalized-eigenvalue ellipse-
fitting literature, Fitzgibbon 1999 / Halir & Flusser 1998, by ~17 years,
so the original method plausibly used simpler statistical estimators, not
a technique that didn't exist yet). Derivation, verified numerically
before being written here (not guessed): with `I' = I - I0 = A*cos(phi)`,
`Q' = Q - Q0 = A*g*sin(phi+eps)`, averaging over enough of a cycle that
`<cos^2(phi)> ~ <sin^2(phi+eps)> ~ 1/2` and `<cos(phi)*sin(phi)> ~ 0`:

```
Var(I')      = A^2/2
Var(Q')      = A^2*g^2/2
Cov(I', Q')  = A^2*g*sin(eps)/2
```

so `g = sqrt(Var(Q')/Var(I'))`, `sin(eps) = Cov(I',Q') / (Var(I')*g)`,
`cos(eps) = +sqrt(1-sin(eps)^2)` (positive root -- valid for
`|eps| < pi/2`, the same physically-motivated branch choice
`quadrature-interferometer-sim`'s own `conic_to_heydemann_params` uses, a
shared PHYSICAL FACT about this regime, not shared code). `I0`, `Q0`
estimated directly as `mean(I)`, `mean(Q)`.

**A real failure mode this estimator has that the eigenvalue-based fits do
not (to the same degree)**: the moment formulas above assume the sampled
phase range is wide enough for the `<cos^2> ~ 1/2` approximation to hold.
Verified numerically (not assumed): at `arc_fraction=1.0` this is exact
(`g` recovered to machine precision on synthetic, noiseless data); at
`arc_fraction <= 0.75` the estimate becomes badly biased (`g` off by 10x
or more at small arc) WITHOUT raising any exception -- silent garbage, not
a crash. Guarded via a self-consistency check (see `fit()`), not a naive
`arc_fraction` threshold (this function never receives `arc_fraction` --
only `(I, Q)` -- so the check has to be a property of the data itself, not
an assumed cause).

**A second, smaller, genuinely interesting residual bias, found while
writing this method's own test suite** (not a bug in either component
involved): at `amplitude_ratio=1.3` (a real, preregistered value), Q dips
negative for ~17% of a 60-sample record even before any noise (the same
deterministic effect `simulate.py`/`noise.py` document from the P1
investigation). `noise.poisson_noise`'s physically-motivated negative-
intensity clamp then forces exactly those samples to `0.0`. Because this
estimator reads `Var(I')`/`Var(Q')` directly off the sample values,
clamping ~17% of samples measurably shifts the variance ratio -- a real,
deterministic (not seed-dependent) ~4% bias in the recovered `g` at this
specific condition, confirmed by comparing against the pre-Poisson-noise
signal directly (1.6% from `build_arc_ramp`'s `endpoint=True` convention
alone, the remaining ~2.6% specifically from the clamp). `atan2`-based
methods (raw atan2, Kasa) are far less sensitive to this, since they
compute an angle from whatever value they're given rather than an
aggregate statistic over the whole record. Not fixed here -- neither the
clamp (P1, `noise.py`) nor this estimator is wrong; this is a real
second-order interaction between two independently-correct design
decisions, and `tests/test_heydemann.py` tests the ACTUAL achievable
accuracy at this condition rather than an idealized one.

Pipeline position: `methods/__init__.py`'s registry entry `"heydemann"`.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods._ellipse import apply_heydemann_correction
from hoqi_bench.methods.base import FitResult, failed_result

NAME = "heydemann"

# Calibrated 2026-07-27 by direct numerical probing (not guessed), against
# the real campaign's own parameter ranges: legitimate full-arc-coverage
# conditions at the top of the swept noise range (noise_std up to 0.1*A)
# reach a post-correction radius relative std of up to ~0.12 across 5
# seeds; genuinely degenerate conditions (arc_fraction <= 0.5 combined with
# realistic noise) start at ~0.33. 0.15 sits with real margin on both
# sides (0.12 vs 0.15 vs 0.33) -- see docs/journal/day17.md for the full
# calibration data.
_RADIUS_CONSISTENCY_THRESHOLD = 0.15


def fit(intensity_i: FloatArray, intensity_q: FloatArray) -> FitResult:
    """Estimates `(I0, Q0, g, eps)` via second-order statistics (see
    module docstring), applies Heydemann's closed-form correction, and
    recovers phase via `atan2` on the corrected signal.

    Failure modes (`docs/WEEK3_METHOD_CONTRACT.md` §2 -- NaN + specific
    reason + `failed=True`, never a crash or silent garbage):
    - `"zero_variance_degenerate"`: `Var(I')` (or the resulting `g`) is
      exactly zero -- no oscillation to estimate anything from (e.g. an
      all-identical-points input).
    - `"invalid_quadrature_estimate"`: `|sin(eps)|` computed `> 1` --
      numerically inconsistent with any real `eps`, from extreme noise or
      too few samples.
    - `"unstable_ellipse_estimate"`: the corrected signal's radius is not
      reasonably constant across samples (relative std over
      `_RADIUS_CONSISTENCY_THRESHOLD`) -- catches the SILENT-garbage
      failure mode the module docstring describes (small `arc_fraction`),
      which does not raise on its own and would otherwise pass through as
      a confidently-wrong phase estimate.
    """
    n = intensity_i.shape[0]

    # ---- 1. DC offsets, directly as channel means ----
    dc_i = float(np.mean(intensity_i))
    dc_q = float(np.mean(intensity_q))
    i_centered = intensity_i - dc_i
    q_centered = intensity_q - dc_q

    # ---- 2. Second-order statistics -> (g, eps), per module docstring ----
    var_i = float(np.mean(i_centered**2))
    var_q = float(np.mean(q_centered**2))
    cov_iq = float(np.mean(i_centered * q_centered))

    if var_i <= 0.0:
        return failed_result(n, "zero_variance_degenerate")

    g = float(np.sqrt(var_q / var_i))
    if g <= 0.0:
        return failed_result(n, "zero_variance_degenerate")

    sin_eps = cov_iq / (var_i * g)
    if abs(sin_eps) > 1.0:
        return failed_result(n, "invalid_quadrature_estimate")
    cos_eps = float(np.sqrt(1.0 - sin_eps**2))
    eps = float(np.arctan2(sin_eps, cos_eps))

    # ---- 3. Apply the closed-form correction (heydemann.md Sections 3-7),
    # via the shared post-fit helper -- see _ellipse.py's module docstring
    # for why this step is legitimate to share across methods ----
    i_c, q_c = apply_heydemann_correction(intensity_i, intensity_q, dc_i, dc_q, g, eps)

    # ---- 4. Self-consistency guard: a valid correction maps the
    # trajectory onto a circle, so its radius should be ~constant --
    # catches the silent-garbage small-arc_fraction failure mode
    # (module docstring) that steps 1-3 alone would not raise on ----
    radius = np.sqrt(i_c**2 + q_c**2)
    mean_radius = float(np.mean(radius))
    if mean_radius <= 0.0:
        return failed_result(n, "zero_variance_degenerate")
    radius_relative_std = float(np.std(radius) / mean_radius)
    if radius_relative_std > _RADIUS_CONSISTENCY_THRESHOLD:
        return failed_result(n, "unstable_ellipse_estimate")

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
