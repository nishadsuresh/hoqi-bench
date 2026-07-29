# RQ3-RQ6 Analysis — DRAFT INTERPRETATION

**Status: DRAFT. This is Claude's interpretation of Week 5's results, for Nishi to revise, not
rubber-stamp.** Written, then reviewed adversarially (hunting specifically for overclaiming and
defects spun as findings), then revised against that review before being presented here — matching
`docs/RQ1_RQ2_ANALYSIS.md`'s own process on Day 28.

**What the review changed, in one line each** (full reasoning inline at each point below): a
"three independent analyses converge" claim about `samples_per_fit` was caught as fabricated — one
of the three cited analyses (RQ3 part 1) never actually measures `samples_per_fit` at all, and a
second citation (RQ4) was simply wrong; corrected to the real two-way convergence (the pre-flight
audit's own P2 finding + RQ6), stated at that strength. The "Established" summary section
originally stated both preregistered and supplementary findings with identical, undifferentiated
confidence — split into separate paragraphs by evidentiary source, per this document's own framing
rules 5/6. RQ3 part 1's `quadrature_error_rad` exponent now states explicitly which 3 methods
produced the clean fits (the uncorrected ones, not the tautologically-favored general-conic
fitters) rather than leaving that ambiguous. Heydemann's moment-estimator mechanism is now stated
as "consistent with," not confirmed by, the observed pattern.

**Binding framing rules applied throughout** (carried from Day 28, extended for Week 5):
1. A result matching a Category 1 (tautological) prediction is captioned as a construction check,
   never a ranking finding.
2. Every error number is reported with its failure rate, gross-error rate, and unusable rate.
3. Cyclic-error amplitudes only where `well_conditioned AND NOT failed`.
4. Statistical significance reported alongside, never instead of, practical magnitude.
5. **Every preregistered-vs-supplementary result is labeled as such in the table itself**, not
   only in surrounding prose.
6. **RQ3's hysteresis half and RQ6 are reported as unanswered by the preregistered campaign**
   (deviations D5, D6), with supplementary results presented separately and clearly subordinate.

---

## RQ3, part 1 — power-law characterization: mostly no clean relationship, and where one exists,
it doesn't match Lehmann's exponent

**[PREREGISTERED]** Fit across 4 monotonic-distortion axes × 7 methods (28 fits total,
`scripts/rq3_power_law_analysis.py`, Day 30). Only **7 of 28** clear the pre-committed r²≥0.90
honesty floor (calibrated against 9,000 synthetic trials before any real number was seen). Where a
clean fit exists, the exponent clusters near **1** (`quadrature_error_rad`: 0.67–0.71;
`hysteresis_magnitude`/radial-inflation: 0.85–0.92) — not near Lehmann et al. 2025's reported ~3.
On `amplitude_ratio` and `dc_offset`, **no method** produces a clean power law at all, and exponents
vary by up to 7× across methods on the same axis, which is itself evidence against a shared
mechanism rather than evidence of one merely being hard to see.

**Honest reading**: this project's own sweep data, on these axes, does not reproduce Lehmann's
power-of-3 finding. This is not a failure of measurement — the comparison was never expected to
match directly (Lehmann's exponent describes residual error vs. *motion range*, a different axis
than this project's *distortion magnitude*, a distinction Day 13 flagged before any code was
written). **Left for Nishi**: whether 21/28 sub-floor fits triggers the documented fallback
(model power-law as an injected transform) or whether the null result stands as reported.

**Which methods cleared the floor matters, and is stated explicitly rather than left implicit**
(caught by `llm-council` review of this document, Day 35): on `quadrature_error_rad`, the 3 clean
fits belong to raw_atan2, Kasa, and Taubin — the three methods with **no structural correction** for
this distortion at all (`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` predicts they track raw_atan2's
uncorrected error here). This exponent therefore characterizes how *uncorrected* error scales with
distortion magnitude, not a construction-check artifact from the tautologically-favored general-conic
fitters — those four (Heydemann, Halir & Flusser, Fitzgibbon, Köning) all fell *below* the honesty
floor on this axis, so their fits are not among the 7 being described here at all.

## RQ3, part 2 — hysteresis direction-dependence: real, and not floor-masked everywhere

**[PREREGISTERED, radial inflation only]** The main campaign's `hysteresis_magnitude` axis measures
direction-**independent** radial inflation (deviation D5) — a real, non-conic distortion (33.9×
displacement-RMSE dynamic range for conic fitters), but not hysteresis.

**[SUPPLEMENTARY]** A bidirectional (triangle-wave) waveform, protocol committed before any code
(`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 1), actually exercises direction reversal.
**36 of 56 (condition, method) pairs exceed the pre-specified RMSE noise-floor criterion; 2 more
went from usable to fully unusable** (Heydemann, Köning at `hysteresis_magnitude=0.2` — a defect in
the analysis script's own significance check initially hid this by comparing against a NaN, fixed
before this number was trusted, Day 32). `raw_atan2` never shows a difference (0/8) — floor-masked
by its own uncorrected classic-axis error, not evidence of direction-insensitivity.

**This is a real, reportable finding, not the null result the protocol allowed for**: direction of
travel, not just magnitude, measurably affects several methods' displacement recovery under this
project's hysteresis model. Full mechanistic explanation (why direction matters for an
ellipse/circle fit specifically) is not derived here — flagged for future work, not asserted.

## RQ4 — Poisson vs. Gaussian noise: no ranking difference survives significance testing

**[PREREGISTERED, existing axes]** `photon_scale` (Poisson) and `noise_std` (Gaussian) were both
already swept independently. Comparing them required defining "equivalent noise," routed through
`llm-council` before any analysis code (`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 2).

**Primary [PREREGISTERED-DATA] analysis**: each axis's own internal ranking changes at 12 of 17
grid points relative to its own easiest point — expected, uninteresting on its own, and depends on
no cross-axis assumption.

**Secondary [PREREGISTERED-DATA, novel analysis] sensitivity matrix**: across three independent
matching rules (sigma, peak-SNR, Fisher information/CRB — the latter computed in closed form,
`fisher_information.py`), 4–7 of 9 matched pairs show an *apparent* ranking difference, but
**zero survive a proper bootstrap significance check under any of the three matching rules**. A
bug in the first version of this check (testing an irrelevant method's confidence interval instead
of the pair that actually swapped position) initially reported 100% "significant" — caught before
being trusted by inspecting exactly which methods diverged at each matched pair (never position 0),
fixed, and the honest result is the opposite of the buggy one.

**Reading**: at this campaign's swept range, no method-ranking difference between Poisson and
Gaussian noise is statistically distinguishable from ordinary seed-to-seed sampling noise, under
any of three independently-reasoned equivalence definitions. This is one of the protocol's own
pre-specified honest outcomes.

## RQ5 — phase-excursion regime: sub-fringe only, and Heydemann is an all-or-nothing case

**[PREREGISTERED]**, per deviation D7: `arc_fraction=1.0` is exactly one 2π cycle, not many
fringes — this analysis covers **only the sub-fringe regime** (a 0.72° arc up to one full cycle).
The many-fringe half of the original question was never in the preregistered grid.

**A finding distinct from RQ1b's single-point headline**: across the FULL swept range
(`scripts/rq5_analysis.py`, Day 35), **Heydemann's `unusable_rate` is exactly 1.0 at every
sub-fringe `arc_fraction` value and exactly 0.0 at `arc_fraction=1.0`** — verified across every
noise level in the `arc_x_noise` interaction grid too, not just the noiseless baseline. This is not
a gradual degradation the way the other methods show; it is a clean binary threshold, mechanistically
consistent with Heydemann's second-order-moment estimator needing a full revolution to compute an
unbiased center — a partial arc doesn't average to a noisier estimate of the right thing, it
averages to a systematically wrong thing.

**Also newly visible over the full range, not just the single `arc_fraction=0.02` point**: Halir &
Flusser's `unusable_rate` is **non-monotonic** — 0.54 at `arc_fraction=0.02`, rising to **1.00 at
0.05**, before falling back to 0.00 by 0.10. A reader looking only at the extreme point (as RQ1b
does) would miss that reliability gets briefly *worse* before it gets better.

**Cross-check**: every number at `arc_fraction=0.02` reproduces `docs/RQ1_RQ2_ANALYSIS.md`'s RQ1b
table exactly (Taubin 3.24×10⁻¹⁰ m, Kasa 9.46×10⁻¹⁰ m, raw_atan2 6.51×10⁻⁹ m, Halir & Flusser 54%
unusable, Fitzgibbon/Heydemann/Köning 100% unusable) — confirmed programmatically before writing
this section, not assumed consistent.

## RQ6 — N-vs-noise design chart: N mostly doesn't determine tolerance, method and noise do

**[SUPPLEMENTARY]**, per deviation D6: no `samples_per_fit x noise_std` interaction grid existed in
the preregistered campaign. Protocol committed before any code
(`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 3); 24,500 new fits, using only preregistered grid
values on both axes.

**Result**: of 70 (method, noise_std) combinations, only **3 produce an interior N crossing**
against the preregistered tolerance. 29 always meet tolerance regardless of N (the four
general-conic fitters at low noise); 38 never meet it regardless of N (Kasa/raw_atan2/Taubin at
every noise level — their error floor is the uncorrected classic distortion, not noise, so more
samples cannot help; and every method at the highest noise levels). Spot-checked one boundary case
(Heydemann's jump from "always fine" to "always broken" between `noise_std=0.06` and `0.08` with no
interior crossing) against the raw per-N values before trusting it — confirmed correct, not a bug.

**Reading, converging with one other finding — corrected here after adversarial review caught a
citation error, not three as an earlier draft of this document claimed.** RQ3 part 1's power-law
axes are `amplitude_ratio`, `quadrature_error_rad`, `dc_offset`, and `hysteresis_magnitude` —
`samples_per_fit` was never among them, and RQ4's within-axis analysis covers only `photon_scale`
and `noise_std`; neither actually says anything about `samples_per_fit`. The real second data point
is the **pre-flight audit's own P2 finding** (`docs/WEEK5_PREFLIGHT_AUDIT.md`,
`docs/PREREGISTRATION.md` deviation D6): at zero noise, a 50× increase in `samples_per_fit` changes
error by at most 1.10×, flat to 4 significant figures for 3 of 7 methods. Together: `samples_per_fit`
has far less influence over whether a method clears the preregistered tolerance than which method is
used or how much noise is present, at zero noise (the audit's finding) and across the full noise
range (this chart's finding). **Two independent checks, not three — stated at that strength, not
inflated.**

**Practical caveat, from `docs/RQ1_RQ2_ANALYSIS.md`'s Day 31 cost addition**: Köning's cost scales
116× from baseline to `samples_per_fit=1000` (driven by per-iteration cost, not iteration count).
Any accuracy-only reading of this chart that recommends high N for Köning should be paired with that
cost fact, not read in isolation.

## What is and is not established, stated plainly

**Established from PREREGISTERED data**: Heydemann requires a full revolution as a hard threshold,
not a soft degradation (RQ5) — the underlying moment-estimator mechanism offered as an explanation
is stated as *consistent with* the observed pattern, not confirmed by a derivation, and should be
read as a plausible account, not a settled fact; `samples_per_fit` is a weaker lever than method
choice or noise level, corroborated by two independent checks — the pre-flight audit's zero-noise
finding and RQ6's full-range design chart (not three, per the correction above).

**Established from SUPPLEMENTARY data only, reported subordinate to the preregistered results
above**: hysteresis direction-of-travel matters for several methods (RQ3 part 2) — this experiment
was not part of the preregistered campaign, and its finding carries the evidentiary weight of a
single, protocol-committed supplementary run, not a preregistered result.

**Not established, despite an initial appearance of a finding**: any Poisson-vs-Gaussian ranking
difference (RQ4 — the apparent differences did not survive proper significance testing); a clean
power-law relationship matching Lehmann's exponent on this project's own axes (RQ3 part 1 — most
fits don't even clear the honesty floor, and the ones that do land far from exponent 3).

## Left for Nishi

- Whether RQ3 part 1's mostly-sub-floor power-law fits should trigger the documented fallback
  (model power-law as an injected transform) or stand as a reported null result.
- Whether RQ3 part 2's hysteresis direction-dependence finding warrants a mechanistic derivation
  (why direction affects an ellipse/circle fit specifically) before being presented externally.
- Whether Heydemann's all-or-nothing arc-completeness threshold (RQ5) is worth a dedicated
  derivation, given how clean and total the effect is.
- Whether the "samples_per_fit is a weak lever" pattern across two independent checks (the
  pre-flight audit and RQ6's design chart) is worth naming as a headline finding of its own,
  alongside RQ1b's arc-fraction reliability inversion.
