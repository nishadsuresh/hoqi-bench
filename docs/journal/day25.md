# Day 25 — Statistics layer, and the ambiguity that needed a council to catch its own mistake

## What "implement exactly" actually required today

The preregistration fixes three procedures — bootstrap confidence intervals, a breakdown-threshold
detector, and a Bonferroni-corrected pairwise comparison — specifically so the analysis can't be
tuned after seeing results. The bootstrap CI and the Bonferroni constant were mechanical: the
preregistration states them precisely enough to implement directly (percentile-method bootstrap on
the mean; 7-choose-2 = 21 comparisons per condition, alpha = 0.05/21). Both passed their
hand-computed tests on the first attempt.

The breakdown-threshold sentence was different. It reads as precise — "smallest swept value where
mean error first exceeds 1% relative RMS error, via linear interpolation between grid points" —
but contains three real gaps: what "1% relative" is relative to, what "linear interpolation" means
on a log-spaced grid, and what "first exceeds" means when a curve isn't monotonic. Getting any of
these wrong doesn't crash anything. It produces a plausible, authoritative-looking number that
silently means something different from what a reader would assume.

## Why this went to `llm-council` instead of my own judgment

Per the Week 4 plan, this is exactly the kind of decision the council is for: hard to reverse once
the campaign runs, about *what a number means* rather than *how to write the code*, and expensive
to get wrong. Five advisors (Contrarian, First Principles, Expansionist, Outsider, Executor)
answered independently, then five more reviewed all five responses anonymously.

## The council caught a mistake in my own framing, and the peer review caught the right way to fix it

I'd told the council that fixing the denominator to a constant was the same kind of move Day 21's
cross-validation gate already made — implying precedent supported it. The Contrarian (rated
strongest by all 5 peer reviews) checked this instead of accepting it: Day 21's actual denominator
was `arc_fraction × 2π`, which *varies* with `arc_fraction` — condition-*dependent*. A fixed
constant is condition-*independent*. Those are opposite properties. I had cited a precedent for a
decision the precedent didn't literally support.

That could have gone two ways — either the majority's conclusion (a fixed constant) was wrong, or
my justification for it was wrong but the conclusion still stood. Peer review sorted this out
precisely: the actual principle Day 21 established wasn't "the denominator must be fixed," it was
**anti-circularity** — the denominator must never be a function of the noisy, fitted quantity the
metric is scoring. `arc_fraction × 2π` is condition-dependent but not self-referential (it's a
known nominal from the condition's own config, fixed before any fit runs). The fixed physical
constant satisfies the same principle even more strongly. Both are legitimate applications of one
deeper rule; my shorthand to the council just conflated two different properties ("fixed" and
"non-circular") that happen to coincide in the fixed-constant case.

I checked the Contrarian's other challenge directly rather than taking it on faith: was
`PREREGISTERED_TOLERANCE_M` already hard-coded before this "resolution," making it theater rather
than a real decision? `git log --follow` shows it was introduced in Day 22, for a *different*
purpose (classifying displacement error), before any breakdown-threshold code existed. Reusing it
here is a genuine choice, not a rubber stamp.

## The gap nobody named until the council found it independently, five times

All five peer reviews — independently — flagged the same missing case: what happens when a method
*never* crosses tolerance across the whole swept range? The original three ambiguities only
handled the mirror-image case (broken at the very first grid point, which is what `raw_atan2`
does). But per `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`, never-breaking-down is the *expected*
outcome for the near-ceiling conic fitters on these axes — probably the more common case, not the
edge case. A `float | None` return type can't tell "broken at start," "never breaks down," and "a
real crossing that happens to land on the first grid point" apart from each other. That's not a
theoretical concern — those three cases need to render as three different things in a results
table.

Fixed by scrapping the `float | None` interface entirely for a three-outcome
`BreakdownThreshold(value, status)`, `status` one of `"found"`, `"broken_at_start"`, or
`"no_breakdown_in_range"`. I'd already written a test asserting the old, wrong interface (`==
1.0` for the broken-at-start case) before running the council — caught it and rewrote that test
before implementing, rather than implementing to satisfy a test I now knew was wrong.

## What the council correctly declined to resolve

Three of five reviews raised the same limitation and none of the five advisors tried to solve it:
the interpolated crossing point has no uncertainty quantification. It's estimated from noisy
per-condition means on a finite grid, and noise near the threshold could shift which grid point
registers as "first." Not implemented today — recorded as an open limitation in the preregistration
deviation, for Nishi to decide whether it's in scope for Week 4 or a later refinement. The hard
rule (`docs/WEEK3-4_PLAN.md` Day 25) is that a statistical test not preregistered gets flagged, not
silently added, and this applies even to a limitation the council itself surfaced.

## A fourth piece not covered by the three named ambiguities: which comparison test

The Statistical protocol names Bonferroni correction but defers "full detail" on the underlying
test to today. `docs/PREREGISTRATION.md`'s own v2 seed-pairing decision settles it without needing
the council: every method sees the identical noise realization at a given `(condition,
seed_index)`, specifically to remove shared-noise variance from method-vs-method comparisons. An
*unpaired* t-test would throw away exactly that engineering investment. Used
`scipy.stats.ttest_rel` (paired) on same-seed-index differences, verified against a hand-computed
manual t-statistic before trusting scipy's result, and a seed where either method has a NaN
(Week 3's fit-failure contract) excluded from that specific pair's comparison — one pair's missing
seed doesn't invalidate a different pair that didn't share the failure.

## Verified against real campaign data, not just synthetic tests

Ran the full 359-condition, 7-method campaign and fed real numbers through all three functions:
- `kasa`'s breakdown threshold on `amplitude_ratio` was found at 1.029 — makes sense, Kasa has no
  free parameter for amplitude imbalance and degrades almost immediately past the undistorted
  baseline.
- `raw_atan2` reports `"broken_at_start"` on the same axis — correct, since the campaign's
  baseline carries non-zero quadrature error and DC offset even at `amplitude_ratio=1.0`, and
  `raw_atan2` corrects neither.
- `heydemann` reports `"no_breakdown_in_range"` — the tautological, structurally-guaranteed
  near-ceiling result confirming the pipeline is correct, not a finding.
- Pairwise comparisons at a real condition (`quadrature_error_rad=0.3`): 18 of 21 method pairs
  significant, with p-values as small as 3.7e-173 where methods genuinely diverge by orders of
  magnitude on 50 tightly-paired seeds — the scale a paired test on this much data should produce.

## A second instance of the environment fragility Day 24 found

Running the full campaign and then immediately calling `scipy.stats.ttest_rel` in the *same*
process crashed with the same SIGFPE Day 24 hit when wrapping a campaign run in
`warnings.catch_warnings()`. Splitting into two separate processes — run the campaign via
`scripts/run_campaign.py`, then a fresh process reading the Parquet files back for statistics —
completed cleanly both times. This doesn't threaten the real pipeline: Day 27's campaign launch
and Day 28's analysis are already meant to be separate steps (the campaign writes to disk; analysis
reads it back later), so this fragility only bites an all-in-one script that does heavy linalg and
then more numpy work in one process. Logged, not chased further, matching Day 24's treatment of
the same underlying issue.

## What was verified before calling this done

12/12 new tests, including two hand-computed breakdown-threshold crossings (one linear, one
log-scale, both worked out on paper before running the code), a hand-computed paired t-test
checked against `scipy.stats.ttest_rel` independently before trusting either, and the
joint-NaN-filtering behavior for pairwise comparisons. Full suite: 180 passed. Ruff and mypy clean.
Real campaign data behaves exactly as the structural predictions say it should, on all three
functions.
