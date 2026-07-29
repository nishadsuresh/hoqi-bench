# Day 35 — RQ5, the RQ3-RQ6 synthesis, and a caught overclaim

## RQ5: sub-fringe analysis over the full range, not just the extreme point

`scripts/rq5_analysis.py` reads only existing preregistered data (`arc_fraction` axis + `arc_x_noise`
interaction grid) — no new campaign. Cross-checked every `arc_fraction=0.02` number against
`docs/RQ1_RQ2_ANALYSIS.md`'s RQ1b table programmatically before writing anything: exact match.

Two findings distinct from RQ1b's single-point headline, visible only by looking at the whole range:

- **Heydemann's `unusable_rate` is exactly 1.0 at every sub-fringe `arc_fraction` value and exactly
  0.0 at `arc_fraction=1.0`** — verified across every noise level in the interaction grid, not just
  the noiseless baseline. Not a gradual degradation like every other method shows; a clean binary
  threshold.
- **Halir & Flusser's `unusable_rate` is non-monotonic**: 0.54 at 0.02, rising to 1.00 at 0.05,
  falling back to 0.00 by 0.10. A reader anchored on the single extreme point RQ1b reports would
  miss that reliability gets briefly worse before it gets better.

## The RQ3-RQ6 synthesis document, and a real overclaim caught before it shipped

`docs/RQ3_RQ6_ANALYSIS.md` synthesizes Tasks 2 (RQ3 power-law), 4 (RQ3 hysteresis), 5 (RQ4), 6
(RQ6), and today's RQ5 work. Run through an adversarial review hunting specifically for
overclaiming, per §0.4 item 2 — the same discipline Day 28 applied to the RQ1/RQ2 draft.

**The review caught a fabricated convergence claim.** The first draft asserted "three independent
analyses converge" on `samples_per_fit` being a weak lever, citing RQ3 part 1 and RQ4's within-axis
analysis alongside RQ6. Checked directly: **RQ3 part 1's power-law axes are `amplitude_ratio`,
`quadrature_error_rad`, `dc_offset`, and `hysteresis_magnitude` — `samples_per_fit` was never among
them**, and RQ4's within-axis analysis covers only `photon_scale`/`noise_std`. Neither citation
supports the claim being made. The real second data point was the pre-flight audit's own P2
finding (the zero-noise flatness result from Day 29), misfiled under the wrong analysis's name.
Corrected to state the real two-way convergence at the strength it actually has, with the citation
error itself recorded in the document rather than silently fixed.

Two more real issues from the same review, fixed:

- The document's "Established" summary section stated preregistered and supplementary findings
  with identical, undifferentiated confidence — violating the document's own framing rules 5/6.
  Split into separate paragraphs by evidentiary source.
- RQ3 part 1's `quadrature_error_rad` exponent didn't state which methods produced the 7 clean
  fits. Checked: raw_atan2, Kasa, and Taubin — the three methods with **no structural correction**
  for that distortion, not the tautologically-favored general-conic fitters. This resolved the
  review's concern (that the exponent might be a construction-check artifact) with a factual
  clarification, not a retraction — the finding survives, now stated precisely.

A minor fourth point (Heydemann's mechanism explanation bordering on asserted-as-settled) was
already adequately hedged with "consistent with" language; tightened slightly for consistency with
the corrected framing elsewhere in the document.

## Task 8b: clean-clone reproduction check — passed in full

The check this project's entire CI investment (Days 7, 26) exists for. Cloned `origin/main` at
`cc3e0cd` (this day's push) into a fresh directory outside the working tree, built a genuinely new
venv via `uv venv` (the existing dev venv's own creation tool, per Day 26's precedent — `python -m
venv` failed outright on this machine: `python3.10-venv` isn't installed system-wide, meaning the
dev venv could not be recreated from scratch by the documented `pip`-based instructions alone, only
by `uv`), and installed with `pip install -e ".[dev,validation]"` per the README's own documented
command.

- **First run**: 244 passed, 1 skipped, 2 xfailed — the skip was
  `test_external_cross_validation.py`, correctly skipped because the `validation` extra
  (`lsq-ellipse`, `ellipsinator`) wasn't installed on the first pass. Not a defect: expected,
  documented behavior, confirmed by reinstalling with `.[dev,validation]` and re-running.
- **Second run, full extras**: **248 passed, 2 xfailed** — exact match to the dev environment's own
  count, both xfails correctly pointing at D5/D6 by name, not silent failures.
- `ruff check` and `mypy --strict`: both clean, zero configuration differences from the dev venv.
- `tests/test_reproducibility.py::test_smoke_campaign_matches_reference_values_within_tolerance`
  explicitly re-run in isolation: **passed** — this WSL sandbox reproduces the committed reference
  values within the documented `rtol=1e-9`/`atol=1e-15` tolerance (D4), on a venv built from nothing
  but the pushed repo, the pinned dependency versions, and the committed reference CSV.

**One real, worth-recording finding, not a defect**: this machine cannot recreate the project's own
existing dev venv using the literal command an external contributor following only the README would
run (`python -m venv` + `pip install`) — `python3.10-venv` is absent system-wide, so `python -m venv`
fails before `pip` even enters the picture. `uv` is already this project's own fallback for exactly
this class of problem (Day 26's journal, for a different reason — Python 3.11 testing). Not fixed
today (a system package install is outside this project's scope, and `uv`'s presence as a working
alternative means the actual reproducibility claim — a correct venv can be built and everything
passes — still holds); flagged for Day 37's README rewrite to document `uv venv` as the primary
instruction on this class of system, not an aside.

Cleaned up: temporary clone and venv both removed after the check completed.

## Verification

248 passed, 2 xfailed. `ruff check`, `ruff format --check`, `mypy --strict` all clean. One more
transient native-library crash on a full-suite run (same category as Days 32-34, not reproducible
on immediate retry).
