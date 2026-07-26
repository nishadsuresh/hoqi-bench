"""
Sweep configuration schema: loading, validation, and cost estimation for
hoqi-bench's TOML experiment configs.

Why this exists: docs/experimental_design.md proposes a sweep structure
(one-factor-at-a-time axes plus one 2D interaction grid) that produces a
specific, checkable total_runs count (10,290 for the proposed main
campaign). Without a config schema that computes this number automatically,
"is this sweep combinatorially reasonable" is a hand-calculation someone has
to redo every time the config changes -- exactly the kind of thing Day 5's
task explicitly warns is the most common weakness in benchmark papers
(silently-arbitrary or silently-exploded ranges). This module makes that
number visible and checked before any sweep runs, not after.

Pipeline position: loaded by scripts/run_sweep.py (Day 24) before the main
campaign launches; also directly used by tests/test_config.py's rejection
tests to confirm malformed configs fail loudly and specifically, not
silently or with an unhelpful generic error.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 fallback -- see docs/journal/day00.md


class ConfigError(ValueError):
    """Raised for any malformed sweep config, with a message specific enough
    to fix the actual problem (not a generic 'invalid config')."""


@dataclass
class SweepConfig:
    """A validated hoqi-bench sweep configuration.

    axes: OFAT sweep axes, e.g. {"amplitude_ratio": [1.0, 1.05, 1.1, 1.2, 1.3]}.
        Each axis is evaluated independently against `baseline` (Section 3 of
        docs/experimental_design.md's OFAT design).
    grids: named 2D interaction grids, e.g.
        {"arc_x_noise": {"arc_fraction": [...], "noise_std": [...]}} --
        evaluated as a full cross of its two named axes, on top of baseline.
    baseline: the "typical hardware" operating point every axis/grid holds
        constant apart from the parameter(s) being swept.
    methods: names of the phase-recovery methods to run (Day 15-20's Method
        registry; validated only for non-emptiness here, not against the
        actual registry, since that doesn't exist until Day 15).
    n_seeds: Monte Carlo seeds per condition.
    tolerance: relative-error threshold used for breakdown-threshold
        detection (docs/experimental_design.md Section 5).
    """

    axes: dict[str, list[float]]
    grids: dict[str, dict[str, list[float]]]
    baseline: dict[str, float]
    methods: list[str]
    n_seeds: int
    tolerance: float

    def total_runs(self) -> int:
        """Number of individual (method, condition, seed) simulation runs
        this config implies. OFAT axes each contribute len(axis) conditions;
        each named grid contributes the PRODUCT of its two axes' lengths
        (a full cross, per docs/experimental_design.md Section 3's stated
        justification for treating arc_fraction x noise_std differently from
        the OFAT axes)."""
        n_conditions = sum(len(values) for values in self.axes.values())
        for grid in self.grids.values():
            grid_axis_lengths = [len(values) for values in grid.values()]
            product = 1
            for length in grid_axis_lengths:
                product *= length
            n_conditions += product
        return n_conditions * len(self.methods) * self.n_seeds


def load_sweep_config(path: str | Path) -> SweepConfig:
    """Loads and validates a sweep config TOML file. Raises ConfigError with
    a specific message for any structural problem -- never returns a
    partially-valid config."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")

    with open(path, "rb") as f:
        try:
            raw = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"malformed TOML in {path}: {exc}") from exc

    return _validate(raw, source=str(path))


def _validate(raw: dict, source: str) -> SweepConfig:
    # ---- 1. Required top-level keys ----
    required_keys = {"axes", "baseline", "methods", "n_seeds", "tolerance"}
    missing = required_keys - raw.keys()
    if missing:
        raise ConfigError(f"{source}: missing required key(s): {sorted(missing)}")

    axes = raw["axes"]
    grids = raw.get("grids", {})  # optional -- OFAT-only configs are valid
    baseline = raw["baseline"]
    methods = raw["methods"]
    n_seeds = raw["n_seeds"]
    tolerance = raw["tolerance"]

    # ---- 2. Type and shape checks ----
    if not isinstance(axes, dict):
        raise ConfigError(f"{source}: 'axes' must be a table of axis_name -> list of values")
    for axis_name, values in axes.items():
        if not isinstance(values, list) or len(values) == 0:
            raise ConfigError(f"{source}: axes.{axis_name} must be a non-empty list")
        if not all(isinstance(v, (int, float)) for v in values):
            raise ConfigError(f"{source}: axes.{axis_name} must contain only numbers")

    if not isinstance(grids, dict):
        raise ConfigError(f"{source}: 'grids' must be a table of grid_name -> {{axis: [values]}}")
    for grid_name, grid_axes in grids.items():
        if not isinstance(grid_axes, dict) or len(grid_axes) < 2:
            raise ConfigError(
                f"{source}: grids.{grid_name} must define at least 2 axes "
                f"(a grid with fewer than 2 axes should be a plain OFAT axis instead)"
            )
        for axis_name, values in grid_axes.items():
            if not isinstance(values, list) or len(values) == 0:
                raise ConfigError(f"{source}: grids.{grid_name}.{axis_name} must be a non-empty list")

    if not isinstance(baseline, dict) or len(baseline) == 0:
        raise ConfigError(f"{source}: 'baseline' must be a non-empty table of parameter -> value")

    if not isinstance(methods, list) or len(methods) == 0:
        raise ConfigError(f"{source}: 'methods' must be a non-empty list of method names")
    if not all(isinstance(m, str) for m in methods):
        raise ConfigError(f"{source}: 'methods' must contain only strings")

    if not isinstance(n_seeds, int) or n_seeds < 1:
        raise ConfigError(f"{source}: 'n_seeds' must be a positive integer, got {n_seeds!r}")

    if not isinstance(tolerance, (int, float)) or tolerance <= 0:
        raise ConfigError(f"{source}: 'tolerance' must be a positive number, got {tolerance!r}")

    # ---- 3. Cross-reference checks ----
    # Every swept axis (OFAT or grid) must have a corresponding baseline
    # entry for every OTHER parameter -- otherwise "hold everything else at
    # baseline" (the OFAT design's core assumption) is undefined for that run.
    all_swept_names = set(axes.keys())
    for grid_axes in grids.values():
        all_swept_names |= set(grid_axes.keys())

    for swept_name in all_swept_names:
        others_needed = all_swept_names - {swept_name}
        missing_baseline = others_needed - baseline.keys()
        if missing_baseline:
            raise ConfigError(
                f"{source}: sweeping '{swept_name}' requires a baseline value for "
                f"{sorted(missing_baseline)} (held constant while '{swept_name}' varies), "
                f"but baseline is missing {sorted(missing_baseline)}"
            )

    return SweepConfig(
        axes=axes, grids=grids, baseline=baseline,
        methods=methods, n_seeds=n_seeds, tolerance=tolerance,
    )
