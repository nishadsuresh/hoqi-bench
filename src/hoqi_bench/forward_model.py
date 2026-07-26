"""
Ideal (distortion-free) Michelson interferometer forward model, with
quadrature (I/Q) homodyne detection.

Why this exists: this is the validated baseline every method in hoqi-bench is
compared against, and every distortion transform (Week 2, Days 8-14) is
layered on top of. Ported directly from the `quadrature-interferometer-sim`
project (Day 7's ACCEPTANCE test: must reproduce that project's exact
0.000000% fringe-spacing error against lambda/2 -- if it doesn't, either this
port or the original is wrong, and the port is investigated before anything
else is built on top of it).

Design decision (carried over from the source project, not re-derived here):
a naive single-photodiode approach fails with a fundamental direction
ambiguity (cos(phi) can't distinguish +phi from -phi). Quadrature detection --
two detectors 90 degrees apart -- resolves this via atan2(Q, I).

Physics: for a Michelson interferometer with one mirror displaced by x(t),
the round-trip path length change is 2x(t), so the phase is
    phi(t) = 4*pi*x(t) / lambda
The two quadrature detector intensities are
    I(t) = I0 * (1 + V*cos(phi(t)))
    Q(t) = I0 * (1 + V*sin(phi(t)))
where V is fringe visibility/contrast (0..1) and I0 is mean intensity.

Pipeline position: called by every method's test harness (Days 15-20) to
generate the ideal signal; Week 2's distortion transforms (Days 9-14) take
this function's output as their input.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

HENE_WAVELENGTH_M: float = 632.8e-9  # HeNe laser, meters


def simulate_ideal_interferometer(
    t: NDArray[np.float64],
    displacement_fn: Callable[[NDArray[np.float64]], NDArray[np.float64]],
    wavelength_m: float = HENE_WAVELENGTH_M,
    mean_intensity: float = 1.0,
    contrast: float = 0.9,
    shot_noise_std: float = 0.0,
    thermal_noise_std: float = 0.0,
    mains_amplitude: float = 0.0,
    mains_freq_hz: float = 60.0,
    drift_amplitude: float = 0.0,
    drift_freq_hz: float = 0.1,
    seed: int | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """
    Generate quadrature (I, Q) detector signals for a given displacement
    waveform, with optional realistic noise sources -- but no ellipse
    distortion (amplitude imbalance, quadrature phase error, DC offset). This
    is the ideal baseline; Week 2's transforms (Days 9-14) inject distortion
    on top of this function's output, not inside it.

    Parameters
    ----------
    t : time array (seconds)
    displacement_fn : callable, x(t) in meters -- the "true" mirror displacement
    shot_noise_std : shot-like noise (modeled as intensity-independent additive
        Gaussian here for simplicity -- true shot noise scales with sqrt(signal);
        see Day 12's Poisson shot-noise transform for the physically correct model)
    thermal_noise_std : detector thermal (Gaussian) noise
    mains_amplitude, mains_freq_hz : 60Hz electrical pickup
    drift_amplitude, drift_freq_hz : slow low-frequency drift (thermal/mechanical)

    Returns
    -------
    (I, Q, x_true) -- the two detector signals and the ground-truth displacement
    (returned for validation; a real system would not have x_true).
    """
    rng = np.random.default_rng(seed)

    x_true = displacement_fn(t)
    phi = 4 * np.pi * x_true / wavelength_m

    intensity_i = mean_intensity * (1 + contrast * np.cos(phi))
    intensity_q = mean_intensity * (1 + contrast * np.sin(phi))

    mains = mains_amplitude * np.sin(2 * np.pi * mains_freq_hz * t)
    drift = drift_amplitude * np.sin(2 * np.pi * drift_freq_hz * t)

    intensity_i = (
        intensity_i
        + mains
        + drift
        + rng.normal(0, shot_noise_std, size=t.shape)
        + rng.normal(0, thermal_noise_std, size=t.shape)
    )
    intensity_q = (
        intensity_q
        + mains
        + drift
        + rng.normal(0, shot_noise_std, size=t.shape)
        + rng.normal(0, thermal_noise_std, size=t.shape)
    )

    return intensity_i, intensity_q, x_true
