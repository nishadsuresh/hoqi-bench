"""
Confirms conftest.py's BLAS-threading pin (docs/WEEK3-4_PLAN.md Part 1, P4)
actually ran for this test session.

Deliberately does NOT re-check the live BLAS thread count via the
ctypes/vendored-.so technique used to empirically verify the fix once
(conftest.py's docstring) -- that technique hardcodes a private, versioned
filename (`numpy.libs/libscipy_openblas64_-<hash>.so`) that WILL change on
any numpy upgrade, which would fail this test for a reason unrelated to
whether determinism is actually broken. Checking `os.environ` instead is
portable and checks the thing this project's code actually controls (the
conftest.py assignment), not a numpy-internal implementation detail.
"""

from __future__ import annotations

import os


def test_blas_thread_env_vars_are_pinned() -> None:
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        assert os.environ.get(var) == "1", (
            f"{var} is {os.environ.get(var)!r}, not '1' -- conftest.py's BLAS pin "
            f"did not take effect for this session"
        )
