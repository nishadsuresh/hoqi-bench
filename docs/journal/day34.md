# Day 34 — RQ6 supplementary: the N x noise design chart

The second genuinely new experiment of Week 5, and the last piece of the D6 fix. Per §0.6, the
full protocol (`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 3) was committed and pushed before
`configs/supplementary_n_x_noise.toml` or any implementation existed.

## The grid

Unlike Task 4's RQ3 experiment, this needed no new forward-model code — the standard
`arc.build_arc_ramp` waveform and the standard `runner.run_campaign` pipeline are unchanged. The
only new thing is `configs/supplementary_n_x_noise.toml`'s `[grids.n_x_noise]` interaction, using
exclusively the preregistered grid's own `samples_per_fit` (7 points) and `noise_std` (10 points)
values — legitimate as a supplementary addition specifically because it adds a new interaction
rather than editing any existing preregistered condition. 24,500 fits total, matching the protocol.

## A real segfault, diagnosed rather than worked around blindly

The first run, via `run_campaign`'s default `ProcessPoolExecutor` path, crashed with a segmentation
fault (exit 139) after ~14 seconds of wall time but 1m25s of CPU time — heavy parallel activity. Per
§0.2, this got a hypothesis before a fix: given this session had already hit two other native-
library crash signatures on this exact WSL2 machine (a transient `Fatal Python error: Floating
point exception` on Day 32, a transient `SystemError: attempting to create PyCFunction...` on Day 33
— the latter the exact signature this project's own Day 20 journal already documented as a known
BLAS-threading flake), the hypothesis was that this was the same category, not something specific to
this config.

Tested directly: reran the identical config with `n_workers=1` (no `ProcessPoolExecutor` at all) —
completed cleanly. This doesn't prove the parallel path is always unsafe on this machine, but it
does confirm the crash is a multiprocessing/BLAS interaction, not a defect in the analysis logic.
Given 24,500 fits costs nothing to run single-threaded (the full 125,650-fit preregistered campaign
itself completes in ~14s), fixed the script to call `run_campaign` with `n_workers=1` explicitly,
with the reasoning and the direct evidence recorded in the function's own docstring — the same
"isolation buys little for a fast job" logic already used for the Day 31 and Day 32 supplementary
scripts, applied here for crash-avoidance rather than clean-timing measurement.

## The design chart

Ran cleanly in 1.6 seconds. **Only 3 of 70 (method, noise_std) combinations produce an actual
interior crossing** — most either always meet the preregistered tolerance regardless of N (29/70,
the four general-conic fitters at low noise) or never meet it regardless of N (38/70, Kasa/
raw_atan2/Taubin at every noise level, and every method at the highest noise levels). Spot-checked
one boundary case before trusting it: Heydemann jumps from `no_breakdown_in_range` at
`noise_std=0.06` straight to `broken_at_start` at `noise_std=0.08` with no interior "found" state in
between — confirmed directly against the raw per-N RMSE values that ALL seven swept N values already
exceed tolerance at `noise_std=0.08` (3.73e-9 to 3.88e-9 m, vs. a 3.164e-9 m tolerance), so
`broken_at_start` at the scan's first point (N=1000) is the mathematically correct call, not a bug.

**The honest headline**: for this campaign's swept range, `samples_per_fit` mostly does NOT
determine whether a method clears the preregistered tolerance — which method, and how much noise,
does. This echoes Day 30's power-law finding (samples_per_fit shows almost no relationship at zero
noise) and Day 33's RQ4 finding (no statistically robust cross-noise-model ranking difference) —
three separate analyses this week, from three different angles, converging on the same shape of
result: N matters far less than the classic literature's framing might suggest, for this project's
specific parameter ranges.

## Flipping the D6 xfail test

Same pattern as Day 32: the Day 29 xfail test stays exactly as it was (D6 remains true for the
preregistered config, unmodified), and a new sibling test confirms the supplementary config actually
has the required interaction grid.

## Verification

246 passed, 2 xfailed (net +5 real tests: 4 in `test_rq6_n_x_noise.py`, 1 new sibling in
`test_campaign_integrity.py`). `ruff check`, `ruff format --check`, and `mypy --strict` all clean.
One more transient native-library crash observed on a full-suite run (same category as Days 32-33,
not reproducible on immediate retry) — noted, not chased further, consistent with how the prior two
were handled.

## What's next

Task 7+8 (Day 35): RQ5's sub-fringe analysis, honestly scoped per D7, and the RQ3-RQ6 analysis
document synthesizing everything from Tasks 2, 4, 5, and 6 — reviewed by `llm-council` for
overclaiming before being presented to Nishi, per §0.4 item 2.
