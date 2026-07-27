"""
Circular-statistics error metric for phase-recovery methods.

Why this exists (Weeks 1-2 audit, 2026-07-26, adversarial council review):
recovered phase is periodic (mod 2*pi) -- a method that recovers phase
correct to within a small error near a +-pi wrap boundary (e.g. true phase
= pi - 0.01, recovered = -pi + 0.01) has a TRUE error of 0.02 radians, but a
naive linear difference reports ~2*pi, a ~628x overstatement that would
dominate any RMSE computed the ordinary way. This module exists so Week 3's
methods (Days 15-20) and the Day 22-23 metrics implementation have a single,
correct, pre-built primitive for this rather than each re-deriving (or
forgetting) the wraparound correction independently.

Pipeline position: called by Day 22-23's displacement/phase-error metrics
implementation (not yet built) once Week 3's methods produce recovered
phase; also directly usable by Week 3's own per-method tests. See
docs/WEEK3_METHOD_CONTRACT.md for the full primary-endpoint specification
this module implements one piece of.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray


def wrapped_phase_error(true_phase: AnyFloatArray, recovered_phase: AnyFloatArray) -> FloatArray:
    """Returns the shortest signed angular difference `recovered_phase -
    true_phase`, wrapped into (-pi, pi] -- the CORRECT error metric for
    periodic phase, unlike a naive `recovered_phase - true_phase` which can
    report an error near 2*pi for two phases that are actually adjacent
    across the +-pi wrap boundary.

    Equation provenance: standard circular-statistics wrapping,
    `((x + pi) mod 2*pi) - pi`, applied to the raw difference -- not specific
    to interferometry, a general technique for any periodic quantity.

    Design decision: returns the SIGNED wrapped difference (not absolute
    value) so callers can distinguish a method that's biased in one
    direction from one that's unbiased but noisy -- RMSE, mean signed error,
    and any other aggregate are computed by the caller from this array, not
    baked in here, keeping this function a single-purpose primitive.

    Failure mode: none -- well-defined for any real-valued inputs (this is
    a modular arithmetic operation, not a division or other operation with
    singularities).
    """
    raw_diff = recovered_phase - true_phase
    wrapped = np.mod(raw_diff + np.pi, 2 * np.pi) - np.pi
    return np.asarray(wrapped, dtype=np.float64)
