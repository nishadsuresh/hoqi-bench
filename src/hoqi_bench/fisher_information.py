"""
Closed-form Fisher information / Cramer-Rao bound for phase estimation
under this project's forward model, used ONLY as a scalar "how hard is
this estimation problem" proxy for matching Poisson noise (`photon_scale`)
to Gaussian noise (`noise_std`) at equivalent difficulty -- Week 5 Task 5,
Day 33, RQ4.

Why this exists (`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 2, adopted
from an `llm-council` verdict): comparing method rankings under Poisson
vs. Gaussian noise "at matched noise level" requires defining what
"matched" means, and no single scalar (sigma, SNR) is uncontroversial,
because Poisson noise is signal-dependent (variance scales with
instantaneous intensity) while Gaussian noise is uniform -- two axes can
share the same AVERAGE sigma while differing in how that noise is
distributed across a fringe cycle. Fisher information resolves this at
the level the two axes can actually be compared: not "do the noise
distributions look alike," but "how much information about the phase does
a measurement under this noise model carry." The peer-reviewed correction
behind this module's existence: this is a property of the MEASUREMENT
MODEL (signal shape + noise type), computable in closed form from the
resolved condition's own parameters, not of any particular one of the 7
correction algorithms -- it is never used here to claim any method
achieves this bound.

Equation provenance: standard Fisher information for a scalar parameter
phi estimated from independent, approximately-Gaussian-distributed
measurements (I, Q) with known, phi-dependent variances --
    FI(phi) = (dI/dphi)^2 / Var(I|phi) + (dQ/dphi)^2 / Var(Q|phi)
(e.g. Kay, "Fundamentals of Statistical Signal Processing," Ch. 3) summed
over every sample in a fit (independence across samples is the same
assumption every method's least-squares/EIV fit in this project already
makes). CRB(phi) = 1 / FI(phi) is the corresponding lower bound on any
unbiased estimator's phase variance -- reported here as a difficulty
proxy only, per this module's docstring above, never as a claim about
what any of the 7 implemented methods actually achieve.

The forward model this module differentiates -- `docs/derivations/
heydemann.md` Section 2's combined-signal equation, ALREADY VERIFIED to
be exactly what `transforms.py`'s composition produces
(`transforms.py`'s own module docstring): with `A = mean_intensity *
contrast`,
    I(phi) = mean_intensity + A * cos(phi)
    Q(phi) = mean_intensity + A * amplitude_ratio * sin(phi + quadrature_error_rad)
`dc_offset` is purely additive (both `transforms.dc_offset`'s own
docstring and `docs/derivations/heydemann.md`) and does not appear in
either derivative below.

Pipeline position: called by `scripts/rq4_analysis.py` to build the
matched-Fisher-information pairing between `photon_scale` and `noise_std`
grid points. Never imported by any preregistered-campaign code path
(`simulate.py`, `runner.py`) -- this module computes a property OF a
resolved condition, it does not generate signal data.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray


def _oscillation_amplitude(mean_intensity: float, contrast: float) -> float:
    return mean_intensity * contrast


def total_fisher_information_gaussian(
    phi_samples: AnyFloatArray,
    mean_intensity: float,
    contrast: float,
    amplitude_ratio: float,
    quadrature_error_rad: float,
    noise_std_absolute: float,
) -> float:
    """Total Fisher information for phase, summed over `phi_samples`,
    under GAUSSIAN noise with the SAME absolute standard deviation on
    both channels (matching `noise.gaussian_noise`'s own documented
    behavior -- independent draws, identical `noise_std` passed to both
    channels).

    Failure mode: `noise_std_absolute == 0.0` gives infinite Fisher
    information (noiseless measurement carries perfect information about
    phase, in this idealized model) -- returns `float("inf")` rather than
    raising, since this is the mathematically correct answer, and the
    caller (matching against a nonzero Poisson condition) is expected to
    treat an infinite value as "cannot be matched," not as an error.
    """
    if noise_std_absolute == 0.0:
        return float("inf")

    amplitude = _oscillation_amplitude(mean_intensity, contrast)
    di_dphi = -amplitude * np.sin(phi_samples)
    dq_dphi = amplitude * amplitude_ratio * np.cos(phi_samples + quadrature_error_rad)

    variance = noise_std_absolute**2
    fi_per_sample = (di_dphi**2 + dq_dphi**2) / variance
    return float(np.sum(fi_per_sample))


def total_fisher_information_poisson(
    phi_samples: AnyFloatArray,
    mean_intensity: float,
    contrast: float,
    amplitude_ratio: float,
    quadrature_error_rad: float,
    photon_scale: float,
) -> float:
    """Total Fisher information for phase, summed over `phi_samples`,
    under POISSON (signal-dependent) noise -- `Var(I|phi) = I(phi) /
    photon_scale`, `Var(Q|phi) = Q(phi) / photon_scale`, per
    `noise.poisson_noise`'s own documented variance derivation
    (`Var(intensity-domain noise) = intensity / photon_scale`).

    Unlike the Gaussian case, the variance itself depends on phi (through
    I(phi), Q(phi)), so this is NOT a constant divided out of a sum of
    squared derivatives -- each sample's contribution is computed with
    its own local variance.

    Failure mode: `I(phi)` or `Q(phi)` going non-positive would make a
    variance non-positive, which is unphysical for a photon-counting
    process -- not guarded here. This module is only ever called at
    `configs/main_campaign.toml`'s shared classic-distortion baseline
    (`amplitude_ratio=1.1`, `quadrature_error_rad=0.1`, RQ4's noise axes
    never sweep these), where I ranges [0.10, 1.90] and Q ranges
    [0.01, 1.99] -- both strictly positive, verified directly, not
    assumed (docs/journal/day33.md). This is NOT true at every grid value
    of `amplitude_ratio` (e.g. `amplitude_ratio=1.5` pushes Q's minimum
    negative) -- a caller passing a condition swept on that axis would
    need to add a guard this module deliberately omits, since RQ4 never
    calls it that way.
    """
    amplitude = _oscillation_amplitude(mean_intensity, contrast)

    intensity = mean_intensity + amplitude * np.cos(phi_samples)
    quadrature = mean_intensity + amplitude * amplitude_ratio * np.sin(
        phi_samples + quadrature_error_rad
    )

    di_dphi = -amplitude * np.sin(phi_samples)
    dq_dphi = amplitude * amplitude_ratio * np.cos(phi_samples + quadrature_error_rad)

    var_i = intensity / photon_scale
    var_q = quadrature / photon_scale

    fi_per_sample = (di_dphi**2 / var_i) + (dq_dphi**2 / var_q)
    return float(np.sum(fi_per_sample))
