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

### 2.1 Binding extension, 2026-07-27 (Week 3 review): `failed` measures SELF-DETECTION, not failure

**The measurement.** Every method was run over all 359 main-campaign
conditions x 5 seeds (12,565 fits per method), recording both the
self-reported failure rate and the rate of *gross error while reporting
success* -- defined as `failed=False` with a wrapped-phase RMSE above
0.5 rad, i.e. ~8% of a full cycle, an answer no practitioner could use:

| method | `failed=True` | gross error, `failed=False` |
|---|---|---|
| raw_atan2 | 0.00% | 0.00% |
| kasa | 0.00% | 6.80% |
| heydemann | 24.51% | 0.00% |
| halir_flusser | 0.56% | 12.59% |
| fitzgibbon | 0.00% | 13.48% |
| taubin | 0.00% | 3.06% |
| koning_wimmer_witkovsky | 15.65% | 1.62% |

**Why this is a contract problem and not just a result.** §2 above, and
`docs/PREREGISTRATION.md`'s Metrics section, commit to reporting failure
rate as a first-class metric, separately from error-when-successful,
precisely so that "a method that fails 40% of the time and is accurate on
the other 60%" cannot hide behind one average. Taken at face value, the
left column says **Heydemann is by far the least reliable of the seven and
Fitzgibbon is flawless**. The right column says the opposite is true:
Heydemann never once returned an unusable answer, and Fitzgibbon returned
one 13.5% of the time without saying so.

The difference between the two columns is not reliability. It is whether a
method's authors built a self-consistency check into it. Heydemann has one
(its post-correction radius guard, Day 17) because its silent-garbage mode
was found and closed; Kasa's `lstsq` returns a minimum-norm solution on a
rank-deficient design without raising, Taubin's and Fitzgibbon's eigen-
solves return *a* candidate, and none of them has any notion of whether the
answer is meaningful. Comparing these failure rates across methods compares
introspection, not performance.

**What was deliberately NOT done.** No method was given a new guard. Adding
a uniform post-fit validity check to all seven would make the failure rates
comparable, but at the cost of changing what each method *is* -- Kasa's own
acceptance bar was port fidelity to an unguarded algorithm (Day 16), and
`docs/WEEK3-4_PLAN.md` Day 20 explicitly forbids "silently fixing a method
by altering its algorithm." The asymmetry is real and belongs in the
results, not hidden by normalising it away.

**Binding requirement on Day 22**, extending §0.4's survivorship-bias fix
(which anticipated only the mirror-image problem -- methods dropping *out*
of hard regimes -- and not this one):

1. Every aggregate reports a **gross-error rate** alongside failure rate and
   error-when-successful. Three numbers per method per condition, not two.
2. The gross-error threshold is fixed **now, before the campaign runs**, at
   the 0.5 rad wrapped-phase RMSE used for the table above, with the
   rationale stated there. It is not to be re-chosen after seeing results.
3. Any reported failure-rate comparison across methods carries the caption
   that it measures self-detected failure. A method with no failure mode is
   reported as having none, not as having a 0% failure rate.

**One result worth naming now, because it is genuinely non-tautological and
nothing predicted it**: raw atan2 -- the deliberately naive floor every
other method is supposed to beat -- is the *most reliable* method in the
benchmark on both columns, 0% and 0%, because it never fits anything and so
has nothing that can become ill-conditioned. That accuracy and reliability
separate this cleanly is not something
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` anticipated on any axis.

### 2.2 Implemented 2026-07-27 (Day 22), with the two thresholds pre-committed

`src/hoqi_bench/aggregate.py` implements §2.1 and §0.4 together. Both
thresholds are fixed here and in that module, before Day 24's runner
exists and before any campaign result exists:

- `GROSS_ERROR_PHASE_RAD = 0.5` -- as justified in §2.1. Defined once, in
  `aggregate.py`, and imported by `tests/test_failure_contract.py` rather
  than restated there; it was briefly written in both places, which is the
  same stale-hand-copied-number defect the Weeks 1-2 audit caught as
  findings F7/F8.
- `MAX_UNUSABLE_RATE_FOR_RANKING = 0.20` -- the §0.4 gate. Chosen on an
  external principle rather than from the observed distribution, which
  matters because the campaign-wide rates in §2.1's table were already
  measured by the time this was written and a threshold picked afterwards
  could not be shown to be innocent of them. Above roughly 20% attrition, a
  complete-case analysis is conventionally treated as at serious risk of
  bias regardless of mechanism, because the survivors are a strongly
  selected subsample. That convention is the anchor, not any particular
  method's rate here.

**§0.4's gate is deliberately STRENGTHENED, recorded as a dated deviation
from that section's own wording.** §0.4 says "no method is ranked on any
condition where any method's FAILURE RATE exceeds a threshold." Applied
literally, a method with no failure mode at all self-reports 0% forever and
can never trigger the gate, however much unusable output it produces --
which is the exact hole §2.1 found, and which would have left Fitzgibbon
(0.00% failures, 13.48% gross errors) ranked everywhere. The implemented
gate therefore keys on `unusable_rate` (failure + gross error), so a method
that is silently wrong is excluded on the same terms as one that says so.

The gate is also **all-or-nothing per condition**: if any method exceeds
the threshold, no method is ranked at that condition. Dropping only the
offending method and ranking the rest would leave exactly the
flattering-by-attrition artifact §0.4 exists to prevent, on the remaining
pairs. A non-rankable condition is still fully reported -- with its
reliability rates, which on a hard condition are frequently the most
informative thing about it -- it simply contributes no ordering.

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

**Clarification and observation, 2026-07-27 (Day 21), recorded rather than
silently resolved at implementation time:**

1. *The denominator was never specified.* "Within tolerance = 0.01 (the
   preregistered 1% relative RMS error threshold)" does not say what the
   error is relative to, and leaving that open until after seeing results
   is precisely how a gate gets rationalised into passing. Fixed at
   implementation: **the record's full-scale phase excursion**
   (`arc_fraction * 2π`). This is the more conservative of the two readings
   considered -- dividing by the signal's RMS instead would be ~1.7x more
   permissive.
2. *No condition in `configs/main_campaign.toml` is actually clean.* The
   baseline carries `amplitude_ratio=1.1`, `quadrature_error_rad=0.1` and
   `dc_offset=0.02`, so each OFAT axis zeroes at most one of the three. The
   §3.1 condition is therefore constructed explicitly in the gate test,
   from the campaign baseline with the three classic distortions set to
   their identity values. `photon_scale` has no true "off" value
   (`noise.poisson_noise`'s own docstring), so the campaign's `1e7`
   "negligible" placeholder is used.
3. *This criterion passed, but is ~750x too loose to be the load-bearing
   check.* All 7 methods came in under 0.01 relative on the clean
   condition -- including Heydemann at the point where Tier 1b showed it
   carrying a real 1.3e-2 rad artifact (0.2% of full scale, comfortably
   inside 1%). The defect was caught by the analytic oracle instead, which
   is exactly the ranking `docs/WEEK3-4_PLAN.md` §0.3 argued for and §0.2's
   "internal agreement is near-worthless as evidence" predicted. **The
   tolerance is deliberately NOT tightened here** -- changing a
   pre-committed criterion after seeing results is forking-paths in either
   direction. It is recorded as too loose, and Tier 1's machine-precision
   check is treated as the real gate.

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

**Deviation, 2026-07-27 (Day 21) -- the gate criterion above states Day 3's
ordering BACKWARDS, and is corrected here rather than quietly aligned to
whatever the implementations happen to do.** The parenthetical demands that
"Fitzgibbon show elevated failure/error relative to Halir & Flusser" in the
ill-conditioned regime. `docs/journal/day03.md` measured the opposite, and
says so at length under its own heading "Finding 2 -- an honest, unplanned
result that complicates the story": at `near_degenerate_15deg`,
**Fitzgibbon failed 0% and Halir & Flusser failed 60%**, because the block
decomposition must invert `S3` (cond ~1.2e8 there), a failure mode the 1998
paper does not analyse. This section was written 2026-07-26 from the
textbook expectation -- that the "stable" reformulation is the safer one --
which is exactly the error Day 3's own journal warned against in its
closing line ("Neither method should be documented as unconditionally safer
than the other"). Corrected criterion, asserted in
`tests/test_cross_validation_gate.py`:

- Halir & Flusser's failure rate at `near_degenerate_15deg` must reproduce
  Day 3's ~60%, and must EXCEED Fitzgibbon's there.
- Fitzgibbon's own singular-`C` ambiguity must nonetheless still be
  reachable and unpatched -- checked at the thinner (`semi_minor=0.001`)
  ellipse from Day 3's own `demonstrate_clean_divergence`, where it is:
  measured 12% Fitzgibbon failures over 200 seeds (all of them the
  AMBIGUOUS mode) against 42% for Halir & Flusser. This is what protects
  Day 19's scientific point -- if a future change added a tie-break rule or
  relaxed the `a^T*C*a > 0` tolerance, `fitzgibbon.py`'s "deliberately not
  patched" docstring would silently become false with nothing failing.

**A second, separate correction to Day 3's own record, from the same
check.** Day 3's "Finding 1" claims that at float32 precision Fitzgibbon
genuinely fails while Halir & Flusser succeeds cleanly. **This does not
reproduce.** Re-running Day 3's own script today prints `ok` for both
methods on its own demo case, and the script's numerics are unchanged since
its Day 3 commit (verified with `git log -p`; only cosmetic refactors
since). Over 200 seeds at that regime: Fitzgibbon-only failures 8% at
float32 vs 7% at float64, Halir & Flusser-only failures 37% vs 42% --
reducing precision to float32 makes essentially no difference, and the
ordering never inverts. Finding 1 was a single-seed observation reported as
a general result. Recorded as a dated addendum in `docs/journal/day03.md`
rather than edited out. Finding 2 is unaffected and is robustly confirmed.

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
