# Day 31 — P3: wiring up the cost metric, and what it changed

The preregistered `cost` metric (`docs/PREREGISTRATION.md`'s Metrics section: "wall-clock time per
fit, mean and std across seeds, same hardware") has been 100% unmeasured since Week 4
(`docs/WEEK5_PREFLIGHT_AUDIT.md` finding P3) — `runner.py` never called the existing
`methods.base.timed_fit` helper. Today fixes the wiring, measures cost properly, and checks whether
the fix changes anything already published in `docs/RQ1_RQ2_ANALYSIS.md`.

## The fix — and why the obvious one-liner doesn't type-check

`timed_fit(fit_fn, *args: FloatArray, **kwargs: object)`'s signature is deliberately strict so
`mypy --strict` can catch a caller passing something that isn't fit data. `fit_by_name(method_name:
str, ...)` takes the method name as its own first argument, so `timed_fit(fit_by_name, method_name,
i, q, ...)` doesn't type-check — `method_name` would have to flow into `*args: FloatArray`.

Fixed by extracting the shared dispatch decision (`raw_atan2` alone needs `mean_intensity`) into a
new private `_resolve_fit_call`, which both `fit_by_name` and a new `timed_fit_by_name` call —
neither duplicates the `if method_name == raw_atan2.NAME` branch a fourth time (the exact
duplication the Week 3 review already fixed once). `runner.py`'s `run_condition` now calls
`timed_fit_by_name` instead of `fit_by_name`.

## A real consequence, caught by running the suite rather than assumed away

Fixing the bug immediately broke three determinism tests
(`test_two_runs_are_byte_identical`, `test_worker_count_does_not_change_results`,
`test_resume_reproduces_an_uninterrupted_run`) — `_hash_directory` hashes raw parquet bytes, and
`runtime_s` now carries a real wall-clock value, which is not reproducible even for the identical
computation on the identical machine in the same process. Confirmed directly before writing any
fix, not assumed: loading two separate runs and comparing column-by-column showed `runtime_s` is
the ONLY column that ever differs.

This is not a new instance of D4's cross-platform finding — D4 was about genuine floating-point
non-determinism across different hardware, itself real information. A differing wall-clock time
between two runs of the same process is not new information; it is what a clock always does.
`test_reproducibility.py`'s own `_NUMERIC_COLUMNS` already excludes `runtime_s` from its comparison
for exactly this reason — `_hash_directory` was just the one place that hadn't caught up to that
precedent. Fixed by hashing each frame's substantive columns (via `to_csv`, `runtime_s` dropped)
rather than raw file bytes. All three tests pass again; two new tests confirm `runtime_s` is now
actually populated and non-negative end-to-end.

## The cost measurement: serial pass, structural subset

The main campaign's own (now-populated) `runtime_s` values are NOT used as the authoritative cost
numbers — they were recorded under `ProcessPoolExecutor` contention, which measures scheduler
behavior as much as algorithm cost, and doesn't honor "same hardware" in any stable sense. Instead:
`scripts/rq1_cost_measurement.py` runs a **serial, single-worker** pass, BLAS pinned to 1, over 9 of
the 359 preregistered conditions — the full baseline (the one condition where every axis sits at its
own baseline value) plus the last configured value of each of the 8 OFAT axes, selected by config
list position, before any cost number existed to look at.

**Results, added to `docs/RQ1_RQ2_ANALYSIS.md` as a new Cost section** (checked first, per Task 3.3,
whether any existing claim in that document depends on cost — it does not; every prior mention of
"iteration" is about Köning's convergence for RQ2, never timing, so this is purely additive, not a
revision of anything already claimed):

- At baseline, cost spans ~53× across methods (raw_atan2 fastest at 3.17 µs; Köning slowest at
  168.0 µs). The cost ordering is NOT the accuracy ordering — Kasa and Taubin (the cheapest
  correction-capable methods) are also the two `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` already
  singles out as more robust at small `arc_fraction`/low N, so the same circle-vs-ellipse structural
  split shows up as a genuine cost advantage too, not only a robustness one.
- **The real finding**: Köning's cost is dramatically, non-uniformly sensitive to `samples_per_fit`
  — 116× more expensive at N=1000 than at baseline (N=60), while Kasa (representative of the
  non-iterative methods) only costs 2.0× more over the same N change.
- Checked further rather than left as an open question, since the iteration-count data was already
  in hand: Köning's `n_iter_mean` at N=1000 is 2.64 — **slightly lower** than its 3.00-iteration
  baseline. Per-iteration cost itself rises from ~56 µs/iteration to ~7,375 µs/iteration (~130×).
  So the N-vs-cost relationship is driven entirely by each iteration doing more work at larger N,
  not by needing more iterations — a real, checked distinction, not an assumption. Flagged as a
  practical consequence for Week 5's RQ6 supplementary N-vs-noise design chart (Task 6): a chart
  recommending more samples for accuracy without also showing this cost curve would be incomplete
  for a practitioner deciding whether to actually run Köning at large N.

## A bug in my OWN Day 29 guard, caught by real usage the same week it shipped

Full suite run after adding the cost script failed one test —
`test_preregistered_results_tree_has_not_been_touched_by_supplementary_runs`, the Task 1 guard
against a supplementary run colliding with the preregistered results tree. It fired because
`scripts/rq1_cost_measurement.py` deliberately re-runs several of the SAME preregistered condition
names (e.g. `axis:amplitude_ratio=1.1`) into `results/supplementary/cost_measurement/`, by design —
measuring cost for the identical preregistered input under a different execution mode. That produces
the same filename in two different directories, which the Day 29 test treated as a collision.

It isn't one. The two files live in physically separate, non-nested directories; nothing in this
project ever reads across a directory boundary without an explicit glob scoped to one tree, so a
shared basename in two different trees cannot be confused by any real code path. The actual risk the
test's own docstring names — a supplementary script's output directory accidentally pointed at or
nested inside `results/raw/` — is a different, checkable invariant. Fixed by replacing the
filename-collision check with a direct structural check (the two directories are distinct paths,
neither nested in the other), and rewrote the test's docstring to record why the original check was
wrong rather than silently swapping the assertion. Classified per §0.2: an implementation error in
my own Task 1 test, not a difference in test conditions or a genuine discrepancy — fixed directly,
root cause recorded here and in the test itself.

## Verification

214 passed, 2 xfailed (unchanged count from Day 30 for the xfails; net +7 real tests today: 2 new
`test_runner.py` cases, 4 in the new `tests/test_methods_registry.py`, 2 in the new
`tests/test_rq1_cost_measurement.py`, minus the fixed-not-added guard test). `ruff check`, `ruff
format --check` on every file touched today, and `mypy --strict` all clean across the full repo.

## What's next

Task 4 (Day 32): the first genuinely new experiment of Week 5 — a supplementary bidirectional
waveform to actually test RQ3's hysteresis direction-dependence (D5). Per §0.6, the protocol goes
into `docs/SUPPLEMENTARY_PROTOCOLS.md` and gets committed and pushed BEFORE any code is written.
