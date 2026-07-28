"""
Day 26 -- reproducibility hardening's core evidence: does the smoke
campaign produce the same NUMERICAL result it produced when this test's
reference was recorded, on THIS machine and (via CI's multi-OS matrix) on
every machine.

Why this is a DIFFERENT check from anything Day 24 already has.
`tests/test_runner.py`'s determinism tests only assert INTERNAL
consistency -- run twice in the SAME process, get the same bytes, which is
sound because both runs execute on the identical hardware in the identical
moment. That says nothing about whether the campaign still produces what
it produced yesterday, or on a different machine. `docs/WEEK1-2_AUDIT.md`
item B5 names reproducibility as this project's STATED CONTRIBUTION -- an
internal-consistency check alone does not evidence that claim; a
COMMITTED reference, checked on Linux/macOS/Windows in CI, does.

**Why this test compares NUMBERS, not bytes -- a real finding, arrived at
in two steps, not assumed from the start.**

Step 1: a single exact SHA-256 hash, asserted on every platform, found a
real cross-OS difference -- Linux matched on both Python versions; macOS
produced one different (but internally consistent) hash; Windows a third.
That looked, at first, like "Linux is bit-stable, only macOS/Windows are
not" -- a reasonable-sounding conclusion, and the one first presented to
Nishi, who approved keeping Linux's hash as an exact reference and
checking macOS/Windows numerically instead.

Step 2, on the very next push: Linux ITSELF produced a THIRD hash,
different from its own first run, in a completely isolated pytest process
(not shared state from another test) on nominally the same `ubuntu-latest`
runner label. That falsified the "Linux is bit-stable" premise directly --
GitHub Actions' `ubuntu-latest` maps to a heterogeneous fleet of actual
machines, and numpy's vectorized transcendental functions (`sin`, `cos`,
`arctan2` in `forward_model.py`) and LAPACK routines (`kasa.py`'s
`np.linalg.lstsq`) can legitimately dispatch different underlying CPU
instructions (e.g. AVX2 vs AVX-512) depending on which physical machine a
given run happens to land on -- producing different low-order bits even
under "the same OS label," not just across different OSes.

Presented back to Nishi as an updated, corrected finding (not silently
patched around): the numeric-tolerance check had already passed on every
platform, on every run, including both of Linux's two different hashes --
because the underlying VALUES agree to far better than machine-epsilon-
scale noise; only the exact byte layout differs. Decision: drop the
exact-hash claim entirely rather than keep a Linux-specific guarantee that
had just been shown false. One universal check, on every platform,
against one committed reference, within a documented tolerance -- an
honest claim ("reproducible to floating-point tolerance, everywhere") in
place of a false stronger one ("byte-exact on Linux").

Pipeline position: run by CI's `cross-platform-reproducibility` job
(`.github/workflows/ci.yml`) across a 3-OS x 2-Python-version matrix, in
addition to the regular local/CI suite.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from hoqi_bench.config import load_sweep_config
from hoqi_bench.runner import load_results, run_campaign

SMOKE_CONFIG = Path(__file__).parent.parent / "configs" / "smoke.toml"
REFERENCE_VALUES_CSV = Path(__file__).parent / "fixtures" / "smoke_reference_values.csv"

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

# Calibrated against real cross-platform data, not guessed: passed on
# Linux (twice, two different underlying machines), macOS, and Windows,
# at this tolerance, on the first attempt each time -- far looser than
# machine epsilon (~2.2e-16) so ordinary ULP-level libm/LAPACK differences
# pass comfortably, while remaining many orders of magnitude tighter than
# any real regression this project's own bugs have produced (D1's
# arc-sampling defect was ~1e-2 relative). If a future platform fails at
# this tolerance, that is new information -- widen only with a measured
# reason recorded here, per this project's no-tolerance-without-a-
# measurement convention (docs/journal/day26.md).
_RELATIVE_TOLERANCE = 1e-9
_ABSOLUTE_TOLERANCE = 1e-15


def test_smoke_campaign_matches_reference_values_within_tolerance(tmp_path: Path) -> None:
    """The one reproducibility check this project makes across machines:
    every numeric column, on every platform, within a tolerance wide
    enough for platform-level floating-point noise, tight enough that a
    real algorithmic regression could not hide inside it. Runs identically
    on Linux, macOS, and Windows -- no platform gets a stronger,
    byte-exact guarantee, since none has actually been shown to hold one
    across separate runs (see module docstring)."""
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
