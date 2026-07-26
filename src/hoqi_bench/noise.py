"""
Detector noise models for hoqi-bench's forward model.

This module starts with the conventional, simplified Gaussian noise model
(this file's `gaussian_noise`) -- intensity-independent, fixed standard
deviation, identical in form to the noise already used in the prior
`quadrature-interferometer-sim` project, kept that way deliberately so
results stay comparable to that earlier, already-validated work.

THIS IS A PHYSICS SIMPLIFICATION, STATED EXPLICITLY: real photodetector shot
noise is signal-dependent (Poisson-distributed, variance scales with
instantaneous intensity), not the fixed, intensity-independent Gaussian
model here. The Gaussian model is used as the conventional starting point in
this literature (matching Heydemann-era and most subsequent ellipse-fitting
papers) because it is simple, well-understood, and analytically tractable
for the classic distortions this is combined with -- not because it is
physically the most accurate choice. Day 12 (`poisson_noise`, in this same
module once built) implements the physically correct, signal-dependent
alternative, and RQ4 (`docs/PREREGISTRATION.md`) directly compares the two
rather than picking one and ignoring the difference.

Equation provenance: matches `quadrature-interferometer-sim`'s
`shot_noise_std`/`thermal_noise_std` parameters in `simulate_interferometer`
(both modeled identically there -- intensity-independent additive Gaussian
noise on each channel) -- combined here into one `noise_std` parameter per
call, since this module's job is to expose the noise model as its own
composable, independently-testable transform (per the architecture in
`pipeline.py`), not to duplicate that project's specific noise-source
naming.

Pipeline position: applied via `pipeline.apply_pipeline`, after the classic
Heydemann shape distortions (`transforms.py`) -- noise is a per-sample,
independent perturbation, so unlike the shape transforms, its position
relative to them doesn't change the result algebraically; applied last by
convention (final step: the shape-distorted signal is what a real detector
would read, and noise is what corrupts that reading).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def gaussian_noise(
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    noise_std: float,
    seed: int | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Adds independent, intensity-independent Gaussian noise (std
    `noise_std`) to each channel. `noise_std=0.0` is an exact identity (both
    channels returned unchanged, no randomness drawn at all -- see the
    early-return below).

    Design decision: I and Q noise are drawn independently (two separate
    calls to the RNG, not the same draw applied to both) -- real photodiodes
    are physically separate devices with uncorrelated electronic noise
    sources; sharing one noise draw between channels would be both
    physically wrong and would silently correlate I and Q in a way that
    could bias downstream ellipse-fitting methods' error estimates.

    Failure mode: none at any parameter value -- Gaussian noise is
    well-defined for any `noise_std >= 0` and any seed.
    """
    if noise_std == 0.0:
        return intensity_i, intensity_q

    rng = np.random.default_rng(seed)
    # Two separate calls (not one call reshaped) to guarantee independence --
    # a single call producing 2N samples split in half would still be
    # independent here, but two calls makes that independence structurally
    # obvious rather than relying on reshaping being done correctly.
    noise_i = rng.normal(0.0, noise_std, size=intensity_i.shape)
    noise_q = rng.normal(0.0, noise_std, size=intensity_q.shape)
    return intensity_i + noise_i, intensity_q + noise_q
