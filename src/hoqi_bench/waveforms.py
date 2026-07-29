"""
Bidirectional (triangle-wave) displacement generator for the RQ3
supplementary hysteresis experiment (Week 5 Task 4, Day 32).

Why this exists: `docs/PREREGISTRATION.md` deviation D5 found that every
preregistered campaign condition's waveform (`arc.build_arc_ramp`) is
strictly monotonic, so `transforms.hysteresis`'s direction-reversal branch
is never exercised -- the main campaign measured direction-INDEPENDENT
radial inflation, not path-dependent hysteresis. This module provides the
one thing that can actually test direction-dependence: a displacement that
travels up to a peak phase excursion and back down, visiting (approximately)
the same phase values twice, once per direction.

Full design specification, and why each choice was made, is committed in
`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 1 -- written and pushed BEFORE
this module existed, per `docs/WEEK5-6_EXECUTION_PLAN.md` §0.6, so the
design predates any result it could have been shaped to produce. This
module is a direct implementation of that already-committed specification;
it does not make any design decision the protocol did not already fix.

Pipeline position: called by Week 5 Task 4's supplementary campaign
(`configs/supplementary_hysteresis.toml`), as `arc.build_arc_ramp`'s
counterpart -- both build the `(t, x_true)` displacement waveform
`simulate.py` composes into a full (I, Q) signal. Never called by the
preregistered main campaign, and never imported by `simulate.py` itself
(that would make the preregistered pipeline depend on a supplementary-only
module) -- a separate supplementary runner script wires this in instead.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray
from hoqi_bench.forward_model import HENE_WAVELENGTH_M


def build_bidirectional_ramp(
    arc_fraction: float,
    n_points: int,
    wavelength_m: float = HENE_WAVELENGTH_M,
) -> tuple[AnyFloatArray, AnyFloatArray]:
    """Builds a triangle-wave displacement `x_true` (and its time array
    `t`) that ramps UP from phase 0 to `arc_fraction * 2*pi`, then back
    DOWN to (just above) 0, over `n_points` total samples.

    Equation provenance / exact sampling formula (committed in
    `docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 1 before this function was
    written): with `peak = arc_fraction * 2*pi`, `n_asc = n_points // 2`,
    `n_desc = n_points - n_asc` --
    - ascending half: `phase[k] = k * peak / n_asc`, `k = 0 .. n_asc - 1`
      (i.e. `linspace(0, peak, n_asc, endpoint=False)`).
    - descending half: `phase[k] = peak - k * peak / n_desc`,
      `k = 0 .. n_desc - 1` (the descending half's FIRST sample is
      exactly `peak`).

    Design decision -- WHY the descending half samples the peak exactly
    once, unlike `arc.build_arc_ramp`'s `endpoint=False` convention on
    BOTH ends: `build_arc_ramp`'s convention exists to avoid double-
    sampling a WRAPAROUND duplicate (phase 0 and phase 2*pi are the same
    physical point on a full circle, per D1). The peak of a triangle wave
    is not a wraparound -- it is a genuine, physically distinct turning
    point, and excluding it would understate the waveform's own peak
    displacement for no principled reason. Verified before this design
    was committed (`docs/SUPPLEMENTARY_PROTOCOLS.md`): the two waveforms'
    SAMPLED maxima are close but not bit-identical (`build_arc_ramp`'s own
    `endpoint=False` maximum falls ~1.7-5% short of the nominal peak,
    shrinking as N grows) -- reported as a known, explained asymmetry
    between the two sampling conventions, not silently equalized.

    Direction-reversal property, verified empirically before this design
    was committed: `sign(gradient(x_true))` is `+1` throughout the
    ascending half and `-1` throughout the descending half, with exactly
    ONE sample at `direction == 0` when `n_points` is even (the single
    symmetric turning-point sample) and ZERO such samples when
    `n_points` is odd -- never a REGION of zero-direction samples.
    `transforms.hysteresis`'s existing formula evaluates to the exact
    identity (`scale = 1.0`) at `direction == 0`, so that single sample
    is automatically, correctly left unperturbed with no changes to
    `transforms.py`.

    Failure mode: `arc_fraction <= 0` produces a degenerate (zero-height)
    triangle -- not guarded here, matching `arc.build_arc_ramp`'s own
    "don't guard against calls this codebase never makes" convention,
    since `docs/experimental_design.md`'s `arc_fraction` range is always
    positive. `n_points < 2` cannot form a two-legged triangle and is
    similarly not guarded, since no caller in this project ever passes
    a `samples_per_fit` that small (`configs/main_campaign.toml`'s own
    range starts at 20).
    """
    peak_phase_rad = arc_fraction * 2 * np.pi

    n_ascending = n_points // 2
    n_descending = n_points - n_ascending

    ascending = np.linspace(0.0, peak_phase_rad, n_ascending, endpoint=False)
    descending = peak_phase_rad - np.linspace(0.0, peak_phase_rad, n_descending, endpoint=False)
    phase_rad = np.concatenate([ascending, descending])

    displacement_m = phase_rad * wavelength_m / (4 * np.pi)
    t = np.linspace(0.0, 1.0, n_points, endpoint=False)

    return t, displacement_m
