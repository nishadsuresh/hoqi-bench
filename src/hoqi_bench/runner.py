"""
The sweep runner: turns a validated `SweepConfig` into the raw results
table every downstream layer reads.

Why this exists: Weeks 1-3 built a forward model, seven methods, and a
metrics layer, but nothing that runs `(condition x method x seed)` at
campaign scale. This module is that, and it is held to four requirements
from `docs/WEEK3-4_PLAN.md` Day 24 -- incremental, resumable, deterministic,
parallel -- because a sweep that silently loses any one of them invalidates
the study's stated reproducibility contribution (`docs/WEEK1-2_AUDIT.md`
item B5).

Design decisions, each against a real alternative:

1. **One Parquet file per CONDITION, not one file for the campaign.** A
   single appended file cannot be made crash-safe without a write-ahead
   log, and cannot be written in parallel without a lock that serialises
   the thing parallelism was for. Per-condition files make "incremental"
   and "parallel" the same mechanism.

2. **Atomic publish via `os.replace`.** Each file is written to
   `<name>.parquet.tmp` and then renamed. `os.replace` is atomic on both
   POSIX and Windows, so a reader can never observe a partial file, so a
   file's EXISTENCE is proof of completeness. Resume is therefore just
   "skip conditions whose file exists" -- no row counting, no checksum
   recovery, no corrupt-file handling, because the corrupt state is
   unreachable by construction.

3. **Rows sorted by `(method_name, seed_index)` before writing.** Worker
   completion order must not reach the bytes on disk. Without this, two
   runs containing identical DATA produce different FILES, which reads as
   nondeterminism and costs a day to diagnose.

4. **Parallelism at the CONDITION level.** Conditions share no mutable
   state. Parallelising over seeds instead would share the resolved
   condition across workers and gain nothing -- the campaign is 14 s
   single-threaded, so parallelism here is for wall-clock comfort during
   development, not necessity.

5. **Condition names are sanitised for the filesystem.** Names contain
   `:` (`axis:amplitude_ratio=1.25`), which is ILLEGAL in Windows
   filenames -- and `docs/WEEK3-4_PLAN.md` Day 26 adds a Windows CI job.
   The unsanitised name is preserved as a column, so the mapping is never
   lossy.

Pipeline position: reads `config.py` + `resolve.py`, calls `simulate.py`
and `methods/`, computes metrics via `metrics.py`/`aggregate.py` and
`harmonics.py`, writes `results/raw/*.parquet`. Day 25's statistics layer
and Day 28's analysis both read it back through `load_results`.
"""

from __future__ import annotations

import os

# Must precede any transitive numpy import in a worker process -- see
# conftest.py's docstring for the measurement showing a post-import
# assignment does NOT take effect, and Day 20's runtime probe for the hard
# crash this prevents (not merely the nondeterminism).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import re  # noqa: E402
from collections.abc import Sequence  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402

from hoqi_bench.aggregate import outcome_from_fit  # noqa: E402
from hoqi_bench.config import SweepConfig  # noqa: E402
from hoqi_bench.forward_model import HENE_WAVELENGTH_M  # noqa: E402
from hoqi_bench.harmonics import cyclic_error  # noqa: E402
from hoqi_bench.methods import timed_fit_by_name  # noqa: E402
from hoqi_bench.resolve import ResolvedCondition, iter_conditions  # noqa: E402
from hoqi_bench.simulate import simulate_condition  # noqa: E402

# The raw table's schema, in order. Fixed here rather than inferred from a
# dict so that a column added by mistake fails loudly instead of silently
# changing every downstream reader's expectations.
RESULT_COLUMNS: tuple[str, ...] = (
    "condition_name",
    "method_name",
    "seed_index",
    "failed",
    "reason",
    "converged",
    "n_iter",
    "displacement_rmse_m",
    "peak_absolute_error_m",
    "phase_rmse_rad",
    "cyclic_first_order_rad",
    "cyclic_second_order_rad",
    "cyclic_conditioning",
    "cyclic_well_conditioned",
    "runtime_s",
)

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._=-]")


def condition_filename(condition_name: str) -> str:
    """Maps a condition name to a filesystem-safe basename.

    `:` and `,` appear in every grid condition's name and `:` is illegal on
    Windows (Day 26's CI matrix includes it). Replacement is a pure
    character substitution, so it is deterministic and collision-free for
    this project's name grammar -- `resolve.py` builds names only from
    parameter names, `=`, `.`, digits, and the separators replaced here.
    """
    return _UNSAFE_FILENAME_CHARS.sub("_", condition_name) + ".parquet"


def run_condition(
    condition: ResolvedCondition,
    methods: Sequence[str],
    n_seeds: int,
    wavelength_m: float = HENE_WAVELENGTH_M,
) -> pd.DataFrame:
    """Every `(method, seed)` for one condition, as a sorted frame.

    Failure mode: a method that RAISES would abort the whole campaign, so
    this is the layer that must not let one through -- but no guard is
    added here, deliberately. Day 20's robustness matrix already proved
    all 7 methods return a `failed` result rather than raising on every
    adversarial input, and `tests/test_robustness_matrix.py` re-checks
    that on every commit. Catching exceptions here would convert a real
    regression in that guarantee into a silently-degraded results table.
    """
    rows = []
    for method_name in methods:
        for seed_index in range(n_seeds):
            signal = simulate_condition(condition.resolved, condition.name, seed_index)
            # timed_fit_by_name, not fit_by_name: populates FitResult.runtime_s
            # (Week 5 Task 3, Day 31 -- docs/WEEK5_PREFLIGHT_AUDIT.md finding
            # P3, previously null in 100% of rows because this call site never
            # went through methods.base.timed_fit). Note this populates
            # runtime_s under WHATEVER execution mode run_condition is called
            # in -- under ProcessPoolExecutor (the default parallel campaign
            # path) that measures scheduler contention as much as algorithm
            # cost, so it is not treated as the authoritative cost figure;
            # see scripts/rq1_cost_measurement.py for the serial,
            # single-worker pass that IS.
            result = timed_fit_by_name(
                method_name,
                signal.i,
                signal.q,
                mean_intensity=condition.resolved["mean_intensity"],
            )
            outcome = outcome_from_fit(result, signal.true_phase, wavelength_m)
            harmonic = cyclic_error(signal.true_phase, result.recovered_phase)
            rows.append(
                {
                    "condition_name": condition.name,
                    "method_name": method_name,
                    "seed_index": seed_index,
                    "failed": outcome.failed,
                    "reason": outcome.reason,
                    "converged": result.converged,
                    "n_iter": result.n_iter,
                    "displacement_rmse_m": outcome.displacement_rmse_m,
                    "peak_absolute_error_m": outcome.peak_absolute_error_m,
                    "phase_rmse_rad": outcome.phase_rmse_rad,
                    "cyclic_first_order_rad": harmonic.first_order_rad,
                    "cyclic_second_order_rad": harmonic.second_order_rad,
                    "cyclic_conditioning": harmonic.conditioning,
                    "cyclic_well_conditioned": harmonic.well_conditioned,
                    "runtime_s": result.runtime_s,
                }
            )

    frame = pd.DataFrame(rows, columns=list(RESULT_COLUMNS))
    # n_iter is a count, only ever populated by Koning (the one iterative
    # method) -- pandas' plain (float64-with-NaN) inference works, but a
    # per-CONDITION frame where n_iter is entirely None (every non-Koning
    # condition after methods that never fail) becomes an all-NA column,
    # and pd.concat across 300+ such files alongside Koning's real integer
    # values triggers a FutureWarning about deprecated all-NA dtype
    # handling (verified directly: reproducible with a minimal synthetic
    # repro of exactly this shape). The nullable Int64 dtype is not an
    # ambiguous "empty" case to pandas' concat logic the way a float64 NaN
    # column is, so it does not trigger the warning -- and it is also the
    # more honest type for a value that is fundamentally a count, never a
    # float.
    frame["n_iter"] = frame["n_iter"].astype("Int64")
    # Design decision 3: sort before writing, so worker scheduling cannot
    # reach the bytes on disk.
    #
    # The explicit annotation on `sorted_frame` (rather than returning the
    # chained expression directly) is load-bearing, not stylistic: CI's
    # Python 3.11 job resolves `pandas>=2.0` to pandas 3.0.5 (a major-
    # version jump from 3.10's 2.3.3), whose stubs type the
    # `sort_values().reset_index()` chain as `Any` in a way 2.x's stubs do
    # not -- caught by mypy strict's `no-any-return` only on 3.11, not
    # locally under 3.10. Binding the fully-chained result to a
    # `pd.DataFrame`-annotated variable before returning is correct under
    # both stub versions.
    sorted_frame: pd.DataFrame = frame.sort_values(["method_name", "seed_index"]).reset_index(
        drop=True
    )
    return sorted_frame


def _run_and_write(args: tuple[ResolvedCondition, list[str], int, Path]) -> str:
    """One worker's whole job. Module-level (not a closure) because
    `ProcessPoolExecutor` pickles the callable."""
    condition, methods, n_seeds, output_dir = args
    frame = run_condition(condition, methods, n_seeds)
    final_path = output_dir / condition_filename(condition.name)
    temp_path = final_path.with_suffix(".parquet.tmp")
    frame.to_parquet(temp_path, index=False)
    os.replace(temp_path, final_path)  # design decision 2: atomic publish
    return condition.name


def run_campaign(
    config: SweepConfig,
    output_dir: Path,
    *,
    n_workers: int | None = None,
    resume: bool = True,
) -> Path:
    """Runs every condition in `config`, writing one Parquet file each.

    `resume=True` skips any condition whose output file already exists.
    That check is sound precisely because of the atomic publish above --
    a file exists only if it was completely written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    conditions = iter_conditions(config)

    pending = [
        condition
        for condition in conditions
        if not (resume and (output_dir / condition_filename(condition.name)).exists())
    ]
    if not pending:
        return output_dir

    jobs = [(c, list(config.methods), config.n_seeds, output_dir) for c in pending]

    if n_workers == 1:
        # Serial path kept explicit rather than a 1-worker pool: it makes a
        # debugging session single-process, and it is the path the
        # worker-count determinism test compares against.
        for job in jobs:
            _run_and_write(job)
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            list(pool.map(_run_and_write, jobs))

    return output_dir


def load_results(output_dir: Path) -> pd.DataFrame:
    """Reads every per-condition file back as one frame, in a
    deterministic order (sorted filename, then the within-file order that
    `run_condition` already fixed)."""
    paths = sorted(output_dir.glob("*.parquet"))
    if not paths:
        raise FileNotFoundError(f"no result files in {output_dir}")
    frames = [pd.read_parquet(path) for path in paths]
    return pd.concat(frames, ignore_index=True)
