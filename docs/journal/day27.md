# Day 27 — Launching the main campaign

## Pre-flight, all three blocking checks passed

1. **Grid matches the preregistration.** `tests/test_docs_consistency.py` passed (total run count
   and seed count consistent between the config and prose). Went further than the automated check
   and cross-referenced the actual swept values by hand: `docs/experimental_design.md`'s stated
   grids for `amplitude_ratio`, `quadrature_error_rad`, `arc_fraction`, and `samples_per_fit` match
   `configs/main_campaign.toml` exactly, value for value.
2. **Pre-data documents committed before any result exists.** `docs/STRUCTURAL_ADVANTAGE_
   PREDICTIONS.md` was committed at Day 15, before any Week 3 method existed. `docs/
   PREREGISTRATION.md`'s v2 (and every dated deviation since) predates today. `results/raw/` has
   never been committed at any point in this repo's history — confirmed via `git log`, not assumed.
3. **Day 24's guarantees still hold.** `tests/test_runner.py` and `tests/test_reproducibility.py`:
   9/9 passed.

## Launch

```
config:     configs/main_campaign.toml
conditions: 359 (0 already complete)
methods:    7  seeds: 50
total fits: 125,650
done in 3.61s
```

Clean run, no crash, matching every prior measurement of this campaign's runtime this session
(consistently 2-4 seconds via the actual `scripts/run_campaign.py` entry point — the intermittent
SIGFPE this session hit repeatedly was always in ad hoc diagnostic scripts that combined heavy
linalg with extra work in the same process, never in the real entry point itself, which has now
run cleanly well over a dozen times).

## Quick-look, before trusting anything

Loaded the raw table: 125,650 rows, schema matches `RESULT_COLUMNS` exactly, no nulls in the
identifying columns. Failure/gross-error rates by method matched `docs/WEEK3_REVIEW.md`'s R1
numbers exactly (Fitzgibbon 0.00%/13.45% gross, Heydemann 24.51%/0.00%, Köning 15.71%/1.24%) —
the campaign reproduces what the review already found, not something new or different.

Then the four structural checks, computed the *correct* way this time — filtered to usable rows
(`not failed and not gross_error`) before taking any mean, per the Day 24 lesson:

- **`raw_atan2` is worst (or tied-worst) on every single axis** — amplitude_ratio, quadrature_error_rad,
  dc_offset, arc_fraction, noise_std. No exceptions.
- **The four conic fitters (Heydemann, Halir & Flusser, Fitzgibbon, Köning) are near-ceiling on the
  three classic axes** — differing from each other only in the 10th-12th significant digit on
  amplitude_ratio and quadrature_error_rad. This is the tautology
  (`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` §0.1): a construction check, not a finding.
- **Kasa and Taubin track `raw_atan2` closely on amplitude_ratio and quadrature_error_rad** (no free
  parameter for either distortion) **but clearly separate from it on dc_offset** — 3.6e-9 m vs.
  5.6e-9 m mean displacement RMSE, exactly the "circle has a center" prediction.
- **Nothing is exactly zero; nothing is NaN where a fit reported success.**

Every one of the four checks the plan named came back exactly as predicted, first attempt, no
surprises requiring investigation.

## What's committed vs. what stays regenerable

`results/raw/*.parquet` (359 files, 125,650 rows) is **not** committed — `*.parquet` is already
gitignored, and it's fully regenerable from the committed config, the pinned environment (Day 26),
and this package's source, which is the entire point of the reproducibility work the last three
days did.

Two things ARE committed, as the actual campaign deliverables:
- `results/main_campaign_manifest.json` — config SHA-256, resolved environment (numpy/scipy/
  pandas/pyarrow versions, platform), and a SHA-256 for every one of the 359 per-condition files,
  so a future re-run can be checked against this exact run without needing the raw data itself.
- `results/main_campaign_summary.csv` — 2,513 rows (359 conditions × 7 methods), produced by the
  new `scripts/aggregate_campaign.py` via `aggregate.summarize` (never a bare `groupby(...).mean()`
  on the raw table — see Day 24's journal for exactly why that would silently misreport reliability).
  Small enough to review in a diff, the way a generated table in a paper would be.

## What's next

Day 28: RQ1/RQ2 analysis over `main_campaign_summary.csv`, with the tautology framing, gross-error
rates reported alongside every error number, and statistical significance from Day 25's paired
t-tests — all per the plan's binding framing constraints.
