# Day 32 — RQ3 supplementary: does direction actually matter?

The first genuinely new experiment of Week 5. Per §0.6, the full protocol (`docs/SUPPLEMENTARY_PROTOCOLS.md`
Protocol 1) was written, committed, and pushed **before** any implementation code existed — so the
design predates any result it could have been shaped to produce.

## The waveform

`src/hoqi_bench/waveforms.py`'s `build_bidirectional_ramp` implements exactly what the committed
protocol specified: a triangle wave — ascending half matching `arc.build_arc_ramp`'s own
`endpoint=False` convention, descending half deliberately sampling the peak exactly once (a genuine
turning point, not `build_arc_ramp`'s wraparound duplicate D1 fixed). Two things verified empirically
*before* the protocol was written, not assumed: direction reverses correctly (exactly one isolated
`direction=0` sample at even N, zero at odd N — never a region), and `transforms.hysteresis`'s
existing formula already leaves that sample exactly unperturbed with zero code changes needed.
14 new tests in `tests/test_waveforms.py` confirm both properties plus sample-count/peak-phase
matching against `build_arc_ramp`.

## Wiring it in without duplicating the pipeline

`simulate.py`'s own docstring calls itself "the single canonical path" specifically to prevent
independent reconstructions from silently diverging. Rather than write a second copy of its 5-step
composition for the supplementary experiment, added an optional `waveform_fn` parameter to
`simulate_condition` (default `build_arc_ramp` — every existing call site's behavior is completely
unchanged) and threaded the same parameter through `runner.run_condition`. Verified: full suite
still green after both changes, before any supplementary code was written.

## Running it

`scripts/rq3_hysteresis_bidirectional.py` runs the same 8-magnitude, 50-seed, 7-method grid as the
preregistered campaign's `hysteresis_magnitude` axis — the only difference is the waveform generator
— reuses Day 27's `aggregate_campaign` function rather than a second aggregation path, and joins
against the immutable `results/main_campaign_summary.csv` at matched condition/method.

**First real bug of the day, caught by inspecting actual output rather than trusting a summary
count**: two methods (Heydemann, Köning) went from `unusable_rate=0.0` (monotonic) to
`unusable_rate=1.0` (bidirectional) at `hysteresis_magnitude=0.2` — the single most dramatic
possible outcome. The pre-specified RMSE-difference criterion missed this entirely: a NaN mean RMSE
(what `aggregate.summarize` returns when zero seeds succeed) makes a NaN comparison silently
`False`, reporting "no difference detected" for exactly the case that most needed reporting. This
is the same shape of omission this project's own R1 finding already named once
(`docs/WEEK3_REVIEW.md`: failure rate must always be reported alongside accuracy, never folded into
or hidden behind it) — caught here a script later. Fixed with a third, always-visible column
(`bidirectional_became_unusable`) that cannot be silently NaN'd away; a synthetic reproduction of
the exact bug is now a permanent regression test
(`tests/test_rq3_hysteresis_bidirectional.py::test_became_unusable_flag_catches_what_the_rmse_criterion_cannot`).

## The result

**36 of 56 (condition, method) pairs exceed the RMSE noise-floor criterion; 2 more went from usable
to fully unusable.** `raw_atan2` is the one method that never shows a difference (0/8) — expected
and consistent with the floor-masking trap flagged in `docs/WEEK5_PREFLIGHT_AUDIT.md`: its baseline
error is dominated by the uncorrected classic-axis distortion, swamping any hysteresis-direction
signal. At the smallest tested magnitude (`h=0.02`), Fitzgibbon, Halir & Flusser, Heydemann, and
Köning all show real, non-floor-masked differences; Kasa, Taubin, and raw_atan2 do not.

This is a real, reportable finding — not the null result the protocol's own falsification criterion
described as one honest possible outcome. Direction of travel, not just magnitude, measurably
affects several methods' displacement recovery under this project's hysteresis model. Full
interpretation (what mechanism plausibly explains it, whether it changes any RQ3 framing) is
deferred to Task 8's RQ3-RQ6 analysis document — today's job was running the experiment and
reporting the numbers honestly, not interpreting them.

## Flipping the guard test

Day 29's `test_hysteresis_axis_actually_reverses_direction` still correctly `xfail`s against the
preregistered config (D5 remains true there — the preregistered campaign itself is never re-run to
fix this). A new sibling, `test_supplementary_hysteresis_config_actually_reverses_direction`, proves
the fix exists and works against `configs/supplementary_hysteresis.toml` + `build_bidirectional_ramp`
— the exact "flip xfail to passing against the supplementary config" the plan specified, done as an
addition alongside the original rather than a replacement of it, so both facts stay visible.

## Verification

231 passed, 2 xfailed (net +16 real tests today: 14 in `test_waveforms.py`, 2 in
`test_rq3_hysteresis_bidirectional.py`, +1 new sibling test in `test_campaign_integrity.py`, net of
the analysis-script fix). `ruff check`, `ruff format --check` on every file touched today, and
`mypy --strict` all clean — one real mypy catch along the way (a test passing `AnyFloatArray` where
`hysteresis` requires strict `FloatArray`, fixed with the same cast pattern `simulate.py` itself
uses). One transient `Fatal Python error: Floating point exception` observed on one of several full-suite
runs, not reproducible on immediate retry with identical code (2 of 3 runs clean) — consistent with
this environment's previously-documented BLAS/native-library flakiness under WSL2, not a regression
introduced today.

## What's next

Task 5 (Day 33): RQ4 — Poisson vs. Gaussian noise ranking comparison. The one open methodological
decision (what "equivalent noise level" means for a fair ranking comparison) goes to `llm-council`
before any code, per §0.4.
