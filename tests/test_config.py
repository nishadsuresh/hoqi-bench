"""Tests for hoqi_bench.config: loading, validation, and total_runs.

Written first per this project's TDD discipline -- covers both the happy
path (a valid config loads and its total_runs is computed correctly by hand)
and rejection cases (each way a config can be malformed fails with a
specific, useful error, not a generic one or a silent partial load)."""

from __future__ import annotations

import sys
from functools import reduce
from pathlib import Path

import pytest

from hoqi_bench.config import ConfigError, SweepConfig, load_sweep_config

# ---- 1. Happy path: the actual proposed main campaign config ----


def test_main_campaign_config_loads_and_computes_expected_total_runs():
    """docs/experimental_design.md Section 3 hand-computes total_runs=117950
    for the approved, expanded config -- this test confirms the loader
    agrees with that hand computation, not just that it loads without
    crashing. (Approved 2026-07-26: expanded from the original 10290-run
    proposal per Nishad's request -- finer resolution, 30->50 seeds, 3
    interaction grids, Taubin/Koning promoted to required methods.)"""
    config_path = Path(__file__).resolve().parent.parent / "configs" / "main_campaign.toml"
    config = load_sweep_config(config_path)

    assert isinstance(config, SweepConfig)
    assert len(config.methods) == 7
    assert config.n_seeds == 50
    assert config.tolerance == 0.01

    # 10(g) + 10(eps) + 8(dc) + 9(arc) + 10(noise) = 47 OFAT conditions
    n_ofat = sum(len(v) for v in config.axes.values())
    assert n_ofat == 47

    # arc_x_noise (9*10=90) + amplitude_x_quadrature (10*10=100) + amplitude_x_noise (10*10=100)
    n_grid = sum(
        reduce(lambda a, b: a * b, (len(v) for v in grid.values()), 1)
        for grid in config.grids.values()
    )
    assert n_grid == 290

    assert n_ofat + n_grid == 337
    assert config.total_runs() == 337 * 7 * 50
    assert config.total_runs() == 117_950


def test_smoke_config_loads():
    config_path = Path(__file__).resolve().parent.parent / "configs" / "smoke.toml"
    config = load_sweep_config(config_path)
    assert config.total_runs() == 3 * 2 * 5  # 3 conditions x 2 methods x 5 seeds


# ---- 2. total_runs on a hand-constructed config, independent of any file ----


def test_total_runs_ofat_only():
    config = SweepConfig(
        axes={"a": [1, 2, 3], "b": [1, 2]},
        grids={},
        baseline={"a": 1, "b": 1},
        methods=["m1", "m2"],
        n_seeds=10,
        tolerance=0.01,
    )
    # 3 + 2 = 5 conditions * 2 methods * 10 seeds
    assert config.total_runs() == 100


def test_total_runs_with_grid():
    config = SweepConfig(
        axes={},
        grids={"g1": {"a": [1, 2], "b": [1, 2, 3]}},
        baseline={"a": 1, "b": 1},
        methods=["m1"],
        n_seeds=5,
        tolerance=0.01,
    )
    # grid contributes 2*3=6 conditions * 1 method * 5 seeds
    assert config.total_runs() == 30


# ---- 3. Rejection cases: each must fail with a specific error ----


def test_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_sweep_config(tmp_path / "does_not_exist.toml")


def test_rejects_malformed_toml(tmp_path):
    bad_file = tmp_path / "bad.toml"
    bad_file.write_text("this is not [ valid toml =")
    with pytest.raises(ConfigError, match="malformed TOML"):
        load_sweep_config(bad_file)


def test_rejects_missing_required_key(tmp_path):
    """'tolerance' omitted entirely -- must fail with a specific missing-key
    error, not an AttributeError/KeyError leaking from inside the loader."""
    config_file = tmp_path / "missing_key.toml"
    config_file.write_text("""
methods = ["kasa"]
n_seeds = 10

[baseline]
x = 1.0

[axes]
x = [1.0, 2.0]
""")
    with pytest.raises(ConfigError, match="missing required key"):
        load_sweep_config(config_file)


def test_rejects_empty_axis_list(tmp_path):
    config_file = tmp_path / "empty_axis.toml"
    config_file.write_text("""
methods = ["kasa"]
n_seeds = 10
tolerance = 0.01

[baseline]
x = 1.0

[axes]
x = []
""")
    with pytest.raises(ConfigError, match="non-empty list"):
        load_sweep_config(config_file)


def test_rejects_non_numeric_axis_values(tmp_path):
    config_file = tmp_path / "bad_values.toml"
    config_file.write_text("""
methods = ["kasa"]
n_seeds = 10
tolerance = 0.01

[baseline]
x = 1.0

[axes]
x = ["not", "numbers"]
""")
    with pytest.raises(ConfigError, match="only numbers"):
        load_sweep_config(config_file)


def test_rejects_grid_with_fewer_than_two_axes(tmp_path):
    config_file = tmp_path / "bad_grid.toml"
    config_file.write_text("""
methods = ["kasa"]
n_seeds = 10
tolerance = 0.01

[baseline]
x = 1.0

[axes]
x = [1.0]

[grids.only_one_axis]
x = [1.0, 2.0]
""")
    with pytest.raises(ConfigError, match="at least 2 axes"):
        load_sweep_config(config_file)


def test_rejects_empty_methods_list(tmp_path):
    config_file = tmp_path / "no_methods.toml"
    config_file.write_text("""
methods = []
n_seeds = 10
tolerance = 0.01

[baseline]
x = 1.0

[axes]
x = [1.0]
""")
    with pytest.raises(ConfigError, match="non-empty list of method names"):
        load_sweep_config(config_file)


def test_rejects_zero_seeds(tmp_path):
    config_file = tmp_path / "zero_seeds.toml"
    config_file.write_text("""
methods = ["kasa"]
n_seeds = 0
tolerance = 0.01

[baseline]
x = 1.0

[axes]
x = [1.0]
""")
    with pytest.raises(ConfigError, match="positive integer"):
        load_sweep_config(config_file)


def test_rejects_negative_tolerance(tmp_path):
    config_file = tmp_path / "bad_tolerance.toml"
    config_file.write_text("""
methods = ["kasa"]
n_seeds = 10
tolerance = -0.01

[baseline]
x = 1.0

[axes]
x = [1.0]
""")
    with pytest.raises(ConfigError, match="positive number"):
        load_sweep_config(config_file)


def test_rejects_missing_baseline_for_other_swept_param(tmp_path):
    """Sweeping 'x' requires a baseline value for 'y' (held constant while x
    varies) if 'y' is also a swept parameter -- this is the OFAT design's
    core assumption (docs/experimental_design.md Section 3), and a config
    that violates it should fail loudly, not silently use an undefined value
    for y."""
    config_file = tmp_path / "missing_cross_baseline.toml"
    config_file.write_text("""
methods = ["kasa"]
n_seeds = 10
tolerance = 0.01

[baseline]
x = 1.0

[axes]
x = [1.0, 2.0]
y = [1.0, 2.0]
""")
    with pytest.raises(ConfigError, match="requires a baseline value"):
        load_sweep_config(config_file)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
