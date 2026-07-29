# Day 29 — The gate: audit record, deviations, CI guards, release scaffolding

Week 5 begins here, and this day exists specifically to be the ordering constraint everything else
depends on: nothing else in Weeks 5-6 may start until this is committed and pushed, because the
whole point is that the paper trail for four pre-existing defects exists *before* any supplementary
data gets collected. If the deviations were written after seeing supplementary results, they would
carry no more evidentiary weight than the defects they document.

## What got built

- **`docs/WEEK5_PREFLIGHT_AUDIT.md`** — the four defects found before this plan was written
  (P1-P4), each with a runnable reproduction command, the measured numbers, root cause, why it was
  missed, and the consequence for the affected research question. Nothing here is new today; this
  formalizes what the pre-flight audit already found on 2026-07-28.
- **Three preregistration deviations, dated 2026-07-29**:
  - **D5**: the `hysteresis_magnitude` axis measures direction-independent radial inflation, not
    path-dependent hysteresis — every campaign waveform is monotonic, so
    `transforms.hysteresis`'s direction-reversal branch is dead code for the entire 125,650-fit
    campaign (measured: direction is `+1` at 100% of samples, `-1` at 0%). RQ3's hysteresis half is
    declared unanswered by the preregistered campaign.
  - **D6**: RQ6 (an N-vs-noise design chart) is unanswerable — `samples_per_fit` was swept entirely
    at zero noise, `noise_std` entirely at N=60, no interaction grid exists. Worse: the
    preregistration's own justification for adding this axis (a "7x swing") is a noise-averaging
    effect that cannot appear at the zero noise it was actually swept at.
  - **D7**: RQ5's grid never reached the "many-fringe" regime its own name promises —
    `arc_fraction=1.0` is exactly one cycle, not many. A previously-undocumented narrowing.
  - Both D5 and D6 explicitly reject amending the grid to retroactively "become" answerable —
    per the `llm-council` review behind `docs/WEEK5-6_EXECUTION_PLAN.md`, that would be exactly the
    forking-paths move preregistration exists to prevent. Both RQs are declared unanswered as
    written; supplementary experiments (Week 5 Tasks 4 and 6) are the only permitted route to a
    real answer, reported separately throughout.
  - A parallel note in `docs/WEEK3_METHOD_CONTRACT.md` records the cost-metric gap (P3) as a
    **defect report, not a deviation** — nothing about ranges/metrics/protocol changed, this is
    unfinished instrumentation, fixed in Task 3.
  - `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` D2 corrects its own Category 3 hysteresis framing to
    match D5.
- **`tests/test_campaign_integrity.py`** — the permanent CI guard against this defect class. Four
  groups of checks: per-axis dynamic-range floors (calibrated from a real measured table, not a
  round number — the module docstring explains at length why a single global threshold cannot work,
  since `dc_offset`'s 2.81x comes entirely from `raw_atan2` while every *correcting* method sits at
  1.00-1.11x there **by correct design**, indistinguishable by magnitude alone from the actual
  `samples_per_fit` defect at 1.10x); a direct hysteresis direction-reversal check (`xfail` against
  the preregistered config, pointing at D5); preregistered-metric population checks, restricted to
  conditions where `unusable_rate < 1.0` (a condition where every seed fails has a legitimately
  undefined mean error — confirmed directly that all 93 null rows in the summary coincide exactly
  with `unusable_rate == 1.0` before writing this floor, not assumed); and a declarative
  research-question-to-grid mapping, which is the test that would actually have caught P2 before the
  campaign ever ran (`xfail` against the preregistered config, pointing at D6).

  Two floors needed a second pass after the first run: the metric-population floor initially fired
  on `displacement_rmse_mean_m`/`phase_rmse_mean_rad` at 96.3% populated, which turned out to be
  every genuinely-unusable condition, not a silent failure — fixed by restricting the denominator to
  usable rows. The `samples_per_fit` floor was initially set at exactly the measured 1.10x value and
  failed on a rounding difference (1.0957x measured by this test's own slightly different pivot);
  fixed by setting it deliberately just below the measured value, matching the intent (pass-while-
  documenting-the-defect) rather than the letter of the number.

- **Release scaffolding, pulled forward from Day 40 per the plan's own reasoning that these are
  ten-minute fills today and a fire drill later**: `LICENSE` (MIT — provisional pending Nishi's
  explicit confirmation, per the plan's Decision Points list; used the plan's own stated
  recommendation rather than leaving the file absent), `CITATION.cff` (DOI left as an explicit
  placeholder, cannot be filled before Zenodo mints one), `CHANGELOG.md` (Weeks 1-6 summary,
  including the four known limitations named plainly rather than buried), and `MANIFEST.in` so
  setuptools actually includes all three in the sdist — verified directly by building one and
  confirming all three filenames appear in the resulting tarball, not assumed from the manifest
  alone.

## What was checked and found NOT broken

RQ4's noise-model exclusivity was reread carefully while writing the audit doc, since an earlier
draft of the audit's wording ("mutually exclusive in `pipeline.py`") was imprecise: both
`poisson_noise` and `gaussian_noise` are applied unconditionally on every condition
(`simulate.py:178-179`); exclusivity at any given condition is an emergent property of the config's
baseline values, not a runtime branch. Worth stating precisely now rather than letting Task 5 go
looking for a branch that does not exist.

## A minor finding, noted but explicitly not acted on today

`ruff format --check .` reports 27 files would be reformatted — none of them touched by today's
work (confirmed by stashing today's changes and re-running; the count is identical before and
after). Root cause: `.github/workflows/ci.yml` runs `ruff check` and `mypy`, but never
`ruff format --check` — despite `docs/WEEK4_EXECUTION_PLAN.md`'s own standing rule #4 claiming "all
three are CI-enforced." That claim has apparently been false since at least the point these 27
files last drifted, undetected because nothing runs the check that would catch it. Not fixed today:
reformatting 27 unrelated files does not belong in a commit whose entire point is "documentation and
guards only, no code changes" (see the commit message). Flagged for the Day 36 documentation-drift
audit (Task 9), which is the day already scoped to find exactly this shape of gap.

## Verification

`ruff check .` and `mypy` both clean. Full suite: 202 passed, 2 xfailed (both pointing at recorded,
dated deviations, not silent failures). Committed as a single commit containing documentation and
guards only — no experiment code, no supplementary data collected.

## Escalated to Nishi (not resolved today — outside what code can do)

The OSF registration at https://osf.io/qyw6t needs an amendment recording D5-D7. Per the plan's own
§2.7 risk 2 (an `llm-council` peer-review finding): a dated note in a repository the author controls
carries limited evidentiary weight on its own; the amendment is what gives these deviations the same
external-timestamp property the original v2 registration has. This blocks Day 41's Zenodo DOI, not
just a documentation nicety — flagged as such in the plan's Decision Points list.

## What's next

Task 2 (Day 30): the power-law characterization anchor named all the way back on Day 13 — "the real
data comes in on Day 30." `power_law.fit_power_law_exponent` was built and validated against
synthetic data three weeks ago, deliberately not run against real campaign results until now.
