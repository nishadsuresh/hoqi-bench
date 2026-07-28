"""
Day 26 -- reproducibility hardening's core evidence: does the smoke
campaign produce the exact same bytes it produced when this test's
reference hash was recorded, on THIS machine and (via CI's multi-OS
matrix) on every machine.

Why this is a DIFFERENT check from anything Day 24 already has.
`tests/test_runner.py`'s determinism tests only assert INTERNAL
consistency -- run twice in the same session, get the same bytes. That
catches non-determinism WITHIN a single environment, but says nothing
about whether the campaign still produces what it produced yesterday, on
a different machine, after a dependency bump. `docs/WEEK1-2_AUDIT.md` item
B5 names reproducibility as this project's STATED CONTRIBUTION -- an
internal-consistency check alone does not evidence that claim; a
COMMITTED reference, checked on Linux/macOS/Windows in CI, does.

Pipeline position: run by CI's `cross-platform-reproducibility` job
(`.github/workflows/ci.yml`) across a 3-OS x 2-Python-version matrix, in
addition to the regular local/CI suite. If this ever fails on a specific
OS, `docs/WEEK3-4_PLAN.md` Day 26's stop-and-ask trigger applies: if the
cause is BLAS-level floating-point non-portability rather than a real
bug, the options (pin a BLAS, relax to tolerance-based comparison, or
document the platform dependence as a finding) go to Nishi, not a
unilateral choice here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from hoqi_bench.config import load_sweep_config
from hoqi_bench.runner import run_campaign

SMOKE_CONFIG = Path(__file__).parent.parent / "configs" / "smoke.toml"

# Recorded 2026-07-28 (Day 26), on Linux, Python 3.10, with the exact
# pinned dependency versions in pyproject.toml (numpy==2.2.6,
# scipy==1.15.3, pandas==2.3.3, pyarrow==25.0.0) -- verified stable across
# 3 repeated local runs before being committed as the reference. A CHANGE
# to this value must be a DELIBERATE, documented decision (a real change
# to the forward model, a method, or the pipeline), never a silent update
# to make a failing CI green -- that would defeat the entire purpose of a
# committed reference.
EXPECTED_SMOKE_CAMPAIGN_HASH = "88a87fb9a72c3fe7704765fef3918fb386d61eed5206c99943410f8719fb2fb1"


def _hash_directory(directory: Path) -> str:
    """Identical to tests/test_runner.py's `_hash_directory` -- NOT
    imported from there, deliberately: this test's reference value must
    stand on its own definition of "the hash," not share a helper whose
    own bug could invalidate both the internal-consistency tests and this
    external-reference test identically."""
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.parquet")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_smoke_campaign_matches_the_committed_reference_hash(tmp_path: Path) -> None:
    """The one test in this project that can fail for a reason that is
    NOT a bug: genuine floating-point non-portability across BLAS
    implementations on different operating systems. If this fails on a
    specific OS in CI, do not loosen this assertion to make it pass --
    that is precisely the failure mode `docs/WEEK3-4_PLAN.md` Day 26
    warns against. Root-cause first (which OS, which columns differ, by
    how much), then escalate per that day's stop-and-ask trigger.
    """
    config = load_sweep_config(SMOKE_CONFIG)
    run_campaign(config, tmp_path, n_workers=1, resume=False)

    actual_hash = _hash_directory(tmp_path)
    assert actual_hash == EXPECTED_SMOKE_CAMPAIGN_HASH, (
        f"Smoke campaign hash drifted: expected {EXPECTED_SMOKE_CAMPAIGN_HASH}, "
        f"got {actual_hash}. This means either (a) a real change to the forward "
        f"model, a method, or the pipeline -- update EXPECTED_SMOKE_CAMPAIGN_HASH "
        f"with a documented reason, or (b) genuine non-determinism -- root-cause "
        f"before touching this constant, per Day 26's stop-and-ask trigger if the "
        f"cause is platform/BLAS-level."
    )
