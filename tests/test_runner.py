"""
Tests for hoqi_bench.runner -- Day 24's sweep runner.

The two tests that matter here are determinism and resumability. A silently
non-reproducible sweep invalidates the entire study (docs/WEEK1-2_AUDIT.md
item B5: reproducibility is this project's STATED contribution), and a
non-resumable one turns any crash into a full restart. Both are asserted
byte-for-byte rather than approximately -- an "almost identical" result
file is exactly the thing that hides a real nondeterminism.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from hoqi_bench.config import load_sweep_config
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.runner import (
    RESULT_COLUMNS,
    condition_filename,
    load_results,
    run_campaign,
)

SMOKE_CONFIG = Path(__file__).parent.parent / "configs" / "smoke.toml"


def _hash_directory(directory: Path) -> str:
    """One hash over every produced file, in sorted filename order."""
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.parquet")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_two_runs_are_byte_identical(tmp_path: Path) -> None:
    """Determinism, asserted the only way that actually proves it."""
    config = load_sweep_config(SMOKE_CONFIG)

    first = tmp_path / "first"
    second = tmp_path / "second"
    run_campaign(config, first, n_workers=2, resume=False)
    run_campaign(config, second, n_workers=2, resume=False)

    assert _hash_directory(first) == _hash_directory(second)


def test_worker_count_does_not_change_results(tmp_path: Path) -> None:
    """The specific nondeterminism this design is built to exclude: if
    output depended on worker scheduling, 1 worker and 4 workers would
    disagree. This is a stronger check than running twice at the same
    worker count, which can pass on a scheduler that happens to be
    repeatable."""
    config = load_sweep_config(SMOKE_CONFIG)

    serial = tmp_path / "serial"
    parallel = tmp_path / "parallel"
    run_campaign(config, serial, n_workers=1, resume=False)
    run_campaign(config, parallel, n_workers=4, resume=False)

    assert _hash_directory(serial) == _hash_directory(parallel)


def test_resume_reproduces_an_uninterrupted_run(tmp_path: Path) -> None:
    """Kill mid-run, restart, verify the result is identical to a clean
    run. Simulated by running the campaign, deleting a subset of the
    output files, and re-running with resume=True -- which exercises the
    same code path a real crash would, without needing to actually kill a
    process mid-write (the atomic publish makes a torn file unreachable,
    so there is no torn state to simulate)."""
    config = load_sweep_config(SMOKE_CONFIG)

    reference = tmp_path / "reference"
    run_campaign(config, reference, n_workers=2, resume=False)
    reference_hash = _hash_directory(reference)

    interrupted = tmp_path / "interrupted"
    run_campaign(config, interrupted, n_workers=2, resume=False)
    produced = sorted(interrupted.glob("*.parquet"))
    assert len(produced) >= 2, "smoke config must have >= 2 conditions for this test"
    for path in produced[: len(produced) // 2 + 1]:
        path.unlink()

    run_campaign(config, interrupted, n_workers=2, resume=True)
    assert _hash_directory(interrupted) == reference_hash


def test_resume_does_not_redo_completed_conditions(tmp_path: Path) -> None:
    """Resume must actually skip, not silently recompute -- otherwise the
    test above would pass even with resume broken."""
    config = load_sweep_config(SMOKE_CONFIG)
    output = tmp_path / "out"
    run_campaign(config, output, n_workers=1, resume=False)

    stamps = {path: path.stat().st_mtime_ns for path in output.glob("*.parquet")}
    run_campaign(config, output, n_workers=1, resume=True)
    for path, stamp in stamps.items():
        assert path.stat().st_mtime_ns == stamp, f"{path.name} was rewritten on resume"


def test_schema_and_row_count_are_exact(tmp_path: Path) -> None:
    config = load_sweep_config(SMOKE_CONFIG)
    output = tmp_path / "out"
    run_campaign(config, output, n_workers=1, resume=False)

    frame = load_results(output)
    assert tuple(frame.columns) == RESULT_COLUMNS
    expected = len(iter_conditions(config)) * len(config.methods) * config.n_seeds
    assert len(frame) == expected


def test_condition_filename_is_windows_safe() -> None:
    """`:` is illegal in Windows filenames and appears in every grid
    condition's name. Day 26 adds a Windows CI job, so this would
    otherwise pass locally and fail on exactly one platform."""
    unsafe = "grid:arc_x_noise:arc_fraction=0.5,noise_std=0.02"
    name = condition_filename(unsafe)
    for character in ':,<>"|?*':
        assert character not in name
    assert name.endswith(".parquet")
    assert condition_filename(unsafe) == name  # deterministic


def test_raw_atan2_has_the_worst_displacement_error_on_the_smoke_grid() -> None:
    """Sanity check on real data, not just structural properties: the
    naive baseline must be the worst method, since every other method
    corrects at least one distortion raw_atan2 cannot. If this fails, the
    wiring is wrong somewhere -- not a finding."""
    config = load_sweep_config(SMOKE_CONFIG)
    output_dir = Path(__file__).parent / "_tmp_runner_sanity"
    try:
        run_campaign(config, output_dir, n_workers=1, resume=False)
        frame = load_results(output_dir)
        means = frame.groupby("method_name")["displacement_rmse_m"].mean()
        assert means["raw_atan2"] >= means["kasa"] - 1e-15
    finally:
        for path in output_dir.glob("*.parquet"):
            path.unlink()
        if output_dir.exists():
            output_dir.rmdir()


def test_failed_fit_still_reports_a_well_conditioned_harmonic_flag() -> None:
    """The D2 caveat, checked directly: a failed fit's cyclic_conditioning
    reflects the true-phase sampling (not the fit), so it can be
    well_conditioned=True with NaN amplitudes. This is not a bug -- it is
    why Day 28 must filter on well_conditioned AND NOT failed, and this
    test exists so that requirement has a concrete check behind it rather
    than only a prose warning."""
    from hoqi_bench.harmonics import cyclic_error
    from hoqi_bench.methods.base import failed_result

    true_phase = np.linspace(0.0, 2 * np.pi, 60, endpoint=False)
    failed = failed_result(60, "synthetic_failure")
    result = cyclic_error(true_phase, failed.recovered_phase)
    assert result.well_conditioned
    assert np.isnan(result.first_order_rad)
    assert np.isnan(result.second_order_rad)
