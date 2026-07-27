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

from hoqi_bench._types import AnyFloatArray, FloatArray

HENE_WAVELENGTH_M: float = 632.8e-9  # HeNe laser, meters


def simulate_ideal_interferometer(
    t: AnyFloatArray,
    displacement_fn: Callable[[AnyFloatArray], AnyFloatArray],
    wavelength_m: float = HENE_WAVELENGTH_M,
    mean_intensity: float = 1.0,
    contrast: float = 0.9,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """
    Generate quadrature (I, Q) detector signals for a given displacement
    waveform. This is the ideal, distortion-free baseline: no amplitude
    imbalance, quadrature phase error, DC offset, or detector noise --
    Week 2's composable transforms (`transforms.py`, `noise.py`) inject every
    non-ideality on top of this function's output, not inside it.

    Audit note (Weeks 1-2 audit, 2026-07-26, finding F11): this function
    used to also accept `shot_noise_std`/`thermal_noise_std`/`mains_amplitude`/
    `drift_amplitude` parameters and inject noise directly. They were never
    referenced by any config, test, or the documented pipeline order in
    `pipeline.py` -- a second, undocumented noise path duplicating `noise.py`,
    with a misleadingly-named `shot_noise_std` that was actually
    intensity-independent Gaussian noise, not physical shot noise. Removed
    rather than fixed in place: `noise.py`'s `gaussian_noise`/`poisson_noise`
    are the single, composable, tested noise path per `pipeline.py`'s
    documented architecture, and a caller wanting noise on this signal should
    go through `pipeline.apply_pipeline`, not through this function.

    Parameters
    ----------
    t : time array (seconds) -- any float precision (matches what
        `np.linspace`/`np.arange` actually return); this function's output is
        always float64 regardless, since every downstream consumer
        (`transforms.py`, `noise.py`, `pipeline.py`) declares that as its
        contract, not something a caller's input precision should affect.
    displacement_fn : callable, x(t) in meters -- the "true" mirror displacement

    Returns
    -------
    (I, Q, x_true) -- the two detector signals and the ground-truth displacement
    (returned for validation, and consumed directly by `transforms.hysteresis`
    for its direction-of-travel ground truth -- see that function's docstring
    for why deriving direction from the noisy measured signal is a category
    error, not a robustness question).
    """
    # ---- 1. Ground-truth displacement and phase ----
    x_true = np.asarray(displacement_fn(t), dtype=np.float64)
    phi = 4 * np.pi * x_true / wavelength_m

    # ---- 2. Ideal quadrature intensities ----
    intensity_i = mean_intensity * (1 + contrast * np.cos(phi))
    intensity_q = mean_intensity * (1 + contrast * np.sin(phi))

    return intensity_i, intensity_q, x_true
