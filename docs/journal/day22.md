# Day 22 — Core metrics, the survivorship-bias fix, and a reference scale that changes how everything reads

Three things today, and the third turned out to reframe the other two.

## The metric that is easy to get wrong in a way nothing catches

Displacement RMSE and peak absolute error are, on their face, trivial. The one real decision is
*where the wrapping happens*.

Recovered phase comes out of `atan2`, wrapped into (−π, π]. Ground-truth phase runs monotonically
from 0 up to `arc_fraction · 2π`. The obvious implementation — convert both to meters, subtract,
take the RMS — is wrong, and wrong in the worst way: it produces a plausible number. A sample whose
phase is recovered *perfectly* but which sits on the far side of the wrap boundary contributes a
displacement error of up to λ/2 ≈ 316 nm. Nothing raises; the method just looks bad.

So displacement error is derived *from* the wrapped phase error — wrap first, in phase, where
wrapping means something, then convert the already-correct error to meters. That ordering is the
whole content of `metrics.py`'s Day 22 additions, and it is what keeps every displacement number
compliant with the contract's §1 rather than merely adjacent to it.

The test for this uses true phase at π − 0.01 and recovered at −π + 0.01: two phases 0.02 rad apart.
Correct answer 1.007 pm; naive answer ~316 nm, a factor of ~314 larger. Every metric here has a
hand-computed reference with the arithmetic written out in the test, including the factor of 4 in
`φ = 4πx/λ` — the double-pass geometry, checked as a physical identity (2π of phase must be exactly
λ/2 of mirror motion) rather than as a formula, because a factor-of-2 slip there would silently
halve or double every number this benchmark ever reports.

## The survivorship-bias fix, and the hole in it

The Weeks 3-4 plan's adversarial review flagged this a week ago: a per-condition mean over
*surviving* runs compares different populations across methods whenever one method drops out
preferentially in the hard regimes — which are exactly the regimes that discriminate between
methods. Köning fails to converge preferentially at small `arc_fraction`; averaging its survivors
there against Fitzgibbon's full sample flatters whoever dropped out of the hardest cases.

The prescribed fix was: report convergence rate alongside every error, and don't rank methods on
any condition where any method's *failure rate* exceeds a threshold fixed before results exist.

Yesterday's Week 3 review found that this fix, implemented literally, has a hole big enough to drive
the whole campaign through. The `failed` flag records whether a method **detects** its own failure.
Fitzgibbon self-reports 0.00% failures and returns an unusable answer 13.48% of the time. Under
§0.4's literal wording it self-reports 0% forever, never trips the gate, and gets ranked
everywhere — while Heydemann, the one method honest enough to say when it cannot fit, self-reports
24.51% and gets excluded.

So the implemented gate keys on **unusable rate** = failure + gross error, not failure alone. A
method that is silently wrong is excluded on the same terms as one that says so. Recorded as a dated
deviation from §0.4's own wording rather than quietly implemented differently from the plan.

Two smaller decisions inside that, both of which could have gone the other way:

**The gate is all-or-nothing per condition.** If any method exceeds the threshold, *no* method is
ranked there. The tempting alternative — drop the offending method, rank the rest — leaves exactly
the flattering-by-attrition artifact the gate exists to prevent, just on the remaining pairs. A
non-rankable condition is still fully reported, with its reliability rates, which on a hard
condition are usually the most informative thing about it. It simply contributes no ordering.

**Failed seeds are NaN, never zero.** A failed seed that contributed `0.0` to a mean would make a
method look *better* the more often it failed. The test for this asserts the actual number — four
usable seeds at 1–4 nm plus six failures must give 2.5 nm, not 1.0 nm — because `0.0` is precisely
what a careless implementation produces and precisely what an equality-free test would miss.

The two thresholds are pre-committed. The 0.5 rad gross-error threshold carries its justification
from the review. The 20% ranking threshold was chosen on an external principle — above roughly 20%
attrition a complete-case analysis is conventionally treated as at serious risk of bias regardless
of mechanism — specifically *because* the campaign-wide rates had already been measured by the time
I wrote it, and a threshold picked after seeing the distribution can't be shown to be innocent of
it. Naming the anchor is the only way that pre-commitment means anything.

## The reference scale, which is the part that changes how the results read

The plan's Outsider advisor put it bluntly: without a physical reference scale, 125,650 runs produce
a ranking nobody can act on. "Method A achieves 0.3 mrad RMS" is not a result until someone can say
whether 0.3 mrad is comfortable, marginal, or useless.

Pulled the numbers from Lehmann et al. 2025 (arXiv:2511.04386) directly, since the project's own
reading notes recorded the paper's *mechanisms* but not its performance figures:

- Sensitivity in the **sub-100 fm** regime, at frequencies from 1 Hz up (abstract).
- Noise floors **below 10⁻¹³ m/√Hz** for stationary test masses (Section II.2).
- On-resonance motion "always less than 5 nm, and often even below 1 nm" (Section III.3).
- Sub-FSR working range 0.1–0.3 µm (Section IV.2).

Then the arithmetic that reframes the campaign. The preregistered breakdown tolerance is 1% relative
RMS error. At full arc coverage the record's full scale is one fringe, λ/2 = 316.4 nm. So the
preregistered tolerance is **3.16 nm of displacement error** — which is:

- **larger than the entire on-resonance motion** the reference paper measures (1–5 nm), and
- **~31,600×** the sub-100 fm sensitivity a HoQI exists to deliver.

A method that merely satisfies the preregistered tolerance is not usable for the application this
benchmark is about. That is not an argument for changing the tolerance — it was committed pre-data
and it stays. It is the reason every Week 4 result has to be placed on the physical scale *as well
as* against that tolerance, or the writeup will describe methods as "within tolerance" that are
useless in practice.

The interpretive bands are fixed now, before any result exists, each anchored to a measured quantity
rather than a round number: **negligible** (≤ the instrument's own noise floor — the method is not
the limiting factor, hardware is), **usable** (≤ 1% of the typical measured motion, 10 pm),
**marginal** (≤ the measured motion itself, 1 nm — the error is the size of the signal), and
**unusable** above that, a band which includes everything that merely meets the preregistered
tolerance.

## State at close

155 tests passing (136 before today), `ruff` and `mypy --strict` clean. Day 23 is cyclic-error
harmonics; Day 24 is the sweep runner, where determinism and resumability are the highest-risk
items in the week and where the BLAS thread pin stops being a nicety.

One note for Day 24, from the review: `aggregate.outcome_from_fit` is the single bridge from a
`FitResult` to a summarised seed. The runner should call it rather than building `SeedOutcome`
fields itself — the whole point of it existing is that the failed/NaN/gross-error rules get applied
in exactly one place, and Week 3 already demonstrated (three copies of one calling convention) how
quickly that stops being true when it is left to call sites.
