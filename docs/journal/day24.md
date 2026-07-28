# Day 24 — The sweep runner, and two things that only showed up at full campaign scale

## The four requirements, and the mechanism behind each

Day 24 needed a runner that is incremental, resumable, deterministic, and parallel. Each got a
specific mechanism rather than a vague intention:

- **Incremental**: one Parquet file per condition. A crash loses at most one condition's worth
  of work (~350 fits, a fraction of a second).
- **Resumable**: each file is written to `<name>.parquet.tmp` and then moved into place with
  `os.replace`, which is atomic on both POSIX and Windows. That means a reader can never see a
  half-written file — so a file's mere existence is proof it's complete, and "resume" is just
  "skip conditions whose file already exists." No corruption detection needed, because the
  corrupted state literally can't occur.
- **Deterministic**: every per-condition frame is sorted by `(method_name, seed_index)` before
  it's written, so which worker happened to finish first can never change the bytes on disk.
- **Parallel**: split the work across conditions (not seeds), since conditions share no mutable
  state.

Both mandatory tests — run twice and diff, and run at 1 worker vs. 4 workers and diff — passed
on the first attempt: **byte-identical** in both cases. That's a strong result. It means the
determinism claim isn't "usually reproducible," it's actually true.

## The Windows trap that would have surfaced three days later

Condition names look like `axis:amplitude_ratio=1.25` and
`grid:arc_x_noise:arc_fraction=0.5,noise_std=0.02`. The `:` character is illegal in a Windows
filename. Day 26 adds a Windows CI job — if I'd written `f"{name}.parquet"` naively, every local
test and every Linux CI run would pass clean, and the very first Windows run would fail on
essentially every grid condition. Caught it now by sanitizing filenames deterministically
(`condition_filename`) and testing it directly against the exact offending string, rather than
letting Day 26 discover it.

## Two things that only showed up once the real 359-condition campaign ran

Everything above passed cleanly on the smoke config (2 methods, 3 conditions, 5 seeds). Running
the actual 125,650-fit campaign surfaced two things the smoke config was too small to expose.

### 1. `raw_atan2` looked like it wasn't the worst method — until I understood why

A naive `groupby("method_name")["displacement_rmse_m"].mean()` over the full campaign put
Heydemann first and Fitzgibbon near the bottom of "best." That's backwards from what the
structural predictions say should happen, and it's *exactly* the R1 finding the Week 3 review
already documented: Heydemann self-reports failure 24.5% of the time and excludes those attempts
from its own mean (so its mean only reflects the easy 75%), while Fitzgibbon self-reports 0%
failure but silently returns garbage (gross error) 13.5% of the time and that garbage gets
averaged in as if it were a real number.

I checked this wasn't a wiring bug by filtering to *usable* rows (not failed, and not a gross
error by the preregistered 0.5 rad threshold) before taking the mean. Once filtered correctly,
`raw_atan2` and Kasa — the two methods with no correction model at all for this campaign's
conditions — sink to the bottom, exactly where the structural predictions say they should be.
The runner and the metrics are correct; a naive per-method mean over the raw table is not a valid
way to compare methods, which is precisely why `aggregate.summarize` and `aggregate.is_rankable`
exist. Day 28's analysis must go through those, never a bare `groupby(...).mean()`.

### 2. A real FutureWarning, found and fixed

Loading all 359 files back with `pd.concat` printed:

> The behavior of DataFrame concatenation with empty or all-NA entries is deprecated...

Isolated it with a minimal synthetic repro (340 all-`None` frames plus 19 frames with real
values, matching the real shape) rather than guessing: it was specifically the `n_iter` column.
Only Köning is iterative and sets it; every other method leaves it `None`, so roughly 340 of the
359 per-condition files have `n_iter` as an entirely-null column, and concatenating that many
all-NA columns against files with real values is exactly the case pandas is warning about.

Fix: cast `n_iter` to pandas' nullable `Int64` dtype before writing, rather than letting it fall
back to a float64-with-NaN column. Verified the fix directly with the same synthetic repro
before touching the real pipeline, then confirmed it on the actual 125,650-row campaign with a
clean stderr. This is also the more honest type for the column — an iteration count is an
integer, never a float.

## A real, separate environment finding, not a code bug

While chasing the warning, I tried wrapping the campaign run in `warnings.catch_warnings()` to
inspect what fired. That crashed the interpreter with `SystemError: attempting to create
PyCFunction with class but no METH_METHOD flag` inside `numpy.all` — called from `fitzgibbon.py`'s
eigenvector validity check. Retried clean (no warnings context manager) and it completed
successfully, twice, with `free -h` showing no memory pressure. The crash appears specifically
correlated with a `warnings.catch_warnings()` context wrapping heavy `scipy.linalg.eig`/
`np.linalg` activity in this numpy 2.2.6 / WSL environment — not with the BLAS-thread-contention
crash Day 20 already documented (that one is prevented by the pin; this one occurred *with* the
pin active). Production code never wraps itself in `catch_warnings`, so this doesn't affect the
runner, but it's a real trap for anyone debugging with that technique here. Logged for the vault
memory rather than chased further, since it's outside this task's scope and doesn't affect any
shipped code path.

## What was verified before calling this done

- 8/8 tests, including byte-identical determinism across repeated runs and across worker counts.
- Full 125,650-fit campaign run twice cleanly end-to-end via the actual `scripts/run_campaign.py`
  entry point, with empty stderr both times.
- Schema and row count exact (125,650 rows, columns matching `RESULT_COLUMNS`).
- `pandas-stubs` installed and pinned (matching the exact installed pandas version) so mypy
  checks pandas usage against real types rather than silencing the import — pandas ships no
  `py.typed` marker itself.
- Full suite: 168 passed. Ruff and mypy clean.

## A CI failure that previewed Day 26's whole reason for existing

Pushed, and CI's Python 3.11 job failed mypy strict — passing locally under 3.10. The cause:
`pandas>=2.0` in `pyproject.toml` is loose enough that pip resolves **pandas 3.0.5** on Python
3.11 (a real major-version jump) while 3.10 still resolves 2.3.3, and pandas 3.0's stubs type
`.sort_values().reset_index()` as `Any` in a way 2.x's stubs don't — mypy strict's
`no-any-return` only fires on the 3.11 job.

Couldn't reproduce it directly (no Python 3.11 interpreter available locally, and pandas 3.0.5
itself requires ≥3.11), so I isolated the *general* failure pattern instead: a two-line repro
of "a function declared to return `Any`, called from a function declared to return a concrete
type," confirmed that error under the local mypy, then confirmed that binding the result to an
explicitly-annotated intermediate variable suppresses it — a structural mypy behavior that
doesn't depend on which stub version is actually in play. Pushed that fix and let CI's real
Python 3.11 + pandas 3.0 environment be the actual test, since I couldn't replicate it any other
way. Green on the second push.

This is exactly the reproducibility gap Day 26 exists to close: two CI jobs building the *same*
declared dependency (`pandas>=2.0`) into two different major versions is a real, live instance of
"reproducible across environments" not yet being true. Flagging it here rather than fixing it
fully now — pinning belongs to Day 26's task, not a side effect of a Day 24 mypy fix — but Day 26
should pin `pandas` to an exact version (not just `pandas-stubs`, which is already effectively
pinned via matching the resolved pandas version) as part of its dependency-pinning work.

## Left uncertain

The `warnings.catch_warnings()` interaction above is worth a documented WSL-quirks entry but
wasn't root-caused to a specific numpy/scipy internal — flagged, not chased further, since it
doesn't affect any code this project actually ships.
