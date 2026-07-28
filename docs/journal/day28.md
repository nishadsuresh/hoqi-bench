# Day 28 — RQ1/RQ2 analysis, and the council catching an overclaim in my own draft

## What was built

`scripts/rq1_rq2_analysis.py` computes four tables over the real 359-condition, 7-method, 50-seed
campaign, using only already-built and already-tested tools: `aggregate`'s reliability
classification, `statistics.bootstrap_ci`, `statistics.breakdown_threshold`,
`statistics.pairwise_comparisons`, and the raw table's `cyclic_*` columns.

- `results/rq1_ranking.csv` — per-axis, per-method displacement RMSE with 95% bootstrap CIs and
  reliability rates, at each axis's baseline and worst grid point.
- `results/rq1_pairwise_significance.csv` — Bonferroni-corrected paired t-tests among all 7
  methods at every axis's worst point.
- `results/rq2_breakdown_thresholds.csv` — breakdown thresholds for the two preregistered axes.
- `results/rq1_cyclic_error.csv` — cyclic-error amplitudes at the classic-axis baselines, filtered
  to well-conditioned, non-failed fits.

Every structural prediction confirmed on the real numbers, as expected from Day 27's quick-look:
the four general-conic fitters near-ceiling on the three classic axes, Kasa/Taubin tracking
`raw_atan2` on two of those axes but beating it on `dc_offset`, `raw_atan2` worst everywhere.

## The one genuinely new result, and the mistake I almost shipped with it

At `arc_fraction = 0.02` — the shortest arc the campaign sweeps — reliability inverts completely.
Taubin and Kasa (3-parameter circle fits) stay fully usable and highly accurate; all four
general-conic fitters, the ones tautologically guaranteed to dominate every classic axis, become
unusable (100%, 100%, 100%, and 54% unusable respectively). This is real, it's in the data, and it
matches `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`'s own arc-conditioning prediction.

I wrote the first draft calling this "the one result in this benchmark that is not implied by
anything already known about the forward model — it required running the actual campaign to see."
That sentence is where I sent the draft to `llm-council` before finalizing anything, per the Week 4
plan's specific instruction that this is exactly the situation the council exists for: "it will
attack overclaiming, which is exactly the failure mode Day 28 names."

It worked. Four of five independent advisors — Contrarian, First Principles, Outsider, and
Executor, using different words but converging on the identical substance — caught that the
sentence was false. That a 3-parameter circle fit needs less of a curve to stay well-conditioned
than a 5-parameter general conic fit is a textbook fact about conic fitting, not something this
campaign discovered. The First Principles reviewer put it most precisely: this is "structurally
tautological in exactly the same sense RQ1a's classic axes are, just not derived from the forward
model — it's derived from linear algebra," and the project's own tautological/genuine/open taxonomy
doesn't have an explicit slot for "known from general estimation theory, not this specific forward
model" — which is a real gap in how I'd been applying the framework, not just a wording problem in
one sentence.

What actually is new, and does require the campaign: not the direction of the effect, but its
specific threshold (`arc_fraction ≈ 0.02`) and its severity (a complete inversion, not a narrowing
of the gap, taking down all four dominant methods rather than just the weakest one). Rewrote the
section to make that distinction explicit and reframed the whole finding as a decision rule — "if
your setup can't guarantee more than a few percent of a fringe cycle, none of the methods that win
everywhere else are usable" — rather than a discovery, which is both more honest and, per the
Expansionist reviewer's point, actually more useful to a reader deciding which method to use.

## What else the council caught

- **Survivorship bias in my own headline table.** Halir & Flusser's mean error at the extreme
  condition was computed over only the ~46% of seeds that didn't fail, sitting right next to
  `raw_atan2`'s mean over all 50 seeds, with no flag that these are different populations — the
  exact R1 mistake this project has already been burned by once (Day 24), reappearing in a table I
  wrote myself three weeks after documenting why it's wrong. Caught by the Outsider reviewer
  reading the table cold. Fixed with an explicit caveat.
- **An unverified causal aside about Köning.** I'd written that its iteration cap "validated for a
  different metric on a different day" might explain a breakdown at `amplitude_ratio=1.495` —
  stating when the cap was validated right next to the speculation made the guess read like
  evidence. It wasn't. Cut the implied mechanism; added the honest "cause unknown," plus the
  Contrarian's base-rate point I'd missed entirely: one anomaly out of 14 breakdown checks across a
  359-condition campaign is not automatically a localized phenomenon requiring an explanation.
- **An untagged post-hoc story.** The Kasa/Taubin second-harmonic cyclic-error explanation is a
  plausible geometric argument, but I presented it with the same confidence as a pre-registered
  prediction. It wasn't pre-registered — it was constructed after seeing the actual numbers. Now
  labeled explicitly as unverified and worth a real derivation, at the same epistemic standard the
  original draft already (correctly) applied to the Köning caveat but not to this one.
- **An asymmetric significance standard.** I'd waved away "significant to 11 decimal places" on
  the classic axes as expected noise but hadn't applied the same scrutiny elsewhere, and hadn't
  named the sharper point the Outsider and Contrarian both raised: agreement that tight is close
  enough to machine epsilon that the test is partly detecting floating-point artifacts between
  implementations, not really comparing the methods at all.

## Why this went straight to revision instead of a second peer-review round

Four of five advisors converged independently on the same core finding, using different language —
that level of agreement is itself the signal a peer-review round exists to surface, and running a
second round would have mostly re-confirmed what was already unambiguous rather than produced new
information (unlike Day 25's breakdown-threshold council, where the Contrarian's citation critique
was a genuine surprise needing arbitration). Synthesized directly and revised `docs/
RQ1_RQ2_ANALYSIS.md` in place against all five responses.

## What's committed

`docs/RQ1_RQ2_ANALYSIS.md` (the revised interpretation, marked DRAFT for Nishi), `scripts/
rq1_rq2_analysis.py`, and the four `results/rq1_*.csv`/`rq2_*.csv` tables — small enough to review
in a diff, the actual analysis deliverable. This closes Week 4.
