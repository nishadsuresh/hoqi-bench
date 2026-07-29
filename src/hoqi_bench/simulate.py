"""
Single canonical path from a resolved experimental condition to the
simulated (I, Q) signal every phase-recovery method (Week 3) and the sweep
runner (Week 4) will consume.

Why this exists (docs/WEEK3-4_PLAN.md Part 1, P1): before this module, the
config-resolve -> forward-model -> transform-pipeline composition existed
only as ad hoc, throwaway glue duplicated in a one-off integration script.
Every method test AND the Day 24 sweep runner would otherwise each
reconstruct this composition independently, with no single place enforcing
the documented pipeline order (pipeline.py's module docstring) or the
paired-seed discipline (seeds.py) -- divergence between two independent
reconstructions would be invisible until results disagreed for no
documented reason.

Composition, in the order pipeline.py's module docstring specifies:
1. `arc.build_arc_ramp` -- the displacement waveform for the condition's
   `arc_fraction` and `samples_per_fit`.
2. `forward_model.simulate_ideal_interferometer` -- ideal (I, Q) from that
   displacement.
3. `transforms.quadrature_phase_error`, THEN `amplitude_imbalance`, THEN
   `dc_offset` -- the classic Heydemann distortions, in the order verified
   in `pipeline.py`.
4. `noise.poisson_noise` THEN `noise.gaussian_noise` -- BOTH applied
   unconditionally, not an either/or choice at this layer. There is no
   "noise model" selector field in `REQUIRED_MODEL_PARAMS`; instead,
   exactly one of the two is ever non-negligible in any single resolved
   condition, by construction of `configs/main_campaign.toml`'s baseline
   (`noise_std=0.0` is `gaussian_noise`'s exact identity; `photon_scale=1e7`
   at the OFAT baseline is `poisson_noise`'s documented "negligible, not
   literally off" placeholder). Applying both unconditionally, relying on
   each one's own identity/negligible behavior at the other axis's
   baseline, is simpler than adding a selector this project's config schema
   does not have. This closes audit finding B6 (docs/WEEK1-2_AUDIT.md):
   `forward_model.py` already had its own noise parameters removed
   (finding F11), so this module is now the ONLY place noise enters a
   simulated condition -- the "silent double application" risk B6 warned
   about is closed structurally (there is nowhere else noise could be
   applied from), not just by convention.

   POISSON MUST COME FIRST, not gaussian-then-poisson as first tried and
   found WRONG when this module's own test suite composed both together
   for the first time (no prior test exercised this combination):
   `poisson_noise` computes `lambda = intensity * photon_scale`, and
   Poisson's `lambda` must be non-negative. Gaussian noise has no such
   domain restriction and, applied first, can push a near-zero-intensity
   sample (this signal's Q channel dips to ~0.03 at its baseline) slightly
   negative -- `rng.poisson` then raises `ValueError: lam < 0`. Poisson
   first avoids this both numerically (its own negligible-baseline
   perturbation can't flip a sample's sign) and physically: shot noise
   is a property of photon detection at the photodiode itself, and
   electronic/readout (Gaussian) noise is introduced downstream in the
   amplifier chain, AFTER photon-to-electron conversion has already
   happened -- so poisson-before-gaussian is the physically ordered
   composition, not an arbitrary tiebreak.
5. `transforms.hysteresis` -- last, per `pipeline.py` (must see whatever
   radius steps 3-4 produced), closing over `x_true` from step 1 for its
   direction-of-travel ground truth (finding F1), not the noisy signal
   steps 3-4 produced.

Each noise model draws from its own SHA-256-derived seed stream
(`seeds.py`), distinguished by stream name (`"gaussian_noise"` vs
`"poisson_noise"`), both derived from the same `(seed_index,
condition_name)` pair -- so a caller running all 7 methods against the same
`seed_index` automatically gets the paired-seed guarantee `seeds.py`'s
docstring requires, without re-deriving it themselves.

Pipeline position: consumed by every Week 3 method's test harness and by
Week 4's sweep runner (not yet built) -- the single place both are meant to
call, rather than each reconstructing this composition independently.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray
from hoqi_bench.arc import build_arc_ramp
from hoqi_bench.forward_model import HENE_WAVELENGTH_M, simulate_ideal_interferometer
from hoqi_bench.noise import gaussian_noise, poisson_noise
from hoqi_bench.pipeline import apply_pipeline
from hoqi_bench.seeds import derive_seed
from hoqi_bench.transforms import amplitude_imbalance, dc_offset, hysteresis, quadrature_phase_error

# A waveform generator matching arc.build_arc_ramp's own signature:
# (arc_fraction, n_points, wavelength_m) -> (t, x_true). Used by
# simulate_condition's waveform_fn parameter (added Week 5 Task 4, Day 32)
# so a supplementary experiment can substitute a different displacement
# generator (e.g. waveforms.build_bidirectional_ramp) without duplicating
# this module's 5-step pipeline composition -- see simulate_condition's
# own docstring for why the default is unchanged for every existing caller.
WaveformGenerator = Callable[[float, int, float], tuple[AnyFloatArray, AnyFloatArray]]


@dataclass(frozen=True)
class SimulatedSignal:
    """The fully-simulated signal for one (condition, seed_index) pair,
    ready to hand directly to a Week 3 phase-recovery method.

    i, q: the distorted, noisy detector signals a method actually sees.
    x_true: ground-truth mirror displacement (meters) -- NOT visible to any
        phase-recovery method; exists for Week 4's metrics to compare
        recovered phase against. Already consumed internally by this
        module's own hysteresis step for direction-of-travel and is not
        re-derived from it -- see module docstring point 5.
    true_phase: `x_true` converted to phase (radians) via this module's
        wavelength -- the ground truth `metrics.wrapped_phase_error`
        compares recovered phase against.
    """

    i: FloatArray
    q: FloatArray
    x_true: FloatArray
    true_phase: FloatArray


def simulate_condition(
    resolved: dict[str, float],
    condition_name: str,
    seed_index: int,
    wavelength_m: float = HENE_WAVELENGTH_M,
    waveform_fn: WaveformGenerator = build_arc_ramp,
) -> SimulatedSignal:
    """Builds the simulated (I, Q) signal for one fully-resolved condition
    (`resolve.ResolvedCondition.resolved` -- already in absolute units, per
    that module's fraction-of-amplitude conversion) and one Monte Carlo
    `seed_index`, applying every transform in the single documented order
    (see module docstring).

    Design decision: `condition_name` and `seed_index` are accepted and
    passed through to `seeds.derive_seed`, rather than a raw seed accepted
    directly -- deliberate, not an inconvenience. It makes the paired-seed
    guarantee structural here too (matching `seeds.py`'s own choice to omit
    a method argument): there is no way to call this function without going
    through the canonical seed derivation.

    `waveform_fn` (added Week 5 Task 4, Day 32, default `arc.build_arc_ramp`
    -- EVERY existing call site's behavior is completely unchanged): lets a
    supplementary experiment substitute a different displacement generator
    (`waveforms.build_bidirectional_ramp`, for RQ3's direction-dependence
    test) without duplicating this function's 5-step pipeline composition
    in a second file -- exactly the divergence-between-independent-
    reconstructions risk this module's own docstring exists to prevent.
    The preregistered main campaign never passes this argument.

    Failure mode: propagates whatever `KeyError` a caller's `resolved` dict
    would raise if missing a `REQUIRED_MODEL_PARAMS` entry -- not
    re-validated here, since `resolve.iter_conditions` is this project's
    only intended producer of `resolved` dicts and already guarantees
    completeness.
    """
    # ---- 1. Displacement waveform for this condition's arc coverage.
    # waveform_fn returns AnyFloatArray (arc.build_arc_ramp's own
    # signature); cast to FloatArray here since this signal-data value
    # flows into hysteresis and SimulatedSignal below, both of which
    # require float64 strictly (per _types.py's FloatArray/AnyFloatArray
    # distinction) ----
    t, x_true_any = waveform_fn(
        resolved["arc_fraction"], int(resolved["samples_per_fit"]), wavelength_m
    )
    x_true: FloatArray = np.asarray(x_true_any, dtype=np.float64)

    # ---- 2. Ideal (I, Q) from that displacement (third return value is the
    # same x_true unchanged, per forward_model.py -- not re-bound here to
    # avoid shadowing the array this function's own step 4 needs) ----
    i0, q0, _ = simulate_ideal_interferometer(
        t,
        lambda _t: x_true,
        wavelength_m=wavelength_m,
        mean_intensity=resolved["mean_intensity"],
        contrast=resolved["contrast"],
    )

    # ---- 3. Independent noise-stream seeds, paired across every method
    # that later calls this function with the same (condition_name,
    # seed_index) -- see seeds.py and module docstring point 4 ----
    gaussian_seed = derive_seed(seed_index, condition_name, "gaussian_noise")
    poisson_seed = derive_seed(seed_index, condition_name, "poisson_noise")

    # ---- 4. The single documented composition (pipeline.py's module
    # docstring): quadrature error -> amplitude imbalance -> DC offset ->
    # poisson noise THEN gaussian noise (poisson first -- see module
    # docstring for why the reverse order raises on this signal) ->
    # hysteresis last, closing over x_true ----
    i, q = apply_pipeline(
        i0,
        q0,
        transforms=[
            lambda a, b: quadrature_phase_error(
                a, b, resolved["mean_intensity"], resolved["quadrature_error_rad"]
            ),
            lambda a, b: amplitude_imbalance(
                a, b, resolved["mean_intensity"], resolved["amplitude_ratio"]
            ),
            lambda a, b: dc_offset(a, b, resolved["dc_offset"], resolved["dc_offset"]),
            lambda a, b: poisson_noise(a, b, resolved["photon_scale"], seed=poisson_seed),
            lambda a, b: gaussian_noise(a, b, resolved["noise_std"], seed=gaussian_seed),
            lambda a, b: hysteresis(
                a, b, resolved["mean_intensity"], resolved["hysteresis_magnitude"], x_true
            ),
        ],
    )

    # ---- 5. Ground-truth phase, for Week 4's metrics to compare against ----
    true_phase = 4 * np.pi * x_true / wavelength_m

    return SimulatedSignal(i=i, q=q, x_true=x_true, true_phase=true_phase)
