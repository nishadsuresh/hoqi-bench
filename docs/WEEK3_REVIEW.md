# Week 3 Review (Days 15-21)

Written 2026-07-27, after Day 21's cross-validation gate closed and before any Week 4 code exists.
Same purpose and same standard as `docs/WEEK1-2_AUDIT.md`: a full adversarial re-read of everything
Week 3 produced — seven method implementations, the shared interface and post-fit machinery, every
test, and every document Week 3 was written against — looking specifically for the class of defect
that a green test suite does not catch, because every one of Week 3's own tests was passing at the
start of this review.

**Scope note on what "review" means here.** Day 21's gate is not summarised in this document; it
has its own journal entry (`docs/journal/day21.md`) and its four findings are recorded as dated
deviations in the documents they affect. This file covers what a *separate* pass over Week 3 found
after the gate was green, plus the campaign-scale measurements that pass produced.

Everything below was measured, not inferred. Where a number appears, it came from running the real
campaign grid (359 conditions) through the real pipeline.

---

## Summary

| # | Finding | Severity | Disposition |
|---|---|---|---|
| **R1** | `failed` measures self-DETECTION, not failure — inverting the reliability ranking | **High** | Contract §2.1 written; binding on Day 22; enforced by `tests/test_failure_contract.py` |
| **R2** | Heydemann's radius guard drives a 24.51% failure rate — precision never measured | Medium | Measured at 87.5%; documented at the constant |
| **R3** | Köning's `_MAX_ITER = 20` is load-bearing on a headline metric and was arbitrary | Medium | Validated and pre-committed with evidence; kept at 20 |
| **R4** | Shared conic conversion can return finite-but-absurd values past every `isfinite` guard | Low | Measured unreachable from the campaign; documented, not guarded |
| **R5** | `raw_atan2`'s calling convention duplicated across 3 call sites; Day 24 would be the 4th | Medium | Consolidated into `methods.fit_by_name` before the runner exists |
| **R6** | README described a project three weeks out of date | Low | Rewritten |

Four further findings — the `arc.py` sampling defect, the §3.2 gate criterion stated backwards,
Day 3's Finding 1 not reproducing, and Taubin misclassified in the structural predictions — came out
of Day 21's gate itself and are recorded in `docs/journal/day21.md`.

---

## R1 — The preregistered failure rate measures introspection, not reliability

**Severity: high.** This one inverts a headline metric.

Every method was run over all 359 main-campaign conditions × 5 seeds (12,565 fits per method),
recording both the self-reported failure rate and the rate of *gross error while reporting success*
— `failed=False` with a wrapped-phase RMSE above 0.5 rad, roughly 8% of a full cycle, or ~25 nm of
a 316 nm HeNe half-wavelength range. An answer no practitioner could act on.

| method | `failed=True` | gross error, `failed=False` |
|---|---|---|
| raw_atan2 | 0.00% | 0.00% |
| kasa | 0.00% | 6.80% |
| heydemann | **24.51%** | **0.00%** |
| halir_flusser | 0.56% | 12.59% |
| fitzgibbon | **0.00%** | **13.48%** |
| taubin | 0.00% | 3.06% |
| koning_wimmer_witkovsky | 15.65% | 1.62% |

`docs/PREREGISTRATION.md`'s Metrics section commits to reporting failure rate as a first-class
number, separately from error-when-successful, so that "a method that fails 40% of the time and is
accurate on the other 60%" cannot hide behind one average. That commitment is sound. The problem is
what the number actually measures.

Read as preregistered — left column only — the campaign will report that **Heydemann is by far the
least reliable of the seven methods and Fitzgibbon is flawless.** The right column says the reverse
is true: Heydemann never once returned an unusable answer across 12,565 fits, and Fitzgibbon
returned one 13.5% of the time without saying so.

The two columns differ by whether a method carries a self-consistency check, not by whether it
works. Heydemann has one (its post-correction radius guard, added Day 17 when its silent-garbage
mode was found). Kasa's `lstsq` returns a minimum-norm solution on a rank-deficient design without
raising. Taubin's and Fitzgibbon's eigen-solves always return *a* candidate. None of those three has
any notion of whether its own answer is meaningful, so none of them can report a failure, so all
three score a perfect 0%.

**What was deliberately not done.** No method was given a new guard. Making the failure rates
comparable by adding a uniform post-fit validity check to all seven would change what each method
*is* — Kasa's own Day 16 acceptance bar was port fidelity to a deliberately unguarded algorithm, and
`docs/WEEK3-4_PLAN.md` Day 20 explicitly forbids "silently fixing a method by altering its
algorithm." The asymmetry is a real property of these methods and belongs in the results.

**Relationship to §0.4.** The Weeks 3-4 plan's adversarial review already flagged a
survivorship-bias problem: methods that fail preferentially in hard regimes make per-condition means
compare different populations. That is real, and Day 22 already has to fix it. R1 is its mirror
image, and the review missed it — methods that *never* drop out, and are ranked on conditions where
their output is meaningless. Between the two, the second is worse: a dropout at least leaves a
visible hole.

**Disposition.** Written up as a binding extension, `docs/WEEK3_METHOD_CONTRACT.md` §2.1, requiring
three numbers per method per condition rather than two, with the 0.5 rad threshold fixed before the
campaign runs and not re-choosable afterwards. Enforced by `tests/test_failure_contract.py`, which
asserts the *direction* of the asymmetry rather than any specific rate — the guards involved are a
few lines inside individual methods, and someone adding a plausibility check to Kasa would change
what the campaign's reliability numbers mean in a diff that looks entirely local.

**One result worth naming now, before it can be invented post hoc.** raw atan2 — the deliberately
naive floor every other method exists to beat — is the most reliable method in the benchmark, 0% and
0%, because it fits nothing and therefore has nothing that can become ill-conditioned.
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` predicts it will be the *worst* method on accuracy on
every single axis and says nothing about reliability. That accuracy and reliability separate this
cleanly is not a construction check, and it is the kind of practitioner-facing result this benchmark
exists to produce.

---

## R2 — Heydemann's guard was never measured for precision, only for separation

Day 17 calibrated `_RADIUS_CONSISTENCY_THRESHOLD = 0.15` by checking that legitimate conditions sit
below it (~0.12) and degenerate ones above (~0.33). That establishes separation. It does not
establish how often the guard is *right*, and since this guard is the sole cause of the 24.51%
failure rate that Week 5 will report as a headline number, "how often is it right" is the question
that number's interpretation depends on.

Measured by re-running every guard-triggered fit with the guard removed, across all 359 conditions ×
5 seeds:

- Guard fired **440** times.
- **385 (87.5%)** would have exceeded 0.5 rad — correctly rejected.
- **55 (12.5%)** discarded a usable fit, at a median error of 0.33 rad and a worst case of 0.357 rad.

So the guard is conservative in the right direction, and its cost is bounded and known. That is what
makes it possible to report 24.51% honestly: this is a method that declines to answer when it
cannot, not a method that breaks. Recorded at the constant itself, next to Day 17's original
calibration, rather than in a document that drifts.

---

## R3 — Köning's iteration cap turned out to be load-bearing on a reported metric

`_MAX_ITER = 20` was a round number. Köning is the only iterative method, so it is the only one
whose reported failure rate depends on a tunable — which makes "Köning fails 15.65% of the time"
partly a statement about that constant, and an arbitrary constant is not something to discover after
publishing.

Measured over a 1/3 sample of the campaign grid × 2 seeds:

| cap | non-convergent | converged **and usable** | converged but gross error |
|---|---|---|---|
| 20 | 12.92% | **82.92%** | 0.83% |
| 50 | 4.17% | **82.92%** | 2.50% |
| 200 | 2.50% | **82.92%** | 2.50% |

The middle column does not move at all. Raising the cap converts non-convergence into
converged-but-wrong, never into a usable answer. So the cap is not truncating fits that were about
to succeed: at 20 iterations, non-convergence is a *validated proxy* for "this fit is not going to
be usable."

That is the honest reason to keep it. Raising the cap would have cut Köning's reported failure rate
from 12.9% to 2.5% while producing zero additional correct answers — a better-looking number bought
entirely by relabelling bad answers as good ones. Kept at 20, now pre-committed with its evidence at
the constant. (Every convergent fit on real campaign data uses 2-6 iterations, median 6.)

---

## R4 — A real but unreachable failure path in the shared conic conversion

`conic_to_heydemann_params` raises `LinAlgError` on an exactly-singular center solve, and all four
conic-fitting methods catch it. A *near*-singular solve does not raise, and can return a finite but
physically absurd center that passes every caller's `np.isfinite` check — confirmed directly:
`conic_to_heydemann_params(1e-18, 0, 1e-18, 1, 1, 1)` returns a center of `-5e17` with
`all_finite=True`, and every caller would report `failed=False`.

Checked whether this contributes to R1's gross-error rates rather than assuming it does. It does
not: across all 359 conditions × 3 seeds, every gross-error fit from all four conic-fitting methods
recovered a center within 0.16 of the data's own span (median 0.03). Those are plausible fits that
are simply wrong at small `arc_fraction` — a real result about ellipse fitting on a 7° arc, not a
numerical pathology.

Left unguarded. Adding a plausibility bound would change no campaign number while introducing a
threshold with nothing to calibrate it against, which `docs/DOCUMENTATION_STANDARD.md` rules out
explicitly. Documented at the function so a future config exploring more extreme geometry knows the
path exists.

---

## R5 — The one non-uniform calling convention had already been copied three times

`PhaseRecoveryMethod` is `Callable[..., FitResult]` with everything past `(intensity_i,
intensity_q)` keyword-only and method-specific. Exactly one method uses that freedom: `raw_atan2`
takes `mean_intensity`, the one nominal design constant a "no correction" baseline may assume
without estimating it.

That means iterating `METHOD_REGISTRY` needs an `if name == "raw_atan2"` branch at the call site,
and by the end of Week 3 three call sites had independently grown their own copy —
`scripts/robustness_matrix.py`, `tests/test_full_campaign_smoke.py`, and Day 21's own gate. Day 24's
sweep runner would have been the fourth.

This is the same shape of defect the Weeks 3-4 plan named as its highest-value pre-Week-3 fix (P1:
"glue that every consumer reconstructs independently, with no single place enforcing it"), and it
had quietly regrown. The specific hazard is not the duplication itself but that a copy passing the
wrong `mean_intensity` produces a plausible-looking wrong answer from the baseline method, with
nothing raising — and the baseline is what every other method's performance is quoted relative to.

Consolidated into `hoqi_bench.methods.fit_by_name`, with `mean_intensity` required rather than
defaulted, and all three existing call sites migrated. Done before the runner exists rather than
after.

---

## R6 — The README described a different project

The project's front door still said "Weeks 1-2 of 6 complete", "75/75 tests passing", "method
implementations… begin Week 3", listed the preregistration's external timestamp and the GitHub push
blocker as unresolved open items (both closed 2026-07-27), and omitted `src/hoqi_bench/methods/`
entirely from the project structure. Rewritten to describe the current state, including the three
limitations a reader is most likely to want stated and least likely to find on their own: external
cross-validation covers only 2 of the 7 methods, seven implementations by one author are not seven
independent samples, and per-method failure rates are not directly comparable (R1).

---

## What was checked and found sound

Recorded because "we looked and it was fine" is information, and because a review that only lists
problems gives no sense of coverage.

- **Contract §2 compliance.** Every method returns a result for every (condition, seed) pair, with
  an all-NaN phase array of the correct length and a specific reason code on failure — never a
  generic `"failed"`, never an absent row. Verified across a 1-in-7 sample of the campaign in
  `tests/test_failure_contract.py`.
- **The no-shared-code-below-`fit()` rule.** Held. `_ellipse.py` contains only post-fit machinery
  (conic → phase) and the correction transform; each method's actual numerical path to a fitted
  conic is its own. Heydemann's Day 17 decision not to port the "obvious" implementation — which
  would have made it and Halir & Flusser the same eigen-solve wearing different names — is the
  reason this holds, and it is the single most important structural decision of Week 3.
- **Day 21's Tier 1a oracle across sample counts.** All four general-conic methods recover the
  generating ellipse's parameters to ≤4.2e-14 at N ∈ {20, 60, 200, 1000}. No method is exact at one
  sample count and biased at another.
- **The robustness matrix.** Re-run post-`arc.py`-change: 0 crashes across all 35 method × adversarial-input
  cells.
- **Köning's covariance.** Finite, symmetric, and positive semi-definite at convergence, and scoped
  honestly in its own docstring as covariance of the raw conic coefficients rather than the
  phase-space uncertainty the 2014 paper's title promises.
- **Test quality.** No tautological or unfailable assertions found. The tests that could most easily
  have been written that way — Fitzgibbon's and Halir & Flusser's per-regime failure rates — instead
  assert against Day 3's specific measured numbers, which is what made it possible to notice that
  one of those numbers no longer reproduces.

## One environment note, not a code finding

The 12,565-fit review sweep crashed once with `SIGFPE`, then completed cleanly on an immediate retry
with byte-identical output. This matches a known intermittent numpy/BLAS instability in this WSL2
environment and is the same class of problem Day 20's runtime probe found (and fixed for the
in-process case with the BLAS thread pin). It is recorded here rather than dismissed because
reproducibility is this project's stated contribution: Day 24's runner needs to survive a worker
process dying without silently losing that worker's rows.
