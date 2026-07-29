# Week 6 Documentation-Drift Audit

Run 2026-07-29 (Day 36), per `docs/WEEK5-6_EXECUTION_PLAN.md` Task 9. Five agents dispatched in
parallel, each auditing a disjoint set of `docs/*.md` and `notes/*.md` files, verifying every
quantitative and definitional claim against the actual current code, config, and result data —
never trusted from the prose itself. This is the specific search the Weeks 1-2 audit's own council
review named as missing: a preregistered term or number drifting silently in prose, caught only by
an audit rather than by any automated process.

**Result: 7 genuine findings across ~4,500 lines of documentation and ~15 files.** Six fixed
directly (per §0.2 classification (i), implementation/documentation errors); one (README.md)
recorded here in full for Task 10's dedicated rewrite rather than patched today, since a partial
fix now would be redone tomorrow.

---

## Fixed today

### 1. Stale count baked into SOURCE CODE, not just a planning doc

`src/hoqi_bench/harmonics.py`'s own module docstring stated "99 of the main campaign's 359
conditions have `arc_fraction < 1.0`." Recomputed from `configs/main_campaign.toml` via
`resolve.iter_conditions`: the correct count is **88** (8 from the `arc_fraction` OFAT axis + 80
from the `arc_x_noise` grid). This is the most serious of the six fixed items — a wrong number had
propagated from a planning document (`docs/WEEK4_EXECUTION_PLAN.md`) into the actual, currently-
running source code's own documentation.

**Fixed:** `harmonics.py`'s docstring corrected to 88, with the correction dated. **Guarded
permanently:** new test `test_sub_fringe_condition_count_is_consistent_across_source_and_docs` in
`tests/test_docs_consistency.py`, matching the existing total_runs/n_seeds pattern — recomputes the
count from the live config and asserts the source docstring states it, so a future config change
that shifts this number can't drift silently again.

### 2. `STRUCTURAL_ADVANTAGE_PREDICTIONS.md`'s own D1 correction didn't reach a later restatement

The document's Per-axis Predictions section was corrected by dated deviation D1 (2026-07-27) to
remove Taubin from the Category 1 (tautological) classification on the classic axes — but the
"How this document is used" section, containing an example caption reusable verbatim in later
analysis, still listed Taubin among "Heydemann, Halir & Flusser, Fitzgibbon, Taubin, and Köning."
**Fixed:** Taubin removed from the caption, with a note explaining D1 fixed the main text but missed
this restatement at the time.

### 3-4. Stale "if implemented" / "if time allows" conditionals for methods that were, in fact, built

`notes/contribution_claim.md` and `notes/taubin_1991.md` both still hedged Köning/Wimmer/Witkovský's
and Taubin's implementation as conditional on schedule, written before Week 3 built all seven
methods. **Fixed:** both updated to state plainly that both methods exist, citing
`METHOD_REGISTRY`/the actual source file.

### 5-6. Two overclaims from THIS WEEK's own work, caught by the same audit that found the older ones

- `docs/WEEK5_PREFLIGHT_AUDIT.md` (P1) and `docs/RQ3_RQ6_ANALYSIS.md` both stated a single "33.9×
  displacement-RMSE dynamic range" figure for "the four conic fitters" on `hysteresis_magnitude`.
  Recomputed directly: three of the four (Fitzgibbon, Halir & Flusser, Köning) are at 33.8–33.9×,
  but **Heydemann is 17.9×** — roughly half. **Fixed:** both documents corrected to name the actual
  per-method split rather than a blended figure.
- `docs/RQ1_RQ2_ANALYSIS.md`'s RQ1c section claimed `raw_atan2`'s first-order cyclic error is "an
  order of magnitude above every corrected method (0.026–0.028 rad vs. 0.00006–0.0003 rad)."
  Recomputed from `results/rq1_cyclic_error.csv`: the corrected-method range is actually
  5.6×10⁻⁵–1.28×10⁻⁴ rad (the stated upper bound overstated the true maximum by ~2.3×), and on
  `dc_offset` specifically, `raw_atan2` (7.5×10⁻⁵ rad) is *lower* than five of the six corrected
  methods — the "order of magnitude above every corrected method" claim does not hold on that axis
  at all. **Fixed:** corrected range stated, and the `dc_offset` exception now stated explicitly
  rather than implied to hold uniformly.

**Note on what this means for the project's own review discipline**: findings 5 and 6 are errors in
work produced and reviewed (via `llm-council`, for the RQ3-RQ6 document) *this same week*. Neither
council review nor the original authoring caught them — a dedicated, independent verification pass
against the raw data did. This is direct evidence for why Task 9 exists as its own step rather than
being folded into each day's own self-review.

---

## Recorded for Task 10 (Day 37), not fixed today

### 7. `README.md` is significantly stale

Three separate, confirmed mismatches, all requiring the dedicated rewrite Task 10 already covers
rather than a patch here:

- **Status line is flatly wrong.** States "Weeks 1-3 of 6 complete... Week 4... is next; no
  campaign data exists yet." Actual state: Week 5 is complete, `docs/PREREGISTRATION.md` has
  deviations D1-D7, `results/main_campaign_summary.csv` and every per-RQ analysis CSV exist on
  disk, `docs/RQ1_RQ2_ANALYSIS.md` and `docs/RQ3_RQ6_ANALYSIS.md` both exist.
- **Test count is stale.** States "136 tests passing." Actual current count, via
  `pytest --collect-only -q`: **251** — grown substantially across Weeks 4-5.
- **Setup instructions don't mention `uv`.** Presents only `python3 -m venv .venv && pip install`
  as the setup path. Day 35's clean-clone check found this literal path fails on the current dev
  machine (`python3.10-venv` not installed system-wide) — `uv venv` is the working alternative,
  already used successfully for the Day 35 verification, but never documented in the README itself.

---

## What was checked and found clean

The majority of documentation checked out. Specifically confirmed consistent with current code/
data, not just assumed:

- `docs/PREREGISTRATION.md`, `docs/PREREGISTRATION_v1_superseded.md`, `docs/experimental_design.md`
  — every axis range, grid cardinality, seed count, tolerance value, and total-run count matches
  `configs/main_campaign.toml` exactly. `experimental_design.md`'s "full-circle ramp measurement"
  wording (the original P4/D7 finding) is already correctly disclosed by D7 — not new drift.
- `docs/WEEK3_METHOD_CONTRACT.md`, `docs/WEEK3_REVIEW.md` — every named constant (
  `MAX_UNUSABLE_RATE_FOR_RANKING`, `GROSS_ERROR_PHASE_RAD`, Heydemann's radius-consistency
  threshold, Köning's `_MAX_ITER`) matches the current source values exactly.
- `docs/WEEK1-2_AUDIT.md`, `docs/WEEK3-4_PLAN.md` — historical claims correctly scoped as
  historical; no evergreen-framed claim found false.
- `docs/RQ1_RQ2_ANALYSIS.md`, `docs/RQ3_RQ6_ANALYSIS.md`, `docs/WEEK5_PREFLIGHT_AUDIT.md`,
  `docs/SUPPLEMENTARY_PROTOCOLS.md` — every CSV row count, condition count, and headline
  percentage checked against the actual result files matched, apart from findings 5-6 above.

## Process note

Per the plan's Task 9 instruction to use a parallel-dispatch pattern: 5 agents ran concurrently,
each independently verifying a disjoint slice of the documentation set against source, rather than
one agent reading everything serially. Total audit coverage: ~15 files across `docs/` and `notes/`,
cross-referenced against `configs/main_campaign.toml`, `src/hoqi_bench/` in full, and 8 result CSVs.
