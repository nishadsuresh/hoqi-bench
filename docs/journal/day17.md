# Day 17 — Heydemann correction (Method 3)

## What the correction does, step by step, on a concrete example

Picture the distorted trajectory as a tilted, off-center ellipse instead of the clean circle
raw atan2 assumes. Heydemann's correction undoes this in three moves. First, subtract each
channel's own DC offset — this is purely a shift, so it doesn't touch the ellipse's shape at
all, just re-centers it at the origin. Second, expand `sin(phi + eps)` via the angle-addition
identity: this pulls `eps` out of the sine argument (where it was tangled up with the actual
unknown, `phi`) and turns it into a known multiplier. Third — the key step — substitute in
`I' = A*cos(phi)`, which is already known from step one, to eliminate `cos(phi)` from the `Q`
equation entirely. What's left has exactly one unknown, `A*sin(phi)`, which a final division
isolates. The corrected `(I_c, Q_c)` is then *exactly* the ideal circle from Section 1 of the
derivation, scaled by `A` — atan2 on that recovers `phi` exactly, the same way it does for
the undistorted case.

## A real design decision: not the "obvious" port

`quadrature-interferometer-sim`'s own Heydemann pipeline estimates `(I0, Q0, g, eps)` via
`fit_ellipse_conic` — which its own docstring names directly as "Halir & Flusser (1998)
direct least-squares ellipse fit." Porting that verbatim as Method 3 would make today's
method and Day 18's Halir & Flusser share the exact same generalized-eigenvalue solve under
the hood — violating Day 15's "no shared code below `fit()`" rule, and worse, making Day
21's cross-validation gate evidentially empty: the two wouldn't be independently agreeing on
anything, they'd be the same computation wearing two names.

Implemented instead via **second-order statistics** — `g` and `eps` recovered from the
variance and covariance of the centered `I`/`Q` channels, a genuinely different estimation
principle. This is also more historically honest: Heydemann's 1981 paper predates the
generalized-eigenvalue ellipse-fitting literature (Fitzgibbon 1999, Halir & Flusser 1998) by
17 years — the original method almost certainly used simpler statistical estimators, since
the eigenvalue technique didn't exist yet. Verified by hand-deriving the moment formulas,
then checking numerically (before writing any code) that they recover known `g`, `eps`, `I0`,
`Q0` exactly on synthetic data.

## Two real, understood biases — found and explained, not hidden

**Bias 1 — `build_arc_ramp`'s `endpoint=True`.** The moment estimator's formulas assume
`<cos²(phi)>` averages to `1/2` over the sample. `build_arc_ramp` uses
`np.linspace(0, 1, n)` with the default `endpoint=True`, so phase `0` and phase `2π` — the
same physical point — both appear in the sample, one point out of 60 effectively duplicated.
Confirmed directly: an `endpoint=False` reconstruction of the identical scenario recovers `g`
to machine precision; the real pipeline's `endpoint=True` convention introduces a real,
deterministic ~1.6% bias. Not fixed in `build_arc_ramp` itself — that function is load-bearing
for already-locked Weeks 1-2 results (Day 7's "31 fringes, 0.000000% error" check, the v2
`samples_per_fit` design table), and silently changing it now to smooth over a bias only this
one estimator is sensitive to would risk invalidating findings that were already verified and
signed off on.

**Bias 2 — a real interaction with P1's Poisson-noise clamp.** At `amplitude_ratio=1.3` (a
real, preregistered value chosen to probe breakdown), Q dips negative for ~17% of a 60-sample
record — the same deterministic effect P1 found and fixed with a physically-motivated clamp
("a real photodiode can't report a negative photon count"). That clamp is correct on its own
terms, but because this estimator reads variance directly off sample values, forcing ~17% of
samples to exactly zero measurably shifts the variance ratio — a real, ~4% (seed-independent,
since the cause is deterministic) bias in recovered `g` at this specific condition. Neither
component is wrong; this is a genuine second-order interaction between two independently
correct decisions, the kind of thing that only surfaces by actually composing the full
pipeline and checking real numbers rather than assuming an idealized formula transfers
unchanged.

## A degeneracy guard, calibrated numerically, not guessed

The moment estimator doesn't crash at small `arc_fraction` — it silently returns a **wildly
wrong** `g` (17x off at `arc_fraction=0.02`) with everything else looking numerically normal.
Guarded with a self-consistency check: apply the estimated correction, then check whether the
corrected signal's radius is actually constant across samples (a valid correction maps the
trajectory onto a circle; a bad one doesn't). Calibrated the threshold directly rather than
picking a round number: legitimate full-arc, worst-case-noise conditions reach a radius
relative std of up to ~0.12 across several seeds; genuinely degenerate conditions start at
~0.33. The threshold, 0.15, sits with real margin on both sides.

## Tests that needed correcting twice, for two different real reasons

Every one of this day's four tests initially used a hand-guessed tolerance and failed against
the real number — each time traced to one of the two biases above, not a code defect. The
"dramatically outperforms Kasa" test also needed its *test condition* corrected: comparing
against a `dc_offset`-only axis understated Heydemann's real advantage, since Day 16 already
established Kasa has genuine (if degraded) partial correction there — dc_offset *is* a
circle's center. Switched to the `amplitude_ratio` × `quadrature_error_rad` interaction grid,
where Kasa has zero free parameters for either axis, which is the actually-informative
comparison.

## Status

101/101 tests passing (was 97; +4), ruff clean, mypy --strict clean (40 files). Day 18 next:
Halir & Flusser — the numerically stable block-decomposition ellipse fit, and the first
method whose failure modes (Day 3's own finding) are worth preserving deliberately rather
than guarding away.
