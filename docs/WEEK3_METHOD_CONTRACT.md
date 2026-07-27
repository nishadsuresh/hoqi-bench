# Week 3 Method Contract

Written 2026-07-26, before Day 15's first method exists, per the Weeks 1-2 audit's
recommendation that gate criteria and failure-handling conventions be fixed
in advance rather than authored after seeing results (a gate written after
the fact isn't a gate). This document is binding on every method
implementation in Days 15-20 and on Day 21's cross-validation gate; any
deviation must be recorded here, dated, with a reason, the same discipline
`docs/PREREGISTRATION.md` already holds itself to.

## 1. Primary endpoint: wrapped (circular) phase error

**Displacement error** (meters) is an ordinary linear quantity -- RMSE and
peak absolute error, as already specified in `docs/PREREGISTRATION.md`'s
Metrics section, need no correction.

**Phase error** (radians) is NOT linear -- phase is periodic mod 2*pi, so a
method that recovers phase correct to within 0.02 rad near a +-pi wrap
boundary (e.g. true = pi - 0.01, recovered = -pi + 0.01) has a naive linear
difference of ~2*pi, a ~300x overstatement that would dominate any RMSE
computed the ordinary way and silently corrupt every method's reported
accuracy near that boundary.

**Rule**: any error computed on RECOVERED PHASE (as opposed to recovered
displacement) must use `hoqi_bench.metrics.wrapped_phase_error`, which wraps
the raw difference into `(-pi, pi]` via standard circular-statistics
wrapping (`((diff + pi) mod 2*pi) - pi`) before any aggregation (RMSE, mean,
percentile, etc.). This is already implemented and tested
(`src/hoqi_bench/metrics.py`, `tests/test_metrics.py`) -- Day 22-23's
metrics implementation must use it, not re-derive the wrapping.

**Cyclic-error harmonic amplitude** (already a preregistered metric) is
unaffected by this -- it's computed via FFT/harmonic fit on the residual,
which is a different operation from a raw phase-difference RMSE and doesn't
have the same wraparound failure mode.

## 2. Fit-failure contract

**Rule**: every method must return a result for every (condition, seed)
pair -- there is no case where a method silently contributes zero rows to
the results table. A method that cannot produce a valid fit (non-convergence,
NaN, a rejected ellipse-specific solution, a singular matrix) must return:

- `displacement_error = NaN` (and phase error, harmonic amplitude, etc. --
  every numeric field NaN)
- an explicit **reason code** (a short string, e.g.
  `"singular_scatter_matrix"`, `"non_convergent"`,
  `"rejected_ellipse_solution"` -- specific enough to distinguish failure
  MODES from each other, not a generic `"failed"`)
- `failed = True` (a boolean field, so failure rate -- already a
  preregistered first-class metric per `docs/PREREGISTRATION.md` -- can be
  computed as `mean(failed)` directly, without inferring failure from NaN
  presence)

**Why this matters, concretely**: `docs/PREREGISTRATION.md`'s own Metrics
section already commits to reporting failure rate SEPARATELY from
error-when-successful ("a method that fails 40% of the time and is accurate
on the other 60% is reported as exactly that -- two numbers, not one
average that hides the failures"). That commitment is unenforceable if a
failed fit can just not appear in the results table: Week 5's analysis would
silently average only over survivors, and every method would look equally
accurate regardless of its actual failure rate. The rule above is what
makes the preregistered commitment actually true of the data, not just of
the prose describing it.

**Consequence for Days 15-20**: every method's return type must be capable
of representing this failure state (Day 15's common Protocol/ABC -- not
designed yet, but must accommodate this) -- this document does not itself
define that dataclass/Protocol, since the actual interface is Day 15's task;
it fixes the CONTRACT that interface must satisfy.

## 3. Day 21 cross-validation gate

Day 21 is a hard, never-skip gate (per the original build plan): all 7
methods must agree on clean (noiseless, undistorted) data, and the
project's own qualitative literature ordering must reproduce. Pass criteria,
fixed here rather than written after seeing Day 15-20's actual results:

### 3.1 Agreement on clean data

On a noiseless, full-circle (`arc_fraction=1.0`), undistorted
(`amplitude_ratio=1.0`, `quadrature_error_rad=0.0`, `dc_offset=0.0`)
condition, all 7 methods must recover displacement to within
`tolerance = 0.01` (the preregistered 1% relative RMS error threshold) of
each other and of ground truth. Any method failing this on the easiest
possible condition is a bug in that method's implementation, not a finding
about the method itself, and must be fixed before Day 22 proceeds.

### 3.2 Fitzgibbon <-> Halir & Flusser equivalence (a positive test, not just a risk)

Halir & Flusser's method is a numerically stable REFORMULATION of
Fitzgibbon's direct least-squares ellipse fit -- in exact arithmetic, the
two solve the identical problem and must return the identical ellipse. This
is a testable prediction, not a caveat to hedge around:

- **In well-conditioned regimes** (full arc coverage, moderate noise,
  `amplitude_ratio` not near 1.0's degenerate boundary): Fitzgibbon and
  Halir & Flusser must agree to tight numerical tolerance (matching
  `scripts/explore_ellipse_constraints.py`'s Day 3 finding for the
  "well_conditioned" regime).
- **In ill-conditioned regimes** (small arc coverage, near-degenerate
  ellipses): the two are EXPECTED to diverge -- Fitzgibbon's known failure
  modes (no valid candidate, or an ambiguous multiple-candidate case,
  per `scripts/explore_ellipse_constraints.py`'s docstring) are the reason
  Halir & Flusser's reformulation exists. Divergence here is confirmation
  of Day 3's finding, not a bug.

**Gate criterion**: Day 21 must assert BOTH halves explicitly -- agreement
in the well-conditioned regime (a bug if it fails) AND divergence in the
ill-conditioned regime reproducing Day 3's qualitative ordering (a bug if
Fitzgibbon does NOT show elevated failure/error relative to Halir & Flusser
there, since that would mean Day 3's finding doesn't generalize from the
exploratory script to the real method implementations).

### 3.3 Kasa <-> Taubin relationship

Taubin's method is Kasa's algebraic circle fit with a bias correction --
both solve a similar linear system. Day 21 should confirm they agree
closely in low-noise conditions (where the bias correction has little to
correct) and diverge as noise increases (where Taubin's correction should
measurably reduce bias relative to Kasa) -- the qualitative ordering the
classic literature reports, reproduced here as a falsifiable check rather
than assumed.

**Deviation, 2026-07-27 (Day 20), falsified and narrowed, not silently
dropped**: the italicized prediction above -- "Taubin's correction should
measurably reduce bias relative to Kasa" -- is TRUE for RADIUS estimation
(the classic literature's own claim) but FALSE for phase-recovery RMSE
specifically. Verified directly, with matched estimators, 200 seeds, at
`axis:noise_std=0.1` (the top of the swept range, where any bias effect
should be largest): Taubin's radius bias is `-0.0095` vs. Kasa's `+0.0535`
-- Taubin's radius bias genuinely is ~5.6x smaller, confirming the
textbook effect and confirming the Taubin implementation itself is
correct. But `atan2`-based phase recovery depends ONLY on the fitted
CENTER, never the radius -- and center bias shows no such improvement
(`-0.0024` for Taubin vs. `+0.0003` for Kasa; Taubin's center bias is, if
anything, larger here). Day 21's gate is narrowed accordingly: checks
Taubin's RADIUS-estimation advantage directly (the effect that is
actually real and measurable), not a phase-RMSE-ordering claim the
classic literature's own result was never about in the first place.

Any change to the wrapping rule, the failure-contract fields, or the Day 21
gate criteria after this point must be recorded as an explicit, dated
deviation in this document, with the reason stated -- matching
`docs/PREREGISTRATION.md`'s own "What counts as deviating from this plan"
discipline.
