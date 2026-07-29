# Day 36 — the documentation-drift audit finds seven real issues, including two in this week's own work

Motivated by the Weeks 1-2 audit's own council review, which named this exact gap: nothing in this
project's process actually searches for a preregistered term or number quietly drifting in prose.
Five agents dispatched in parallel, each independently auditing a disjoint slice of `docs/` and
`notes/` against the actual current code, config, and result data.

## Seven real findings, not the zero a project this careful might expect

**The most serious**: `src/hoqi_bench/harmonics.py`'s own module docstring — actual source code,
not a planning document — stated "99 of the main campaign's 359 conditions have `arc_fraction <
1.0`." Recomputed from the live config: **88**. Fixed at the source, and permanently guarded with a
new test (`test_sub_fringe_condition_count_is_consistent_across_source_and_docs`,
`tests/test_docs_consistency.py`) matching this project's existing total_runs/n_seeds pattern.

**A correction that didn't fully propagate**: `STRUCTURAL_ADVANTAGE_PREDICTIONS.md`'s own D1
deviation (Day 21) removed Taubin from the Category 1 tautological classification — but a later
"How this document is used" section's example caption still listed Taubin among the construction-
check methods. D1 fixed the reasoning; a restatement of the conclusion elsewhere in the same
document was missed at the time.

**Two stale implementation conditionals**: `notes/contribution_claim.md` and `notes/taubin_1991.md`
both still hedged Köning and Taubin's implementation as "if time allows" / "if in fact implemented,"
written before Week 3 built all seven methods. Corrected to state plainly what's true now.

**Two overclaims from THIS WEEK's own work — the most important finding of the day.**
`docs/WEEK5_PREFLIGHT_AUDIT.md` and `docs/RQ3_RQ6_ANALYSIS.md` both stated a blended "33.9×"
hysteresis dynamic-range figure for "the four conic fitters"; recomputing directly, three are at
33.8-33.9× but Heydemann alone is 17.9×. And `docs/RQ1_RQ2_ANALYSIS.md`'s RQ1c section claimed
`raw_atan2`'s cyclic error is "an order of magnitude above every corrected method" on all three
classic axes; checked against the raw CSV, that's true on two axes but **false on `dc_offset`**,
where `raw_atan2` is actually lower than five of the six corrected methods. Neither error was caught
by the `llm-council` review that already ran on the RQ3-RQ6 document this same week — a dedicated,
independent re-verification against raw data found what a targeted overclaiming review did not.
Worth naming plainly: this is the argument for Task 9 existing as its own separate step, not
something folded into each day's own self-check.

## Deferred to Task 10, not patched today

README.md is significantly stale — a status line claiming "no campaign data exists yet" when Week 5
is fully complete, a test count off by nearly half (136 stated vs. 251 actual, via
`pytest --collect-only -q`), and setup instructions that don't mention `uv`, despite Day 35's clean-
clone check finding `python -m venv` fails outright on this machine. Recorded in full in
`docs/WEEK6_DOC_AUDIT.md` rather than patched piecemeal today, since Task 10 (tomorrow) is the
dedicated rewrite and a partial fix now would just be redone.

## What checked out clean

The majority of the ~15 audited files matched the current code exactly: `PREREGISTRATION.md`,
`PREREGISTRATION_v1_superseded.md`, `experimental_design.md` (every axis range, grid cardinality,
seed count, and total-run figure verified against `configs/main_campaign.toml`), `WEEK3_METHOD_
CONTRACT.md`, `WEEK3_REVIEW.md` (every named threshold constant matched current source), and
`WEEK1-2_AUDIT.md`/`WEEK3-4_PLAN.md` (historical claims correctly scoped, nothing evergreen-framed
found false). `WEEK4_EXECUTION_PLAN.md`'s two stale references (the same "99" count, and
instructions to use the now-superseded `fit_by_name` rather than `timed_fit_by_name`) were left in
the document's own body as a historical record, with a single dated correction note added at the
top rather than editing history throughout.

## Verification

249 passed, 2 xfailed (251 collected). `ruff check`, `ruff format --check`, `mypy --strict` all
clean.

## What's next

Task 10 (Day 37): the README rewrite, now with a complete, verified list of exactly what's wrong
with it from today's audit rather than having to rediscover the gaps from scratch.
