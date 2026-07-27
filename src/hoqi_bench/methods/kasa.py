"""
Method 2 -- Kåsa (1976) algebraic circle fit, ported from
`quadrature-interferometer-sim`'s `fit_circle_center`
(`../quadrature-interferometer-sim/src/analysis.py`).

Core idea (`notes/kasa_1976.md`): `(I, Q)` traces a circle
`(I-a)^2 + (Q-b)^2 = r^2`, which expands to `I^2+Q^2 = 2aI + 2bQ +
(r^2-a^2-b^2)` -- LINEAR in `[2a, 2b, (r^2-a^2-b^2)]`, solvable by ordinary
least squares instead of a nonlinear optimization a direct geometric fit
would need. Recovering the center `(a, b)` this way is independent of
oscillation amplitude, frequency, or how many fringes the record spans.

What this method does NOT correct, structurally, per
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`: a circle has no free parameter
for eccentricity or tilt, so `amplitude_ratio` and `quadrature_error_rad`
(which distort a circle into an ellipse) pass through uncorrected -- this
method should track raw atan2's error on those two axes while
outperforming it on `dc_offset` (a circle's center) alone.

**Acceptance criterion, corrected from the original build plan** (per
`docs/WEEK3-4_PLAN.md` Day 16): the plan's stated criterion --
"reproduce 0.0395% displacement RMS error and 0.0019% vibration-frequency
error" -- tests numbers from `quadrature-interferometer-sim`'s FULL
end-to-end pipeline (mains removal, phase unwrapping, FFT-based vibration
detection), none of which this project's method interface builds (a
method here is `(I,Q) -> recovered phase`, nothing more). That criterion
tests something this day does not build. Replaced with a strictly
TIGHTER check: `tests/test_kasa.py` asserts this module's center estimate
is BIT-IDENTICAL to an independent reconstruction of the original
`fit_circle_center`'s exact algorithm, on identical input -- bit-identity
on the actual unit under test, not a percentage match on a downstream
composite this project doesn't have.

Failure mode: NOT characterized here -- `np.linalg.lstsq` does not raise
on a rank-deficient design matrix (e.g. a degenerate all-identical-points
or zero-contrast input); it silently returns a minimum-norm solution
instead. Per `docs/WEEK3-4_PLAN.md`, robustness against exactly these
adversarial inputs is Day 20's task (the full 7-method robustness matrix),
not invented ahead of schedule here -- `failed` is always `False` from
this method today, matching the ported algorithm's own original,
unguarded behavior, port fidelity being this day's actual acceptance bar.

Pipeline position: `methods/__init__.py`'s registry entry `"kasa"`.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods.base import FitResult

NAME = "kasa"


def _fit_circle_center(intensity_i: FloatArray, intensity_q: FloatArray) -> tuple[float, float]:
    """`(I-a)^2 + (Q-b)^2 = r^2` expands to `I^2+Q^2 = 2aI + 2bQ +
    (r^2-a^2-b^2)`, linear in `[2a, 2b, (r^2-a^2-b^2)]`, solved via
    ordinary least squares -- identical algorithm to
    `quadrature-interferometer-sim`'s `fit_circle_center`, ported
    line-for-line (see module docstring for the bit-identity acceptance
    test this port is held to)."""
    design = np.column_stack([intensity_i, intensity_q, np.ones_like(intensity_i)])
    target = intensity_i**2 + intensity_q**2
    coeffs, *_ = np.linalg.lstsq(design, target, rcond=None)
    center_i = coeffs[0] / 2
    center_q = coeffs[1] / 2
    return float(center_i), float(center_q)


def fit(intensity_i: FloatArray, intensity_q: FloatArray) -> FitResult:
    """Fits the circle center directly from the data (no `mean_intensity`
    input, unlike `raw_atan2` -- this is what makes Kasa a real, if
    partial, correction method rather than the floor), then recovers
    phase via `atan2` about that fitted center."""
    center_i, center_q = _fit_circle_center(intensity_i, intensity_q)
    recovered_phase = np.arctan2(intensity_q - center_q, intensity_i - center_i).astype(
        np.float64
    )
    return FitResult(
        recovered_phase=recovered_phase,
        params={"center_i": center_i, "center_q": center_q},
    )
