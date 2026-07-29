# RQ1 + RQ2 Analysis — DRAFT INTERPRETATION

**Status: DRAFT. This is Claude's interpretation of Day 27's campaign results, for Nishi to revise,
not rubber-stamp.** Written, then reviewed adversarially via `llm-council` (5 advisors, hunting
specifically for overclaiming), then revised in place against that review before being presented
here — this is the post-review version, not the first draft (see `docs/journal/day28.md` for the
full council transcript and exactly what changed and why). It is still a draft: the council catches
overclaiming, it does not replace Nishi's own judgment about what this benchmark should claim.

**What the council changed, in one line each** (full reasoning inline at each point below): RQ1b's
"not implied by anything already known, required the campaign to see" claim was cut — 4 of 5
reviewers independently caught that only the specific *threshold and magnitude* were genuinely
empirical, not the qualitative direction, which is a known conic-vs-circle-fitting fact; the RQ1b
table now flags that Halir & Flusser's conditional mean (survivors only) isn't directly comparable
to fully-unconditioned means; RQ2's Köning aside no longer implies its iteration cap is a verified
cause, and now notes this is one anomaly among 14 checks; RQ1c's cyclic-error explanation is now
explicitly labeled post-hoc and unverified, not established; the significance section now says
plainly that 11-significant-figure "significant" results are likely partly numerical-precision
artifacts, not real method differences, applied as a consistent standard rather than only where
convenient.

**Data:** `results/main_campaign_summary.csv` (2,513 rows) and `results/rq1_*.csv`/
`results/rq2_*.csv` (produced by `scripts/rq1_rq2_analysis.py`), over the full 125,650-fit main
campaign (Day 27). All numbers below are computed, not estimated — reproduce with
`python scripts/rq1_rq2_analysis.py` against `results/raw/`.

**Binding framing rules applied throughout** (per `docs/WEEK3-4_PLAN.md` Day 28 and
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`):
1. A result on `amplitude_ratio`, `quadrature_error_rad`, or `dc_offset` matching the Category 1
   (tautological) prediction is captioned as a **construction check**, never a ranking finding.
2. Every error number is reported **with** its failure rate, gross-error rate, and unusable rate —
   never alone (R1, `docs/WEEK3_REVIEW.md`).
3. Cyclic-error amplitudes are reported only where `well_conditioned AND NOT failed`.
4. Statistical significance (Day 25's paired, Bonferroni-corrected t-tests) is reported
   **alongside**, not instead of, whether the actual magnitude is practically meaningful.

---

## RQ1a — The three classic axes: a construction check, not a finding

On `amplitude_ratio`, `quadrature_error_rad`, and `dc_offset`, Heydemann, Halir & Flusser,
Fitzgibbon, and Köning are all general-conic fitters, and the forward model's distortion on these
axes *is* a general conic (`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` §0.1). All four recover
displacement to 1.6–2.0 × 10⁻¹¹ m at baseline and stay within a factor of ~200 of that even at the
worst preregistered grid point — differences between them are statistically significant (18–20 of
21 pairwise comparisons per condition, Bonferroni-corrected) but the entire spread sits five to six
orders of magnitude below any real interferometric noise floor
(`reference_scale.INSTRUMENT_NOISE_FLOOR_M` = 1×10⁻¹³ m is the nearest physical reference, and even
that is two orders above these numbers). **This is exactly what the forward model guarantees by
construction. It is not evidence that any one of these four methods is generally superior.**

Kasa and Taubin — circle-only fits — track `raw_atan2` closely on `amplitude_ratio` and
`quadrature_error_rad` (no free parameter for either distortion: 3.09×10⁻⁹ m vs. `raw_atan2`'s
3.24×10⁻⁹ m at the amplitude_ratio baseline) but separate clearly on `dc_offset` (3.61×10⁻⁹ m vs.
`raw_atan2`'s 1.01×10⁻⁸ m at the worst grid point — a circle has a center, `raw_atan2` assumes one
that doesn't move). **This is Category 2, not Category 1 — but the distinction needs stating
explicitly, not just asserted, since a skeptical reader could reasonably call it tautological too**
(council review, `docs/journal/day28.md`): Category 1 means a method's correction model
*algebraically is* the forward model's exact injected functional form (an ellipse); Category 2 means
a property of the method's general estimation structure that holds regardless of which specific
distortion is present. Kasa/Taubin correcting `dc_offset` is Category 2 by that test — a
circle-center estimate corrects any translation, not specifically *this* forward model's — but it is
worth naming why that test, not "genuine" vs. "tautological" as a bare label, is what separates it
from the classic-axis claim above.

## RQ1b — The practically important finding: reliability inverts at extreme `arc_fraction`

At `arc_fraction = 0.02` (a 0.72° arc — the shortest the campaign sweeps), reliability inverts
completely relative to the classic axes:

| method | usable? | unusable rate | mean displacement RMSE, among usable seeds |
|---|---|---|---|
| **Taubin** | ✅ | 0% | **3.24×10⁻¹⁰ m** (all 50 seeds) |
| **Kasa** | ✅ | 0% | 9.46×10⁻¹⁰ m (all 50 seeds) |
| raw_atan2 | ✅ | 0% | 6.51×10⁻⁹ m (all 50 seeds) |
| Halir & Flusser | ⚠️ | 54% | 7.32×10⁻⁹ m (only the 46% / ~23 seeds that succeeded) |
| Fitzgibbon | ❌ | 100% | — (every fit is gross error) |
| Köning | ❌ | 100% | — (88% failed, 12% gross) |
| Heydemann | ❌ | 100% | — (100% self-reported failure) |

**A caveat the first draft of this table did not carry (council review flagged it):** Halir &
Flusser's 7.32×10⁻⁹ m is *not* directly comparable to `raw_atan2`'s 6.51×10⁻⁹ m — one is computed
over all 50 seeds, the other over only the ~23 that happened to succeed. If Halir & Flusser's
failures are not random with respect to difficulty (plausible: harder noise draws are more likely
to push an already-marginal fit into failure), the reported 7.32×10⁻⁹ m is a survivor-conditioned
number and likely *understates* how bad this method actually is at this condition, not overstates
it. Read the 54%/46% split itself, not the conditional mean, as the primary signal for this row.

Per `aggregate.is_rankable`'s all-or-nothing rule, this condition is not formally rankable — 4 of 7
methods exceed the 20% unusable-rate threshold — but that is a methods footnote about this
benchmark's own ranking protocol, not a statement about whether the underlying reliability rates are
real or usable. They are the finding.

**What is and is not new here (corrected after council review — the first draft overclaimed this
point directly).** That a 3-parameter circle fit needs less of a curve to stay well-conditioned
than a 5-parameter general-conic fit is a textbook fact about conic fitting, not a discovery this
campaign made — `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` already predicted the *qualitative
direction* of this effect before Day 15 wrote a single method. Four independent reviewers
(`docs/journal/day28.md`) caught that an earlier draft's claim — "not implied by anything already
known about the forward model, required running the actual campaign to see" — overstated this.
**What the campaign actually established, and what genuinely required running it, is the specific
threshold and magnitude**: that the crossover happens by `arc_fraction ≈ 0.02` specifically, that
it is a *complete* inversion (not a narrowing of the gap), and that it takes down not just the
weakest general-conic fitter but all four, including the two (Fitzgibbon, Köning) whose failure
modes are structurally distinct from each other. Framed as a decision rule rather than a discovery:
**if a real interferometer setup cannot guarantee more than a few percent of a fringe cycle per
fit, none of the four methods that dominate on every classic-distortion axis are usable, and the
two circle-only methods this benchmark's own preregistration predicted would be more robust are
also the two that are, in fact, still accurate.**

## RQ1c — Cyclic error: a coherent, physically-explicable pattern, not noise

At the classic-axis baselines (well-conditioned per `harmonics.HARMONIC_CONDITIONING_LIMIT`, and
filtered to non-failed fits per the D2 aggregation caveat):

- `raw_atan2` carries first-order cyclic error an order of magnitude above every corrected method
  **on `amplitude_ratio` and `quadrature_error_rad`** (0.027–0.028 rad vs. 5.6×10⁻⁵–1.28×10⁻⁴ rad,
  corrected here Week 6 doc audit, 2026-07-29 — the upper end of the corrected-method range was
  previously overstated as 0.0003, roughly 2.3× the actual maximum) — expected, since it corrects
  nothing. **This does NOT hold on `dc_offset`**: there, `raw_atan2` (7.5×10⁻⁵ rad) is actually
  *lower* than five of the six corrected methods (1.16×10⁻⁴–1.18×10⁻⁴ rad), only above Heydemann
  (5.9×10⁻⁵ rad) — the "order of magnitude above every corrected method" claim was previously
  stated as if it held on all three classic axes uniformly; it does not.
- **Kasa and Taubin carry SECOND-order cyclic error roughly two orders of magnitude above their own
  first-order error** (0.048–0.069 rad second-order vs. 0.0001 rad first-order), while the four
  general-conic fitters show no such asymmetry.

**Provenance of the explanation below, stated explicitly per council review**: this pattern is
**not** named in `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` — it was constructed after seeing these
specific numbers, not predicted in advance. It is offered as a plausible mechanistic account, at the
same epistemic standard as RQ2's unresolved Köning finding below, not a confirmed one: fitting a
circle to genuinely elliptical data leaves a residual that is geometrically a second-harmonic
distortion (an ellipse's deviation from its best-fit circle repeats twice per cycle, not once) — the
same underlying fact that makes Kasa/Taubin structurally unable to correct `amplitude_ratio`/
`quadrature_error_rad`, now visible as a specific harmonic signature rather than only an aggregate
RMSE number. If this holds up under a proper derivation (not done here), it would be a useful
practical diagnostic — a real interferometer showing a dominant second-order cyclic error, with
little first-order component, is a signature consistent with "a circle was fit to elliptical data,"
distinguishable from `raw_atan2`'s uncorrected first-order-dominant signature. **Flagged as a
plausible interpretation worth a real derivation, not stated as established.**

## RQ2 — Breakdown thresholds (preregistered axes: `amplitude_ratio`, `arc_fraction`)

| method | `amplitude_ratio` | `arc_fraction` |
|---|---|---|
| Heydemann | no breakdown in range | no breakdown in range |
| Halir & Flusser | no breakdown in range | 0.171 |
| Fitzgibbon | no breakdown in range | 0.171 |
| Köning | **1.495** (flagged below) | 0.229 |
| Kasa | 1.029 | broken at start |
| Taubin | 1.029 | broken at start |
| raw_atan2 | broken at start | broken at start |

**Flagged as surprising, not silently smoothed over:** Köning breaks down on `amplitude_ratio` at
1.495 — inside the grid, at its second-to-last point — while the three other conic fitters never
do across the full preregistered range. Köning is one of the five methods
`STRUCTURAL_ADVANTAGE_PREDICTIONS.md` predicts should be near-ceiling on this axis by construction,
so a breakdown at all is unexpected. **Cause unknown — not investigated further in this pass, and
no specific mechanism is asserted here** (council review: an earlier draft's aside about the
iteration cap read as more established than it was, since it cited when that cap was validated for
a *different* metric on a different day as if that were evidence for *this* observation, which it
is not). **Also worth weighing before treating this as a localized phenomenon at all**: this is one
anomaly surfaced out of 14 breakdown-threshold checks (7 methods × 2 axes) across a 359-condition
campaign — some rate of single-point surprises is an ordinary property of running many checks, not
necessarily evidence of one specific cause. **Left for Nishi's judgment**: whether this is worth a
follow-up (e.g., rerunning Köning at `amplitude_ratio` values near 1.4–1.5 with a raised iteration
cap and checking whether the breakdown persists) or an accepted, undiagnosed limitation of the
labeled approximation `koning_wimmer_witkovsky.py` already declares itself to be.

On `arc_fraction`, `raw_atan2`, Kasa, and Taubin are `broken_at_start` — already above the fixed
physical tolerance at `arc_fraction=1.0`, the easiest point on this specific axis. This is not a
contradiction of RQ1b above: it reflects the campaign's OFAT design, where sweeping `arc_fraction`
holds `amplitude_ratio=1.1` and `quadrature_error_rad=0.1` fixed at their own non-zero baseline
values, which these three structurally-uncorrecting methods can never get below tolerance on,
regardless of how much arc is visible.

## Cost — RQ1's fourth dimension, added Day 31 (previously missing entirely)

**Not part of the original draft.** RQ1 was preregistered to compare methods on "displacement
accuracy, cyclic-error harmonics, robustness, **and cost**," but `runner.py` never wired the timing
instrumentation up (`docs/WEEK5_PREFLIGHT_AUDIT.md` finding P3) — `runtime_s` was null in 100% of
the main campaign's 125,650 rows, and this document's first draft omitted cost entirely without
flagging the gap. Fixed Day 31 (`src/hoqi_bench/methods/__init__.py`'s new `timed_fit_by_name`); see
`docs/WEEK3_METHOD_CONTRACT.md`'s Day 29 defect report for the fix itself.

**Checked before adding this section, not assumed**: does any existing claim above depend on cost or
change once cost is real? No — grepped the full document; every prior mention of "iteration" refers
to Köning's convergence behavior (RQ2), never to timing. This section is purely additive.

**Measurement design.** The main campaign's own `runtime_s` values (now populated) are NOT used as
the authoritative cost figures — they were recorded under `ProcessPoolExecutor` contention, which
measures scheduler behavior as much as algorithm cost. Instead: a **separate serial, single-worker
pass** (`scripts/rq1_cost_measurement.py`), BLAS pinned to 1 thread, over 9 of the 359 preregistered
conditions — the full baseline (`axis:amplitude_ratio=1.1`, the one condition where every axis sits
at its own baseline value) plus the last configured value of each of the 8 OFAT axes, selected
structurally (by config list position) before any cost number was looked at.

**At baseline, cost spans ~53x, and the ordering is NOT the same as the accuracy ordering above:**

| method | mean (µs) | std (µs) | × raw_atan2 |
|---|---|---|---|
| raw_atan2 | 3.17 | 1.27 | 1.0× |
| kasa | 21.31 | 4.34 | 6.7× |
| heydemann | 32.96 | 4.36 | 10.4× |
| halir_flusser | 74.00 | 17.74 | 23.3× |
| taubin | 106.22 | 53.91 | 33.5× |
| fitzgibbon | 128.79 | 66.46 | 40.6× |
| koning_wimmer_witkovsky | 167.99 | 28.24 | 53.0× |

Kasa and Taubin are the cheapest correction-capable methods (matching their simpler 3-parameter
circle fit vs. the 5-parameter general-conic fitters) — the same circle/ellipse split
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` already uses to explain their accuracy profile on
`arc_fraction`/`samples_per_fit`, now showing up as a genuinely separate cost advantage too, not
merely a robustness one.

**The real finding: Köning's cost is dramatically, non-uniformly sensitive to `samples_per_fit`.**
At the baseline (N=60), Köning is the most expensive method at 53× the floor — expensive, but the
same order of magnitude as Fitzgibbon. At `samples_per_fit=1000`, Köning costs **19,470 µs — a
116× increase over its own baseline** — while Kasa (a representative non-iterative method) only
increases 2.0× over the same N change. This is not surprising in kind (Köning is the one iterative,
errors-in-variables method, and each of its iterations does linear algebra that scales with N,
unlike a single-shot closed-form solve) but the *magnitude* of the gap was not measured before this
pass. **Practical consequence**: `docs/PREREGISTRATION.md`'s RQ6 (an N-vs-noise design chart, being
answered separately as a supplementary result per deviation D6) should report Köning's cost
alongside any accuracy recommendation at high N — a chart that recommends more samples for accuracy
without also showing this cost curve would be incomplete for a practitioner deciding whether to
actually run Köning at large N.

**The 116× is per-iteration cost, not iteration count — checked directly, not left as an open
question, since the data needed was already in hand.** Köning's own `n_iter_mean` at
`samples_per_fit=1000` is **2.64 — slightly LOWER than its 3.00-iteration baseline**, while
per-iteration cost rises from ~56 µs/iteration at baseline to **~7,375 µs/iteration at N=1000** (a
~130× increase). So the practical N-vs-cost relationship for Köning is driven entirely by each
iteration doing more work at larger N (consistent with an errors-in-variables solve whose per-step
linear algebra scales with sample count), not by needing more iterations to converge — a real,
checked distinction, not an assumption.

## What is statistically significant vs. practically meaningful

Pairwise significance (Bonferroni-corrected paired t-test, Day 25) found 13–20 of 21 comparisons
significant at nearly every condition tested, including the classic-axis baselines where every
conic fitter agrees to 11 significant figures. **This is expected, not a red flag, but it also means
those specific "significant" results are not meaningfully comparisons of the METHODS at that
precision** (council review): agreement to 11 significant figures on a double-precision computation
is close enough to machine epsilon that a paired t-test there is at least partly detecting
floating-point/summation-order artifacts between implementations, not a real difference in
estimation accuracy. 50 tightly paired seeds and near-zero within-method variance make even a
picometer-scale (or smaller) difference statistically distinguishable regardless of its cause.
Significance here answers "did I measure a difference," not "does this difference reflect the
methods actually behaving differently, or does it matter" — applied consistently in both
directions: the practical answer for the classic axes is that these particular significant results
do not reflect a meaningful method difference (the entire spread is below any physical noise floor
this benchmark defines, and likely partly numerical-precision noise); the practical answer for
`arc_fraction=0.02` is the opposite — that result is not from a significance test at all (most of
the affected methods are excluded from ranking entirely by their own failure rates), and it matters
because the magnitude is the difference between a usable and a completely unusable result, not
because a p-value says so.

## Left for Nishi

- Whether Köning's `amplitude_ratio=1.495` breakdown warrants a follow-up investigation, given it
  could be a real, localized effect or one anomaly among 14 checks that base rates alone predict
  will occasionally surface.
- Whether the `arc_fraction=0.02` finding should be the headline result in any external write-up
  of this benchmark — as a **decision rule with an empirically-established threshold**, per the
  corrected framing above, not as "a discovery unknowable in advance."
- Whether RQ1c's second-harmonic cyclic-error explanation is worth a real derivation (it is
  currently a plausible, post-hoc, unverified account) before it is presented anywhere as a
  practical diagnostic.
- Whether RQ3–RQ5 (hysteresis, power-law, Poisson-vs-Gaussian noise — all Category 3, "genuinely
  open" per `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`) warrant the same depth of analysis as a
  Week 5/6 follow-up; this document covers RQ1/RQ2 only, per Day 28's scope.
