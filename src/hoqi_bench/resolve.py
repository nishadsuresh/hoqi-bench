"""
Resolves a `config.SweepConfig` into the fully-specified, absolute-units
per-condition parameter manifest every simulated run actually needs.

Why this exists: the Weeks 1-2 audit (2026-07-26, docs/WEEK1-2_AUDIT.md) and
its adversarial llm-council review converged on a single root cause behind
several of its findings (F2, F4, F5, F6, F9): there was no compiler between
`docs/PREREGISTRATION.md`'s prose and the runs a harness would actually
execute. Prose named parameters no code read (dc_offset/noise_std described
as fractions of amplitude A, with no conversion layer -- finding F2); a
config could validate cleanly while still being unrunnable (finding F9,
fixed at the schema level in `config.py`, not here). This module is the
missing compiler: given a loaded, ALREADY-VALID `SweepConfig`, it enumerates
every condition and returns each one's fully resolved, absolute-units
parameter dict -- ready to pass directly to `forward_model` and the
transform pipeline, with no further conversion or lookup required.

Pipeline position: consumed by Week 4's sweep harness (not yet built, since
Week 3's methods don't exist yet); `iter_conditions` enumerates the
`n_conditions` half of `SweepConfig.total_runs()`'s `n_conditions * len(methods)
* n_seeds` formula, since which parameter VALUES a condition resolves to
doesn't depend on which method or seed is run against it.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from hoqi_bench.config import FRACTION_OF_AMPLITUDE_PARAMS, REQUIRED_MODEL_PARAMS, SweepConfig


class ResolutionError(ValueError):
    """Raised when a condition cannot be fully resolved to absolute-units
    parameter values. `config.py`'s own validation should make this
    unreachable for any config that loaded successfully (REQUIRED_MODEL_PARAMS
    is checked there too) -- this is defense at the point of use, for any
    `SweepConfig` constructed directly rather than via `load_sweep_config`."""


@dataclass(frozen=True)
class ResolvedCondition:
    """One fully-specified experimental condition.

    name: human-readable identifier, e.g. "axis:amplitude_ratio=1.25" or
        "grid:arc_x_noise:arc_fraction=0.5,noise_std=0.02" -- for logging and
        for the run manifest, not consumed by any simulation code.
    resolved: every `REQUIRED_MODEL_PARAMS` key, resolved to ABSOLUTE units
        (fraction-of-amplitude params already multiplied by A =
        mean_intensity*contrast) -- ready to pass directly to
        `forward_model.simulate_ideal_interferometer` and the transform
        pipeline for this condition.
    """

    name: str
    resolved: dict[str, float]


def _resolve_params(
    overrides: dict[str, float], baseline: dict[str, float]
) -> dict[str, float]:
    """Merges `overrides` onto `baseline` (the OFAT/grid design's "hold
    everything else constant" rule), then converts every
    `FRACTION_OF_AMPLITUDE_PARAMS` entry from a fraction of A =
    mean_intensity*contrast into an absolute value -- the conversion Weeks
    1-2 audit finding F2 found missing entirely: `transforms.dc_offset` and
    `noise.gaussian_noise` take absolute values; `docs/experimental_design.md`
    specifies dc_offset/noise_std/hysteresis_magnitude as fractions of A;
    nothing previously converted between the two, a silent 1.11x error at
    the campaign's own baseline A=0.9.

    Design decision: conversion happens HERE, once, at resolution time --
    not inside `transforms.py`/`noise.py` themselves, which correctly take
    absolute values (a transform shouldn't need to know whether its caller's
    config expressed a parameter as a fraction or not; that's a config-layer
    concern)."""
    merged = {**baseline, **overrides}

    missing = REQUIRED_MODEL_PARAMS - merged.keys()
    if missing:
        raise ResolutionError(
            f"condition is missing resolved value(s) for {sorted(missing)} -- "
            f"baseline + overrides did not cover every required model parameter"
        )

    amplitude = merged["mean_intensity"] * merged["contrast"]
    resolved = dict(merged)
    for name in FRACTION_OF_AMPLITUDE_PARAMS:
        resolved[name] = merged[name] * amplitude

    return resolved


def iter_conditions(config: SweepConfig) -> list[ResolvedCondition]:
    """Enumerates every condition `config.total_runs()` counts towards its
    `n_conditions` term -- each OFAT axis's values (one condition per value,
    every other parameter held at baseline) and each named grid's full cross
    (one condition per combination of its axes' values) -- returning each
    one's fully resolved, absolute-units parameter dict.

    Does NOT multiply by methods or seeds: `total_runs() = n_conditions *
    len(methods) * n_seeds`, and this function enumerates only the
    `n_conditions` half, since which parameter values a condition resolves
    to is independent of which method or seed a harness later runs against it.
    """
    conditions: list[ResolvedCondition] = []

    # ---- 1. OFAT axes: one condition per value, rest held at baseline ----
    for axis_name, values in config.axes.items():
        for value in values:
            conditions.append(ResolvedCondition(
                name=f"axis:{axis_name}={value}",
                resolved=_resolve_params({axis_name: value}, config.baseline),
            ))

    # ---- 2. Named grids: full cross of each grid's own axes ----
    for grid_name, grid_axes in config.grids.items():
        axis_names = list(grid_axes.keys())
        for combo in product(*(grid_axes[name] for name in axis_names)):
            overrides = dict(zip(axis_names, combo, strict=True))
            label = ",".join(f"{name}={val}" for name, val in overrides.items())
            conditions.append(ResolvedCondition(
                name=f"grid:{grid_name}:{label}",
                resolved=_resolve_params(overrides, config.baseline),
            ))

    return conditions
