"""
Arc-coverage displacement generator: builds the (t, displacement_fn) pair
whose resulting (I, Q) trajectory spans exactly a given fraction of a full
2*pi phase cycle -- the `arc_fraction` measurement-regime parameter named
throughout docs/experimental_design.md and docs/PREREGISTRATION.md (RQ1/RQ2,
the `arc_x_noise` interaction grid) but never implemented until now.

Why this exists (Weeks 1-2 audit, 2026-07-26, finding F5): arc_fraction is
called "the single most consequential axis for numerical stability" (Day 3's
finding) and appears in 99 of the main campaign's 337 (now 359) conditions,
but had zero implementation anywhere in `src/` -- the Week 2 "forward model
complete" claim was premature.

Design decision -- WHY this is a DISPLACEMENT-WAVEFORM generator, not a
post-hoc transform on an already-generated signal: arc coverage models how
much of a fringe cycle a REAL measurement window records (a full ramp
traverses many fringes; a small steady-state vibration dwells within a
fraction of one) -- a property of the experiment's DESIGN (what
displacement waveform and record length were used), not something to crop
out of a fixed-length record after the fact. This is why `arc_fraction`
lives here, alongside `forward_model.py`'s own displacement-generation
concern, rather than in `transforms.py` alongside the pointwise/hysteresis
distortions that operate on an already-generated (I, Q) pair.

Pipeline position: called BEFORE `forward_model.simulate_ideal_interferometer`
to build its `t`/`displacement_fn` arguments for a given arc_fraction
condition; `transforms.py`'s distortions and `noise.py`'s noise models are
then applied to `simulate_ideal_interferometer`'s output exactly as for any
other condition -- arc_fraction changes what signal is generated, not what
happens to it afterward.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray
from hoqi_bench.forward_model import HENE_WAVELENGTH_M


def build_arc_ramp(
    arc_fraction: float,
    n_points: int,
    wavelength_m: float = HENE_WAVELENGTH_M,
) -> tuple[AnyFloatArray, AnyFloatArray]:
    """Builds a linear displacement ramp `x_true` (and its time array `t`)
    whose phase excursion phi = 4*pi*x/wavelength spans EXACTLY
    `arc_fraction * 2*pi` radians over `n_points` samples -- `arc_fraction=1.0`
    is a full 2*pi circle; `arc_fraction=0.05` is an 18-degree arc.

    Design decision: returns `(t, x_true)` -- a precomputed displacement
    array -- rather than `(t, displacement_fn)`, unlike
    `forward_model.simulate_ideal_interferometer`'s own `displacement_fn`
    parameter. A ramp's closed form (`x(t) = total_displacement * t`, `t` in
    [0, 1]) has no free parameters left to defer to a callable once
    `arc_fraction` and `n_points` are fixed, so returning the array directly
    avoids an unnecessary closure; a caller passes `lambda t: x_true`
    (or equivalent) into `simulate_ideal_interferometer` if a callable is
    specifically needed.

    Equation provenance: inverts `forward_model.py`'s
    `phi = 4*pi*x/wavelength_m` for `x`, given a target total phase
    excursion `arc_fraction*2*pi`.

    Design decision -- `endpoint=False`, CHANGED 2026-07-27 (Day 21's
    cross-validation gate), recorded as a dated deviation in
    `docs/PREREGISTRATION.md` and `docs/WEEK3_METHOD_CONTRACT.md`:
    the `n_points` samples sit at the LEFT edge of `n_points` equal
    sub-intervals of a phase window of length exactly `arc_fraction*2*pi`,
    i.e. at `k * arc_fraction*2*pi/n_points` for `k = 0 .. n_points-1`.
    The window covered is still exactly `arc_fraction*2*pi`; the final
    sample sits one step short of its far edge.

    This function originally used `np.linspace(0, 1, n_points)`
    (`endpoint=True`), which at `arc_fraction=1.0` samples phase `0` and
    phase `2*pi` -- THE SAME PHYSICAL POINT -- so one sample in every
    full-circle record was a duplicate. Day 17 found and quantified that
    (`docs/journal/day17.md`, "Bias 1") but deliberately left it, on the
    grounds that changing a load-bearing function to smooth over a bias
    only one estimator was sensitive to was the riskier move. Day 21's gate
    overturned that call with evidence Day 17 did not have:

    - The duplicate makes `mean(I) = I0 + A/n_points` instead of `I0`
      (verified exactly: `A=0.9`, `N=60` gives `1.015`), so Heydemann's
      moment estimator carried a `~1/N` rad phase bias on the
      NOISELESS, UNDISTORTED condition -- measured 3.8e-2 rad RMSE at
      N=20, 1.3e-2 at N=60, 3.9e-3 at N=200, 7.9e-4 at N=1000, against
      1.1e-7 for the other six methods.
    - `arc_fraction=1.0` is the campaign BASELINE, so this applied to
      every condition on every axis except the arc sweep -- not to one
      corner case.
    - The `1/N` scaling lands directly on the preregistered
      `samples_per_fit` axis (RQ6), where it would have produced a clean,
      entirely artifactual "Heydemann's error falls as 1/N" curve, five
      orders of magnitude above every other method, indistinguishable by
      inspection from a real finding about moment-estimator sample
      efficiency.

    All six other methods are unaffected either way (verified: identical
    to ~1e-15 under both conventions), so this is not a change that
    flatters one method -- it removes an artifact that penalised one.
    `endpoint=False` is also the standard periodic-sampling convention: a
    record of `N` samples covering exactly one cycle contains each phase
    exactly once.

    Failure mode: `arc_fraction <= 0` produces a zero or negative total
    displacement excursion, which is degenerate (no phase coverage at all,
    or a direction reversal) -- not guarded here since docs/experimental_design.md's
    own arc_fraction range is always positive ([0.02, 1.0]); a caller
    passing a non-positive value gets a degenerate ramp, not a raised error,
    matching this project's "don't guard against calls this codebase never
    makes" documentation-standard convention.
    """
    total_phase_rad = arc_fraction * 2 * np.pi
    total_displacement_m = total_phase_rad * wavelength_m / (4 * np.pi)

    t = np.linspace(0.0, 1.0, n_points, endpoint=False)
    x_true = total_displacement_m * t

    return t, x_true
