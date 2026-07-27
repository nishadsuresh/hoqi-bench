"""
Method 1 -- raw arctangent, no correction. The deliberately naive baseline
every other Week 3 method (Days 16-20) must beat.

Why a benchmark needs this at all: without a floor, a report of "Heydemann
achieves 0.03% RMS error" has no reference point -- is that good? A
benchmark's whole point is comparison, and the cheapest, most naive thing a
practitioner could do (ignore every distortion, just take the angle) is the
correct zero point for that comparison. If a sophisticated method can't
measurably beat this on distorted data, the sophistication bought nothing.

What atan2 is actually doing: `forward_model.py`'s ideal signal is
`I = mean_intensity*(1+contrast*cos(phi))`, `Q = mean_intensity*(1+contrast*sin(phi))`
-- centering each channel by `mean_intensity` and taking `atan2(Q_ac, I_ac)`
recovers `phi` exactly, because `(I_ac, Q_ac) = contrast*(cos(phi), sin(phi))`
traces a circle and `atan2` is *defined* as the function that inverts
`(cos, sin)` back to an angle, correctly across all four quadrants (unlike
plain `arctan(Q/I)`, which cannot distinguish `phi` from `phi + pi` -- the
same direction-ambiguity `forward_model.py`'s own module docstring names as
the reason quadrature detection exists in the first place).

Why this is "no correction": `mean_intensity` here is a KNOWN, ASSUMED
nominal design constant of the experimental setup (the detector's intended
DC bias point) -- not something estimated FROM the signal. Every other
method (Days 16-20) instead FITS a circle or ellipse to the actual observed
trajectory, recovering its true center/shape directly from the distorted
data. This method skips that step entirely: it has no free parameters, and
consequently no way to compensate for amplitude imbalance, quadrature phase
error, DC offset drift away from the assumed nominal, or any other
distortion -- it will degrade exactly as much as whatever distortion is
injected, which is the point (docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md: this
is the one method the forward model does not favor even structurally, since
it has no correction model to match anything against).

Failure mode: none, structurally -- `np.arctan2` is defined for every real
input pair, including `(0, 0)` (numpy returns `0.0`, not an exception). This
method is the one exception among the 7 planned methods to
`docs/WEEK3_METHOD_CONTRACT.md` §2's fit-failure contract needing real use:
`failed` is always `False` here, since there is no computation that can
fail. Kept as a `FitResult` field regardless, for interface uniformity with
the other 6 methods.

Pipeline position: `methods/__init__.py`'s registry entry `"raw_atan2"`;
consumed identically to every other method by Week 4's sweep runner
(Day 24, not yet built).
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods.base import FitResult

NAME = "raw_atan2"


def fit(intensity_i: FloatArray, intensity_q: FloatArray, mean_intensity: float) -> FitResult:
    """Recovers phase via `atan2(Q - mean_intensity, I - mean_intensity)`
    -- no ellipse or circle fit, no distortion correction. `mean_intensity`
    is the only input beyond the raw signal, and is treated as a known
    constant, not estimated (see module docstring for why that is what
    makes this "no correction").
    """
    recovered_phase = np.arctan2(
        intensity_q - mean_intensity, intensity_i - mean_intensity
    ).astype(np.float64)
    return FitResult(recovered_phase=recovered_phase)
