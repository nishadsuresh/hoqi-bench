"""
Sweep configuration schema: loading, validation, and cost estimation for
hoqi-bench's TOML experiment configs.

Why this exists: docs/experimental_design.md proposes a sweep structure
(one-factor-at-a-time axes plus one 2D interaction grid) that produces a
specific, checkable total_runs count (125,650 for the v2 main campaign, per
docs/PREREGISTRATION.md's revision history). Without a config schema that
computes this number automatically,
"is this sweep combinatorially reasonable" is a hand-calculation someone has
to redo every time the config changes -- exactly the kind of thing Day 5's
task explicitly warns is the most common weakness in benchmark papers
(silently-arbitrary or silently-exploded ranges). This module makes that
number visible and checked before any sweep runs, not after.

Pipeline position: loaded by scripts/run_sweep.py (Day 24) before the main
campaign launches; also directly used by tests/test_config.py's rejection
tests to confirm malformed configs fail loudly and specifically, not
silently or with an unhelpful generic error. `resolve.py` consumes a loaded
`SweepConfig` to produce the actual per-condition parameter manifest.

Weeks 1-2 audit (2026-07-26, findings F2/F4/F5/F6/F9): a config could
previously validate cleanly while covering only SOME of the model's actual
parameters (finding F9 -- `configs/smoke.toml` validated while missing
`dc_offset`/`noise_std`/`quadrature_error_rad` entirely). `_validate` below
now also requires `baseline` to cover `REQUIRED_MODEL_PARAMS` -- every
parameter the forward model/transform pipeline actually consumes, not just
whatever the config happens to sweep -- so a config that cannot fully
specify a run fails at load time, not silently at whatever point Week 4's
harness first reaches for a parameter nobody supplied.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # type: ignore[import-not-found]  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 fallback -- see docs/journal/day00.md

# Every parameter the forward model + transform pipeline actually consumes,
# as of Week 2's composable pipeline (forward_model.py, transforms.py,
# noise.py). A baseline must supply ALL of these -- not just whatever this
# config happens to sweep -- so every condition is fully specified before any
# run starts (Weeks 1-2 audit finding F9).
REQUIRED_MODEL_PARAMS = frozenset({
    "mean_intensity",
    "contrast",
    "amplitude_ratio",
    "quadrature_error_rad",
    "dc_offset",
    "arc_fraction",
    "noise_std",
    "samples_per_fit",
    "hysteresis_magnitude",
    "photon_scale",
})

# Parameters expressed in the config as a FRACTION of oscillation amplitude
# A = mean_intensity * contrast (docs/experimental_design.md's "* A" ranges),
# not as absolute values -- resolve.py converts these before any transform
# call (Weeks 1-2 audit finding F2: transforms.dc_offset/noise.gaussian_noise
# take absolute values, and nothing previously converted between the two,
# a silent 1.11x error at A=0.9).
FRACTION_OF_AMPLITUDE_PARAMS = frozenset({"dc_offset", "noise_std", "hysteresis_magnitude"})

# Parameters that must be INTEGERS, not merely numbers. `samples_per_fit` is
# a sample COUNT: it reaches `np.linspace(..., num=samples_per_fit)` via
# `arc.build_arc_ramp`, which raises TypeError on a float. TOML distinguishes
# `60` from `60.0`, so a config writing the latter would otherwise validate
# cleanly and then crash mid-campaign -- the same "validates but is
# unrunnable" defect class as Weeks 1-2 audit finding F9, caught by an
# end-to-end integration check after that finding's original fix.
INTEGER_MODEL_PARAMS = frozenset({"samples_per_fit"})


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


def _validate(raw: dict[str, object], source: str) -> SweepConfig:
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
                raise ConfigError(
                    f"{source}: grids.{grid_name}.{axis_name} must be a non-empty list"
                )

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

    # Integer-only parameters, checked wherever a value for one can appear
    # (baseline, an OFAT axis, or a grid axis) -- TOML's `60` and `60.0` are
    # different types, and only the former survives reaching np.linspace.
    # `bool` is excluded explicitly: it subclasses int in Python, so
    # `samples_per_fit = true` would otherwise pass an isinstance(_, int) check.
    def _check_integer_param(name: str, value: object, where: str) -> None:
        if name not in INTEGER_MODEL_PARAMS:
            return
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConfigError(
                f"{source}: {where} '{name}' must be an integer, got {value!r} "
                f"({type(value).__name__}) -- it is a sample count and reaches "
                f"np.linspace(num=...), which rejects non-integers"
            )

    for param_name, param_value in baseline.items():
        _check_integer_param(param_name, param_value, "baseline")
    for axis_name, values in axes.items():
        for value in values:
            _check_integer_param(axis_name, value, "axes")
    for grid_name, grid_axes in grids.items():
        for axis_name, values in grid_axes.items():
            for value in values:
                _check_integer_param(axis_name, value, f"grids.{grid_name}")

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

    # Baseline must cover every parameter the model actually consumes, not
    # just whatever this config happens to sweep -- otherwise a condition
    # can validate cleanly and still be unrunnable (Weeks 1-2 audit finding
    # F9: configs/smoke.toml previously passed while missing 3 of these).
    missing_required = REQUIRED_MODEL_PARAMS - baseline.keys()
    if missing_required:
        raise ConfigError(
            f"{source}: 'baseline' is missing required model parameter(s) "
            f"{sorted(missing_required)} -- every parameter the forward model/pipeline "
            f"consumes must have a baseline value, whether or not this config sweeps it"
        )

    return SweepConfig(
        axes=axes, grids=grids, baseline=baseline,
        methods=methods, n_seeds=n_seeds, tolerance=tolerance,
    )
