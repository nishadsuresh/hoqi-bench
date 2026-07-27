"""
Pins BLAS threading to 1 thread, for the whole test session, before numpy is
first imported anywhere in this process.

Why this exists (docs/WEEK3-4_PLAN.md Part 1, P4): determinism under
parallelism is Day 24's highest-risk engineering item (audit item B5 --
reproducibility is this project's STATED CONTRIBUTION and was previously
unevidenced). Multi-threaded BLAS is a real, silent source of
non-determinism -- floating-point summation order (and therefore the exact
bit pattern of a result) can depend on how many threads a BLAS call used,
which can vary run to run even at a fixed random seed. Determinism is far
easier to PRESERVE from day one than to retrofit once results already exist.

Empirically verified for this project's venv (2026-07-27, via ctypes against
the vendored `numpy.libs/libscipy_openblas64_*.so`, calling its
`scipy_openblas_get_num_threads64_`/`_set_num_threads64_` symbols directly):
this build defaults to 32 threads, and setting `OPENBLAS_NUM_THREADS` (or
`OMP_NUM_THREADS`) in `os.environ` BEFORE the BLAS library is first loaded
correctly pins it to 1 -- but setting it AFTER numpy has already been
imported in the same process does NOT retroactively take effect (confirmed:
32 threads persisted). This is why the three assignments below are the
first thing in this file, and why this lives in `conftest.py` specifically
-- pytest guarantees the rootdir `conftest.py` is imported before any test
module is collected, so this reliably predates every test file's own numpy
import for THIS process.

Scope note: this fixes pytest's single-process test runs. Day 24's sweep
runner (not yet built) will additionally need to set these same three
variables in each WORKER process's environment before that worker's own
numpy import -- inherited automatically if workers are spawned via
`subprocess`/`multiprocessing` from a parent whose `os.environ` already has
them set (the standard, portable pattern for this problem; not retrofitted
here since the runner doesn't exist yet).

**Upgraded from "determinism nicety" to "prevents an actual crash," Day 20's
runtime probe**: running the full 125,650-run campaign as a standalone
script (i.e. WITHOUT this file's pin, since a bare `python -c` invocation
never imports `conftest.py`) crashed partway through with
`SystemError: attempting to create PyCFunction with class but no
METH_METHOD flag` -- a low-level numpy/BLAS internal error under sustained
multi-threaded contention across tens of thousands of rapid
`np.linalg` calls. Re-running the IDENTICAL script with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1` set in the
shell environment completed all 125,650 runs cleanly in 14.32 seconds,
zero crashes. This is now a CONFIRMED requirement for Day 24's runner, not
a theoretical one: every worker process must inherit this pin or risks the
exact crash observed here, not just non-deterministic results.

`MKL_NUM_THREADS` is set for portability even though this venv's numpy is
linked against OpenBLAS, not MKL -- Week 4's planned multi-OS CI matrix
(docs/WEEK3-4_PLAN.md Day 26) may hit an MKL-linked numpy build on a
different platform, and setting an irrelevant env var is harmless.
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
