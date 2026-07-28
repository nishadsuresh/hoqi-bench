# Day 21 — The cross-validation gate (and it did not pass on the first run)

This is the one day of Week 3 that was designated **never skip**, with an explicit failure branch
written a week in advance specifically so that a failing gate could not be rationalised into
passing under schedule pressure. It failed. This entry is mostly about what it caught, because
that is the only part that matters — a gate that always passes is a decoration.

## What a "gate" is here, and why it is built in tiers

Seven methods now exist. The tempting way to validate them is to run all seven on the same clean
data and check they agree. The Weeks 3-4 plan's adversarial review had already demolished that
idea (`docs/WEEK3-4_PLAN.md` §0.2): seven implementations written by one person, in one week, from
one shared mental model of conic fitting are **not independent samples**. If I misunderstood
something about ellipse geometry, all seven inherit the misunderstanding and agree with each other
perfectly. Agreement between them is weak evidence no matter how many of them there are.

So the gate is built around evidence that does *not* come from the methods themselves:

- **Tier 1a — the analytic oracle.** Generate `(I, Q)` directly from the forward model's own
  equations, with known `(I₀, Q₀, A, g, ε)` and no noise. Any method whose model can *represent*
  that data must recover those five numbers to machine precision. The reference is the generating
  equation — algebra — not another fit. This covers all seven methods, unlike Day 19's external
  packages, which only cover two.
- **Tier 1b — the same oracle, but through the project's own pipeline.** Tier 1a generates its data
  itself, so it is blind to any defect that lives in the *simulation* code rather than in a method.
  Tier 1b reruns the exactness claim on the signal `simulate_condition` actually produces.
- **Tier 3 — the falsifiable predictions** written into `docs/WEEK3_METHOD_CONTRACT.md` §3.2–3.3
  before any method existed.

Tier 2 (cross-checking against the `lsq-ellipse` and `ellipsinator` packages) was deliberately
pulled forward to Day 19, so that a disagreement would have days of debugging room instead of hours
before a blocking gate.

## Tier 1a passed cleanly, and that mattered for what came next

All four general-conic methods — Heydemann, Halir & Flusser, Fitzgibbon, Köning — recovered the
generating ellipse's four parameters to **≤4.2e-14** at every sample count tested (N = 20, 60, 200,
1000), and recovered phase to ≤4.0e-14 rad. The shared conic→parameter conversion was checked
separately against a closed-form conic derived by hand, because a bug *there* would move all four
methods identically, which is exactly the correlated error method-agreement cannot see.

Two smaller things were worth asserting rather than assuming:

- All seven methods are exact on an undistorted circle — the one condition where every method's
  model can represent the data.
- Raw atan2, Kasa and Taubin **cannot** fit an ellipse: 0.14 rad RMS on noiseless, exact ellipse
  data. That is not a defect, it is what `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` predicts, and
  turning the prediction into a test is what caught the document error described further down.

Tier 1a passing is what made Tier 1b's failure interpretable. If both had failed, the defect could
have been anywhere. Only Tier 1b failing localises it to the simulation path.

## The failure: one duplicated sample, and a fake research finding it would have produced

Tier 1b failed on Heydemann, at every sample count:

| N | Heydemann | the other six |
|---|---|---|
| 20 | 3.8e-2 rad | 1.1e-7 rad |
| 60 | 1.3e-2 rad | 1.1e-7 rad |
| 200 | 3.9e-3 rad | 1.1e-7 rad |
| 1000 | 7.9e-4 rad | 1.1e-7 rad |

On the *noiseless, undistorted* condition — the easiest thing the benchmark can express — the
method that is supposed to be tautologically perfect there was the worst of the seven by five
orders of magnitude.

**Root cause, confirmed exactly rather than inferred.** `arc.build_arc_ramp` built its displacement
ramp with `np.linspace(0, 1, n)`, which includes both endpoints. At `arc_fraction = 1.0` that means
phase `0` and phase `2π` — the same physical point — both appear in the record. One sample out of
`N` is a duplicate. Heydemann's estimator works from second-order moments, so it computes
`mean(I)`, and the duplicate makes that `I₀ + A/N` instead of `I₀`. At `A = 0.9`, `N = 60`, that
predicts a reported DC offset of exactly `1.015`. The method reported `1.015`. The remaining error
follows the same `1/N` law across the whole table above.

The other six methods never compute a channel mean — a conic fit does not care that one point
appears twice — which is why they are unaffected to ~1e-15 either way.

**Day 17 had already found this bias and chose not to fix it.** That entry quantified it at ~1.6%
and reasoned, defensibly, that `build_arc_ramp` was load-bearing for already-validated Weeks 1-2
results and that changing it to smooth over a bias only one estimator was sensitive to was the
riskier move. Day 21 overturned that with three facts Day 17 did not have:

1. `arc_fraction = 1.0` is the **campaign baseline**, so the duplicate was present in essentially
   every condition on every axis and every interaction grid — not in one corner case.
2. The error scales as `1/N`, and `samples_per_fit` is a **preregistered swept axis** (RQ6). The
   campaign would have produced a clean, monotone "Heydemann's error falls as 1/N" curve, five
   orders of magnitude above every other method, in a chart whose stated purpose is practitioner
   guidance. Nothing about that curve would have *looked* like an artifact.
3. On the three classic axes at low noise, Heydemann would have come out roughly twelve orders of
   magnitude *worse* than the other conic fitters — falsifying this project's own structural
   prediction because of a `linspace` argument.

`build_arc_ramp` now uses `endpoint=False`: `N` samples at the left edge of `N` equal sub-intervals
of a phase window of length exactly `arc_fraction·2π`. The window covered is unchanged. This is
also the standard periodic-sampling convention — a record covering one full cycle should contain
each phase once. Recorded as deviation **D1** in `docs/PREREGISTRATION.md`, with the full argument,
and made before any campaign data exists, which is the cheapest possible moment to make it.

**Consequences, re-measured rather than assumed.** Heydemann's parameter recovery at
`quadrature_error_rad = 0.3` went from ~1.6% error to 0.009%, and from beating raw atan2 by 15x to
beating it by 725x. Every tolerance in `tests/test_heydemann.py` that had been sized around the
artifact was re-measured and tightened — leaving them loose would have let the same defect
reappear silently, which defeats the point of deriving a tolerance from measurement in the first
place. One bound in `tests/test_halir_flusser.py` was tightened 20x for a related reason: it had
been given a 2% budget on the reasoning that Halir & Flusser shares Heydemann's post-fit conversion
and therefore its bias. That reasoning was wrong — the artifact was specific to the moment
estimator — and the method had been sitting 250x inside a bound it never needed.

The second bias Day 17 documented, the interaction with `poisson_noise`'s negative-intensity clamp,
is untouched and is now cleanly isolated: 2.6% in recovered `g` at `amplitude_ratio = 1.3`, all of
it attributable to the 9 of 60 samples the clamp forces to zero, confirmed against an unclamped
analytic reconstruction where the same estimator returns `g = 1.3000000000000005`.

## Tier 3: the contract had one of its own predictions backwards

Contract §3.2 requires the ill-conditioned Fitzgibbon↔Halir & Flusser comparison to reproduce
"Day 3's qualitative ordering," and then states that ordering as *Fitzgibbon showing elevated
failure relative to Halir & Flusser*. Day 3 measured the reverse and devoted a section to it:
Fitzgibbon 0%, Halir & Flusser **60%**, because the block decomposition has to invert a matrix
(`S₃`) whose conditioning the 1998 paper never analyses.

The contract was written from the textbook expectation — that the "stable" reformulation must be
the safer one — which is precisely the error Day 3's own closing line warns against. It was
corrected to Day 3's measured direction, anchored to that journal entry (a primary record written
weeks before any method existed), not to whatever the current implementations happen to do. That
distinction is the whole difference between correcting a gate and rigging one.

Checking that claim surfaced a second, larger problem. **Day 3's "Finding 1" does not reproduce.**
That finding claims that at float32 precision Fitzgibbon genuinely fails while Halir & Flusser
succeeds cleanly. Running Day 3's own script today prints `ok` for both methods on its own demo
case. Over 200 seeds at that regime: Fitzgibbon-only failures 8% at float32 versus 7% at float64;
Halir & Flusser-only failures 37% versus 42%. Reducing precision does essentially nothing, and the
ordering never inverts. `git log -p` confirms the script's numerics are unchanged since its Day 3
commit, so this is not a regression — Finding 1 was a single-seed observation written up as a
general result.

What survives is the part Day 19 actually depends on: Fitzgibbon's singular-`C` ambiguity is real
and reachable at double precision — 12% of 200 seeds on the thinner test ellipse, every one of them
the AMBIGUOUS mode. The gate now asserts that directly, so that if some future change quietly adds
a tie-break rule or relaxes the `aᵀCa > 0` tolerance, the "deliberately not patched" claim in
`fitzgibbon.py` cannot become false without something failing. Both corrections are recorded as
dated addenda rather than edits, per the never-delete convention.

## The pre-committed §3.1 criterion passed — and is too loose to have mattered

Contract §3.1 required all seven methods to agree with ground truth, and pairwise with each other,
to within the preregistered 1% relative RMS threshold on a clean condition. All seven passed.

Two things had to be pinned down to run it at all, and both are recorded rather than quietly
resolved: the criterion never said what "relative" was relative to (fixed to the record's
full-scale phase excursion, the more conservative of the two candidate readings), and **no
condition in the campaign config is actually clean** — its baseline carries `amplitude_ratio=1.1`,
`quadrature_error_rad=0.1` and `dc_offset=0.02`, so every OFAT axis zeroes at most one of the three
at a time. The condition had to be constructed explicitly.

The honest observation is that §3.1 passed *while the defect was present*. Heydemann's 1.3e-2 rad
artifact is 0.2% of full scale, comfortably inside a 1% bound. The criterion is roughly 750x too
loose to have caught what Tier 1 caught. It is deliberately **not** tightened — changing a
pre-committed criterion after seeing results is forking-paths in either direction — but it is
recorded as not load-bearing, and the analytic oracle is treated as the real gate. That is exactly
the ranking the plan's §0.3 argued for before any of this was known, which is a small point in
favour of having written the plan that way.

## A preregistered document contradicted its own implementation

While turning the structural predictions into an actual test, one more thing fell out.
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` lists Taubin among "all four general-conic/ellipse
fitters" and puts it in **Category 1 (tautological)** on the three classic axes — meaning any Week
4 result there gets captioned as a construction check rather than a finding.

Taubin fits a **circle**. Its own module docstring says so, under a heading that says so. It has no
free parameter for `amplitude_ratio` or `quadrature_error_rad`, exactly like Kasa. Tier 1a measures
it: 0.136 rad RMS on exact ellipse data, sitting right alongside Kasa's 0.136 and raw atan2's
0.143, while the true conic fitters are at 1e-13.

Under the uncorrected document, Taubin's large, real, informative error on those two axes would
have been captioned in the final writeup as tautologically-expected near-ceiling accuracy — a label
flatly contradicted by the numbers printed underneath it. Recorded as deviation D1 in that
document, which had been carrying an empty deviation record until today.

## State at close

133 tests passing (123 before today), `ruff` and `mypy --strict` clean. The gate is in
`tests/test_cross_validation_gate.py` and runs on every future commit, so none of the four
corrections above can silently regress.

Four real defects, none of which any individual method's own test suite would have found, because
each lived in the seams: one in the simulation path (`arc.py`), one in the gate criteria
themselves, one in a primary journal record, and one in a preregistered predictions document. That
is a reasonable argument for why the gate day was worth not skipping.
