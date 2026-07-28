"""
Day 26 -- reproducibility hardening's core evidence: does the smoke
campaign produce the same result it produced when this test's reference
was recorded, on THIS machine and (via CI's multi-OS matrix) on every
machine.

Why this is a DIFFERENT check from anything Day 24 already has.
`tests/test_runner.py`'s determinism tests only assert INTERNAL
consistency -- run twice in the same session, get the same bytes. That
catches non-determinism WITHIN a single environment, but says nothing
about whether the campaign still produces what it produced yesterday, on
a different machine, after a dependency bump. `docs/WEEK1-2_AUDIT.md` item
B5 names reproducibility as this project's STATED CONTRIBUTION -- an
internal-consistency check alone does not evidence that claim; a
COMMITTED reference, checked on Linux/macOS/Windows in CI, does.

**Two tiers, not one -- a real cross-platform finding, not a hypothetical
one.** The first version of this test asserted one exact SHA-256 hash on
every platform. Pushed, and CI showed: Linux matched the hash on both
Python versions; macOS produced ONE different hash (identical across its
own two Python versions); Windows produced a THIRD different hash
(likewise identical across its own two Python versions). Each platform is
internally deterministic -- the same OS always produces the same result --
but the three platforms do not agree with each other. That is the exact
signature of genuine floating-point non-portability (transcendental
functions like `sin`/`cos`/`arctan2`, and LAPACK routines like the SVD
`lstsq` uses internally, are not required to round identically across
different platforms' math libraries), not a flaky bug -- a real bug would
not reproduce byte-for-byte identically across two Python versions on each
of three different operating systems.

Presented to Nishi as a decision (per `docs/WEEK3-4_PLAN.md` Day 26's own
stop-and-ask trigger for exactly this scenario), who chose: keep Linux's
exact hash as the source of truth (it matches the environment the actual
125,650-run main campaign, Day 27, will execute in), and verify macOS/
Windows against the SAME reference NUMERICALLY, within a tolerance loose
enough to absorb platform-level floating-point noise but far too tight to
hide a real algorithmic difference.

Pipeline position: run by CI's `cross-platform-reproducibility` job
(`.github/workflows/ci.yml`) across a 3-OS x 2-Python-version matrix, in
addition to the regular local/CI suite.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hoqi_bench.config import load_sweep_config
from hoqi_bench.runner import load_results, run_campaign

SMOKE_CONFIG = Path(__file__).parent.parent / "configs" / "smoke.toml"
REFERENCE_VALUES_CSV = Path(__file__).parent / "fixtures" / "smoke_reference_values.csv"

# Recorded 2026-07-28 (Day 26), on Linux, Python 3.10, with the exact
# pinned dependency versions in pyproject.toml (numpy==2.2.6,
# scipy==1.15.3, pandas==2.3.3, pyarrow==25.0.0) -- verified stable across
# 3 repeated local runs before being committed as the reference. A CHANGE
# to this value must be a DELIBERATE, documented decision (a real change
# to the forward model, a method, or the pipeline), never a silent update
# to make a failing CI green -- that would defeat the entire purpose of a
# committed reference. Confirmed (2026-07-28, first CI run on this job) to
# ALSO hold on both Linux Python versions -- Linux is the only platform
# checked against this exact hash; see module docstring for why.
EXPECTED_SMOKE_CAMPAIGN_HASH = "88a87fb9a72c3fe7704765fef3918fb386d61eed5206c99943410f8719fb2fb1"

# The numeric columns compared against the CSV reference on every
# platform -- the same columns RESULT_COLUMNS defines as floating-point,
# excluding boolean/string/nullable-int columns for which "close within a
# tolerance" isn't a meaningful comparison.
_NUMERIC_COLUMNS = (
    "displacement_rmse_m",
    "peak_absolute_error_m",
    "phase_rmse_rad",
    "cyclic_first_order_rad",
    "cyclic_second_order_rad",
    "cyclic_conditioning",
)

# Calibrated against nothing yet -- this is the FIRST value tried, chosen
# to be far looser than machine epsilon (~2.2e-16) so ordinary ULP-level
# libm/LAPACK differences pass comfortably, while remaining many orders of
# magnitude tighter than any real algorithmic discrepancy this project's
# own bugs have produced (Day 21's arc-sampling defect was ~1e-2 relative;
# a real regression would not hide inside 1e-9). If a future CI run on
# macOS/Windows fails at this tolerance, that is new information -- widen
# only with a measured reason recorded here, per this project's
# no-tolerance-without-a-measurement convention (docs/journal/day26.md).
_RELATIVE_TOLERANCE = 1e-9
_ABSOLUTE_TOLERANCE = 1e-15


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


@pytest.mark.skipif(
    sys.platform != "linux",
    reason=(
        "Byte-identical output is verified against Linux only (the main "
        "campaign's actual execution environment) -- macOS and Windows are "
        "checked numerically instead, see test_smoke_campaign_matches_reference_"
        "values_within_tolerance and this module's docstring for why."
    ),
)
def test_smoke_campaign_matches_the_committed_reference_hash_on_linux(tmp_path: Path) -> None:
    """The strong, exact check -- Linux only, since Linux is where the
    real campaign (Day 27) runs. Root-cause any failure here before
    touching the constant; this is not the test to relax."""
    config = load_sweep_config(SMOKE_CONFIG)
    run_campaign(config, tmp_path, n_workers=1, resume=False)

    actual_hash = _hash_directory(tmp_path)
    assert actual_hash == EXPECTED_SMOKE_CAMPAIGN_HASH, (
        f"Smoke campaign hash drifted on Linux: expected "
        f"{EXPECTED_SMOKE_CAMPAIGN_HASH}, got {actual_hash}. Linux was previously "
        f"exact-match stable across repeated runs and across both supported Python "
        f"versions -- a drift here is NOT the known cross-platform floating-point "
        f"finding this module documents, and must be root-caused as a real bug or "
        f"a real, deliberate change before this constant is touched."
    )


def test_smoke_campaign_matches_reference_values_within_tolerance(tmp_path: Path) -> None:
    """The universal check -- runs on every platform, including Linux
    (where it is a strictly weaker restatement of the exact-hash test
    above, and should never fail if that one passes). Verifies every
    numeric column against the committed CSV reference within a tolerance
    wide enough for platform-level floating-point noise, tight enough that
    a real algorithmic regression could not hide inside it.
    """
    config = load_sweep_config(SMOKE_CONFIG)
    run_campaign(config, tmp_path, n_workers=1, resume=False)
    actual = (
        load_results(tmp_path)
        .sort_values(["condition_name", "method_name", "seed_index"])
        .reset_index(drop=True)
    )

    expected = (
        pd.read_csv(REFERENCE_VALUES_CSV)
        .sort_values(["condition_name", "method_name", "seed_index"])
        .reset_index(drop=True)
    )

    assert list(actual["condition_name"]) == list(expected["condition_name"])
    assert list(actual["method_name"]) == list(expected["method_name"])
    assert list(actual["seed_index"]) == list(expected["seed_index"])

    for column in _NUMERIC_COLUMNS:
        actual_values = actual[column].to_numpy(dtype=np.float64)
        expected_values = expected[column].to_numpy(dtype=np.float64)
        mismatched = ~np.isclose(
            actual_values,
            expected_values,
            rtol=_RELATIVE_TOLERANCE,
            atol=_ABSOLUTE_TOLERANCE,
            equal_nan=True,
        )
        assert not np.any(mismatched), (
            f"{column}: {int(np.sum(mismatched))} of {len(actual_values)} rows exceed "
            f"tolerance (rtol={_RELATIVE_TOLERANCE}, atol={_ABSOLUTE_TOLERANCE}). "
            f"Max relative difference: "
            f"{np.max(np.abs((actual_values - expected_values) / expected_values)):.3e}. "
            f"If this is a NEW platform failure, do not silently widen the tolerance -- "
            f"measure the actual discrepancy magnitude first (per docs/journal/day26.md's "
            f"no-tolerance-without-a-measurement convention) and record the reason."
        )
