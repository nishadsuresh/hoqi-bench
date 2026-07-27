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
physically the most accurate choice. `poisson_noise` (below, added Day 12)
implements the physically correct, signal-dependent alternative, and RQ4
(`docs/PREREGISTRATION.md`) directly compares the two rather than picking
one and ignoring the difference.

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

from hoqi_bench._types import FloatArray


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
    # ---- 1. Identity case: no noise, no randomness drawn ----
    if noise_std == 0.0:
        return intensity_i, intensity_q

    # ---- 2. Independent noise draws per channel (see design decision above) ----
    rng = np.random.default_rng(seed)
    # Two separate calls (not one call reshaped) to guarantee independence --
    # a single call producing 2N samples split in half would still be
    # independent here, but two calls makes that independence structurally
    # obvious rather than relying on reshaping being done correctly.
    noise_i = rng.normal(0.0, noise_std, size=intensity_i.shape)
    noise_q = rng.normal(0.0, noise_std, size=intensity_q.shape)

    # ---- 3. Combine ----
    return intensity_i + noise_i, intensity_q + noise_q


def poisson_noise(
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    photon_scale: float | None,
    seed: int | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Physically correct, SIGNAL-DEPENDENT shot noise: variance scales with
    instantaneous intensity, unlike `gaussian_noise`'s fixed variance. Built
    as a genuinely separate transform (per this module's docstring) --
    Day 11's `gaussian_noise` is NOT replaced or modified by this function,
    so RQ4 (docs/PREREGISTRATION.md) can compare both on identical
    underlying signals.

    Physical basis: photon arrival at a detector over a fixed integration
    time is a Poisson process -- the probability of detecting exactly k
    photons when lambda are expected is Poisson(lambda), which has the
    defining property Var = mean = lambda. `photon_scale` (photons per unit
    of this simulator's dimensionless intensity) converts continuous
    intensity into a photon-count scale: count = intensity * photon_scale,
    Poisson noise is drawn on that count, then converted back to intensity
    units by dividing by photon_scale. Working through the variance
    algebra: Var(count) = lambda = intensity*photon_scale (Poisson's
    defining property), so Var(intensity_domain_noise) =
    Var(count)/photon_scale^2 = intensity/photon_scale -- variance
    proportional to intensity, exactly the signal-dependent property real
    shot noise has and `gaussian_noise` does not.

    `photon_scale=None` is this transform's identity case (returned
    unchanged, no randomness drawn) -- there is no finite `photon_scale`
    value that turns off shot noise the way `noise_std=0` turns off Gaussian
    noise (any real detector receiving any nonzero light has SOME shot
    noise); `None` is used instead to mean "not modeling this effect,"
    matching this project's general "zero/None means off" convention for
    every other transform without pretending shot noise literally vanishes
    at some intensity.

    Failure mode: `photon_scale` must be positive (excluding None) and
    `intensity * photon_scale` must be non-negative for Poisson's lambda
    parameter to be valid -- this simulator's intensity is always
    non-negative by construction (mean_intensity*(1 +/- contrast) with
    contrast <= 1), so this isn't expected to be hit in practice, but is
    not defended against here with an explicit guard, since a negative
    intensity reaching this function would indicate a bug further upstream
    worth seeing fail loudly (as a numpy warning/NaN), not silently caught.
    """
    # ---- 1. Identity case: not modeling shot noise, no randomness drawn ----
    if photon_scale is None:
        return intensity_i, intensity_q

    # ---- 2. Intensity -> photon count -> Poisson draw -> back to intensity units ----
    rng = np.random.default_rng(seed)

    def _apply(intensity: FloatArray) -> FloatArray:
        photon_count_mean = intensity * photon_scale
        sampled_count = rng.poisson(photon_count_mean).astype(np.float64)
        return sampled_count / photon_scale

    # ---- 3. Independent draws per channel, same rationale as gaussian_noise above ----
    return _apply(intensity_i), _apply(intensity_q)
