# Preregistration

Committed 2026-07-26, before any main-campaign result exists. This document fixes the research
questions, parameter space, metrics, and analysis plan from `docs/experimental_design.md` (approved
the same day, after Nishad's expansion request) as the plan this project is held to, going forward.

## Why preregistration matters here specifically

The single biggest failure mode in solo research with no external reviewer isn't fraud — it's a
much quieter thing: unconsciously steering the analysis toward whichever result feels most
satisfying, after the fact. If the parameter ranges, the metrics, and the statistical protocol are
only decided *after* looking at some early results, it becomes very easy to retroactively justify
"well, that range made more sense anyway" in whichever direction happens to make the story cleaner
— not through dishonesty, but because a compelling narrative is a real, human pull, and nobody is
checking. Writing all of this down *before* the main campaign runs, and then holding to it (or
explicitly, visibly deviating from it and saying why), is the cheapest available substitute for
having an external reviewer who would otherwise catch that kind of drift.

## Research questions (unchanged from the original plan)

- **RQ1** — Across a common controlled parameter space, how do the major phase-recovery methods
  compare on displacement accuracy, cyclic-error harmonics, robustness, and cost?
- **RQ2** — For each method, at what parameter magnitude does error exceed a stated tolerance?
- **RQ3** — Do methods built for classic static ellipse distortion retain accuracy under Lehmann et
  al.'s power-law and direction-dependent nonlinearity classes?
- **RQ4** — Under physically correct signal-dependent Poisson shot noise rather than the usual
  Gaussian assumption, do the comparative rankings change?
- **RQ5** — How does performance depend on phase-excursion regime (many-fringe ramp vs. small
  steady-state vibration)?

## Parameter space (per the approved, expanded `docs/experimental_design.md`)

- **Methods (7, all required)**: raw atan2 (no correction), Kasa, Heydemann, Halir & Flusser,
  Fitzgibbon, Taubin, Köning/Wimmer/Witkovský.
- **OFAT axes**: amplitude ratio (10 points, `[1.0, 1.5]`), quadrature phase error (10 points,
  `[0, 0.5]` rad), DC offset (8 points, `[0, 0.2]*A`), arc coverage fraction (9 points,
  `[0.02, 1.0]`), noise level (10 points, `[0, 0.1]*A`).
- **Interaction grids (3)**: arc-fraction x noise (90 conditions), amplitude-ratio x
  quadrature-error (100 conditions), amplitude-ratio x noise (100 conditions).
- **Monte Carlo seeds**: 50 per condition.
- **Total**: 337 conditions x 7 methods x 50 seeds = 117,950 runs.

## Metrics (committed now, implemented Day 22-23)

- Displacement RMSE and peak absolute error.
- **Cost**, defined explicitly (not left as a placeholder): wall-clock time per fit (mean and std
  across seeds, same hardware), and a secondary iteration count for iterative methods (currently
  only Köning/Wimmer/Witkovský — see below — since every other method is a single-shot linear
  solve with no iteration count to report).
- **Robustness**, defined explicitly as one number per method per condition: failure rate (fraction
  of the 50 seeds where the method returns no valid fit — NaN, non-convergence, or a rejected
  ellipse-specific solution), reported separately from error-when-successful, never blended into a
  single combined score. A method that fails 40% of the time and is accurate on the other 60% is
  reported as exactly that — two numbers, not one average that hides the failures.
- Cyclic-error harmonic amplitude (first and second order).

## Statistical protocol (committed now, implemented Day 25)

- Bootstrap confidence intervals (percentile method) on the mean across 50 seeds per condition —
  chosen over a normal-approximation CI because failure-inflated distributions are not assumed
  normal.
- Breakdown-threshold: smallest swept value where mean error (excluding outright failures, tracked
  separately) first exceeds 1% relative RMS error, via linear interpolation between grid points.
  **Applies only to the amplitude-ratio and arc-coverage axes**, both grounded in real numbers
  (Lehmann et al. 2025's reported typical/drift values, and Day 3's own findings, respectively) —
  see item 1 in "Revision history" below for why quadrature-error and DC-offset breakdown
  thresholds are NOT reported as calibrated quantitative values.
- Multiple-comparison correction: **Bonferroni, family = all pairwise method comparisons WITHIN a
  single research question and a single swept condition** (i.e., 21 pairwise comparisons per
  condition for 7 methods, corrected alpha = 0.05/21 ≈ 0.0024 per condition) — not a single global
  correction across all 337 conditions x 5 RQs, which would be needlessly conservative to the point
  of guaranteeing false negatives (per the council review below). Comparisons across different
  conditions or different RQs are treated as separate families, each with their own
  per-condition correction, not pooled into one number.

## Revision history

**2026-07-26: revised following an adversarial llm-council review**, run per Day 6's own
instructions to attack the plan rather than rubber-stamp it. Full transcript and verdict available
on request; changes made as a direct result, each with the reason:

1. **RQ2's breakdown thresholds, demoted on two axes.** The council's strongest, most convergent
   finding: reporting a precise breakdown threshold (e.g. "method X breaks at quadrature-error =
   0.31 rad") on a grid that is admittedly an engineering guess, not a measurement, is false
   precision — a bootstrap CI quantifies Monte Carlo sampling noise, not the deeper uncertainty of
   whether the grid itself is even in the right neighborhood of real hardware behavior. **Fix
   applied**: quadrature-error and DC-offset breakdown findings are reported as *ordinal/relative
   only* ("method X degrades earlier than method Y on this grid") — never as a calibrated
   engineering threshold implying real hardware will behave identically. Amplitude-ratio and
   arc-coverage breakdown thresholds keep full quantitative reporting, since those axes are grounded
   in Lehmann et al. 2025's actual reported numbers and Day 3's own findings respectively.
2. **Köning/Wimmer/Witkovský's implementation risk, substantially reduced, not just flagged.**
   Rather than leaving this as a named risk, direct action was taken immediately after the council
   review: found and read the CRAN `OEFPIL` package manual (open access), which explicitly
   generalizes this exact method and describes the real algorithm family in equation-level
   detail — an errors-in-variables (EIV) model fit via iterated Taylor linearization, distinct in
   kind from every other method's single-shot linear-algebra solve (see `notes/koning_2014.md`'s
   2026-07-26 update). This is enough to implement a faithful version of the algorithm family.
   **Named fallback, in case that proves harder than expected at Day 19-20**: if a working
   iterated-linearization EIV fit isn't achieved by Day 19, substitute a simpler covariance-weighted
   total-least-squares ellipse fit (a one-shot approximation of the same EIV idea, well-documented
   in the general TLS literature) and flag the substitution explicitly in every output table rather
   than silently presenting it as the 2014 paper's actual method.
3. **RQ3's power-law fork, given a default and a stated fallback.** Per the council's synthesis of
   the Expansionist's one salvageable point (frame RQ3's output as a falsifiable operating-envelope
   boundary) combined with the majority's insistence that an undefined mechanism can't be
   preregistered: **default interpretation, effective now**: the power-law relationship is treated
   as an *emergent property to characterize*, not a distinct mechanism to inject — i.e., sweep the
   already-defined classic distortions (amplitude ratio, quadrature error, DC offset) and fit a
   power-law curve to the resulting residual-error-vs-magnitude relationship, checking whether the
   exponent matches Lehmann et al.'s reported "close to power of 3." **Named fallback**: if this
   produces no clean power-law relationship at all (a real, reportable possibility, not a failure to
   hide), fall back to treating power-law as a separate injected forward-model transform, built and
   tested the way hysteresis will be (Day 14). Either way, RQ3's actual deliverable is now stated
   concretely: an explicit operating-envelope boundary (a function or lookup table — "static
   correction valid below distortion magnitude X / hysteresis magnitude Y, unreliable above it") —
   a falsifiable output, not just "did accuracy hold up, yes or no."
4. **Cost and robustness, defined as explicit formulas** (see Metrics section above) rather than
   left as undefined placeholders a reader would have to guess at.
5. **Bonferroni correction, fully specified** (family size, scope, resulting alpha — see Statistical
   protocol section above) rather than named without parameters.

**One council recommendation deliberately NOT actioned today, and why**: the single highest-leverage
suggestion — run a small real pilot (even N=1 seed, coarse grid, all 7 methods) to empirically
calibrate the two guessed axes before finalizing anything — cannot honestly be done on Day 6, since
none of the 7 methods exist as code yet (Days 15-20 build them). Silently skipping this would be
exactly the kind of thing this document exists to prevent. **Committing here instead**: this exact
pilot check is scheduled for Day 15, immediately once the first 2 methods (raw atan2, Kasa) exist,
expanding to all 7 as they're built through Day 20 — before the Day 27 main campaign launches, not
after. If that pilot suggests the quadrature-error or DC-offset grids are implausible, this document
will be revised again, dated and reasoned, at that point.

## What counts as deviating from this plan

Any change to the parameter ranges, metrics, or statistical protocol after this point must be
recorded as an explicit, dated deviation in this document (not silently edited in), with the reason
stated — exactly as the Revision History section above was itself just handled.

