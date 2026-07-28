# Structural Advantage Predictions

Written 2026-07-27, before Day 15 -- before any of the 7 methods exist and before any
result exists. Per `docs/WEEK3-4_PLAN.md` Part 0.1: the forward model
(`docs/experimental_design.md` Section 1) is algebraically the SAME model the Heydemann
correction is derived to invert:

```
I(phi) = I0 + A * cos(phi)
Q(phi) = Q0 + A * g * sin(phi + eps)
```

A method whose correction model matches this exactly will win the corresponding axis **by
construction**, not by merit. Reporting that as a finding would be reporting a tautology.
This document exists so that Day 28's analysis can check its own results against a
prediction made in ignorance of them, rather than discovering after the fact which results
were guaranteed and quietly presenting them as evidence of anything.

**Binding rule, referenced from `docs/WEEK3-4_PLAN.md` Day 28**: any Week 4 result matching
a "tautological" prediction below is reported as a construction check, not a finding. Any
result matching a "genuine prediction" below IS a real finding if confirmed -- these are
falsifiable, not guaranteed, and are named here specifically so they cannot later be
presented as more surprising than they are, in either direction. Any result that
CONTRADICTS a genuine prediction is also a real, reportable finding (a theory failing to
hold is informative).

## Three categories, not one

1. **Tautological** -- the method's correction model algebraically IS the injected
   distortion. The method winning is guaranteed by construction. Not a finding.
2. **Genuine theoretical prediction** -- grounded in a real, citable property of the
   method's estimation principle (not the forward model's exact functional form), stated in
   advance and falsifiable. A confirming result IS a finding (it demonstrates the theory
   holds in this specific simulated regime); a contradicting result is also a finding.
3. **Genuinely open** -- no method's assumed model has any structural relationship to the
   axis. This is where the benchmark's real information content lives.

## Per-axis predictions

### `amplitude_ratio`, `quadrature_error_rad`, `dc_offset` -- the three classic Heydemann axes

**Category 1 (tautological).** All four general-conic/ellipse fitters -- **Heydemann**,
**Halir & Flusser**, **Fitzgibbon**, **Taubin** -- solve for the same underlying geometric
object: the tilted, off-center ellipse these three parameters produce. Halir & Flusser and
Fitzgibbon fit the general 5-parameter conic (`notes/halir_flusser_1998.md`); Taubin is a
bias-corrected algebraic ellipse/circle fit (`notes/taubin_1991.md`); Heydemann's
correction is derived directly from this exact `(I0, Q0, g, eps)` parameterization
(`docs/derivations/heydemann.md`). **Köning/Wimmer/Witkovský** also fits an ellipse (via
iterated-Taylor EIV estimation rather than ordinary least squares,
`notes/koning_2014.md`) -- same geometric target, different estimation principle.

**Prediction:** on noiseless or low-noise data, all five of these methods (Heydemann,
Halir & Flusser, Fitzgibbon, Taubin, Köning) should recover displacement to near-ceiling
accuracy across the full swept range of these three axes -- because the forward model's
distortion IS an ellipse, and all five are ellipse fitters. Differences between them on
these axes at low noise are expected to be small and are NOT evidence one method is
generally superior; they are evidence of implementation/conditioning differences on a
problem all five are structurally equipped to solve.

**Kasa** is the one partial exception among the correction-capable methods: it fits only a
*circle* (`notes/kasa_1976.md`), so it corrects `dc_offset` (a circle's center) but has NO
free parameter for `amplitude_ratio` or `quadrature_error_rad` (which distort a circle into
an ellipse, a shape Kasa cannot represent). **Prediction:** Kasa should track raw atan2's
error on `amplitude_ratio`/`quadrature_error_rad` (no structural correction available) while
outperforming it on `dc_offset` alone.

**Raw atan2** has no correction model at all -- it is the floor every method must beat on
all three axes, by construction, per the original build plan's own framing (Day 15).

### `noise_std` (Gaussian) -- Köning's genuine, non-tautological prediction

**Category 2 (genuine theoretical prediction).** Halir & Flusser, Fitzgibbon, Taubin, and
Kasa are all **ordinary least squares** estimators: they minimize algebraic residual
treating the fitted curve as exact and all deviation as noise in one direction. Köning's
method is an **errors-in-variables (EIV)** estimator: it explicitly models measurement
error in BOTH `I` and `Q` (`notes/koning_2014.md`, "Update 2026-07-26" section), which is a
real, textbook-grounded statistical property of EIV vs. OLS estimation, independent of this
project's specific forward model.

**Prediction:** as `noise_std` rises, Köning should show a measurably smaller bias/error
increase than the OLS-based ellipse fitters, with the gap widening at higher noise. This is
NOT guaranteed by the forward model's functional form (unlike the classic-axes prediction
above) -- it is a falsifiable claim about estimator theory. **If it does not hold**, that is
a real, reportable finding (e.g., it could mean this implementation's approximation of the
EIV algorithm family, made without the original 2014 paper's specific tuning, does not
capture the advantage faithfully -- itself worth stating plainly, not hidden).

**Taubin vs. Kasa**, on this same axis, is the internal falsifiable prediction already fixed
in `docs/WEEK3_METHOD_CONTRACT.md` §3.3: Taubin's bias correction should measurably reduce
Kasa's noise-driven bias as `noise_std` rises. Also Category 2 (a real property of the bias
correction, not tautological).

### `arc_fraction` and `samples_per_fit` (N) -- a conditioning prediction, not an accuracy one

**Category 2 (genuine theoretical prediction), and structurally DIFFERENT in kind from every
prediction above.** These two axes control how many points are available and how much of
the ellipse they trace, not which distortion is injected. This is a **numerical
conditioning** question, not a **model-match** question.

A circle fit (Kasa, and Taubin in its circle-fit mode) has 3 free parameters; a general
ellipse fit (Halir & Flusser, Fitzgibbon, Köning) has 5. Fewer free parameters are easier to
constrain from few, closely-spaced points. **Prediction:** at small `arc_fraction` and low
`samples_per_fit`, Kasa/Taubin should degrade more gracefully (fail less often, smaller
error growth) than the 5-parameter ellipse fitters -- even though Kasa/Taubin cannot
correct the classic distortions at all. This produces a genuinely interesting,
non-tautological structure: **the most robust method at low N and small arc is not the most
accurate method once enough of the ellipse is visible** -- these are different methods, and
finding that split is itself informative, not an artifact.

Within the 5-parameter methods specifically, Day 3's own already-established finding
(`docs/WEEK3_METHOD_CONTRACT.md` §3.2, `scripts/explore_ellipse_constraints.py`) already
predicts Fitzgibbon shows elevated failure/error relative to Halir & Flusser specifically in
this ill-conditioned regime -- restated here as it directly extends this axis's prediction,
not a new claim.

### `hysteresis_magnitude`, power-law residual scaling (RQ3), Poisson vs. Gaussian noise
(RQ4)

**Category 3 (genuinely open).** No method among the 7 models path-dependence (hysteresis),
power-law residual scaling, or non-Gaussian (Poisson) noise structure. All 7 assume a
static ellipse plus some implicit noise model at the estimation stage (OLS for six of them;
EIV-Gaussian for Köning -- neither is a Poisson-aware estimator). **No method has a
structural home-field advantage on these axes.** These are the results this benchmark
actually exists to produce -- per the project's own contribution claim
(`notes/contribution_claim.md`), the extension to Lehmann et al. 2025's newer nonlinearity
classes is the genuinely novel half of the work, and it is genuinely novel precisely
because nothing built for the classic axes has an assumed answer here.

The one soft prediction worth naming: methods that already tolerate small deviations from a
perfect ellipse better in general (per the conditioning discussion above, the lower-variance
Kasa/Taubin family, or Köning's EIV robustness) MIGHT also tolerate small
hysteresis/power-law perturbations slightly better as a side effect of general robustness --
but this is explicitly weaker than Category 2 and should be treated as speculative, not
predicted with confidence. Flagged here only so it isn't invented post hoc if it turns out
to be true.

## How this document is used (Day 28 binding rule, restated)

When Day 28's RQ1/RQ2 analysis reports results:
- A result on the classic axes (`amplitude_ratio`, `quadrature_error_rad`, `dc_offset`)
  matching the Category 1 prediction above is captioned as a construction check ("Heydemann,
  Halir & Flusser, Fitzgibbon, Taubin, and Köning all recover near-ceiling accuracy here, as
  structurally guaranteed -- see `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`"), not presented
  as a ranking finding.
- A result on `noise_std`, `arc_fraction`, or `samples_per_fit` is checked against its
  Category 2 prediction and reported as CONFIRMED or CONTRADICTED, either of which is a real
  finding.
- A result on `hysteresis_magnitude`, power-law, or Poisson-vs-Gaussian is reported with no
  structural-prediction caveat needed -- these are the open axes.

## Deviation record

Any later change to a prediction above (e.g., upon discovering a method's actual implementation
differs from the algorithm family described in its `notes/*.md` file) must be recorded here, dated,
with the reason -- matching `docs/PREREGISTRATION.md`'s own discipline.

### D1 -- 2026-07-27 (Day 21): Taubin is a CIRCLE fit, and belongs with Kasa on the classic axes

**What this document says above, and what is wrong with it.** The classic-axes section opens "All
four general-conic/ellipse fitters -- **Heydemann**, **Halir & Flusser**, **Fitzgibbon**,
**Taubin**" and places all four in **Category 1 (tautological)**, predicting near-ceiling accuracy
across the full swept range of `amplitude_ratio`, `quadrature_error_rad` and `dc_offset`, with
Kasa named as "the one partial exception among the correction-capable methods."

`src/hoqi_bench/methods/taubin.py` fits a **3-parameter circle**, not a 5-parameter ellipse -- as
its own module docstring states explicitly ("Why this is a CIRCLE fit, not an ellipse fit, like
Kasa"), following `docs/WEEK3_METHOD_CONTRACT.md` §3.3's framing of the Kasa<->Taubin relationship
as a bias correction on the same linear system. Taubin's bias correction operates on Kasa's model;
it does not add eccentricity or tilt parameters. So Taubin has **no free parameter for
`amplitude_ratio` or `quadrature_error_rad` either**, exactly like Kasa.

**Falsified, not merely noticed.** Day 21's Tier 1a test measures this directly: on noiselessly,
exactly generated ellipse data (`g=1.3`, `eps=0.15`), the four true conic fitters recover phase to
<1e-13 rad, while Taubin recovers it to **0.136 rad RMS** -- indistinguishable from Kasa's 0.136 and
raw atan2's 0.143. Taubin is on the wrong side of the line this document draws.

**Corrected predictions**, replacing the classic-axes text above for Taubin only:

- On `amplitude_ratio` and `quadrature_error_rad`: Taubin is **Category 2, not Category 1**. It
  should track raw atan2 and Kasa, not the conic fitters. A Week 4 result showing Taubin near
  ceiling on these two axes would be a genuine anomaly worth investigating, not a construction
  check.
- On `dc_offset`: unchanged in substance -- Taubin corrects a circle's center, so it should
  outperform raw atan2 here, alongside Kasa.
- The `noise_std` and `arc_fraction`/`samples_per_fit` sections are unaffected: both already treat
  Taubin correctly as a member of the Kasa/circle-fit family.

**Why this had to be caught before Week 4.** This document's own binding Day 28 reporting rule
captions any Category 1 result as a construction check rather than a finding. Under the uncorrected
text, Taubin's (large, real, informative) error on the two classic distortion axes would have been
reported as tautologically expected near-ceiling accuracy -- a caption directly contradicted by the
numbers underneath it.
