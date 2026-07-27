"""
Composable distortion-transform pipeline for hoqi-bench's forward model.

Why this exists: rather than one large function with every non-ideality
(amplitude imbalance, quadrature phase error, DC offset, noise, power-law,
hysteresis) hardcoded inline, each non-ideality is a separate, independently
testable transform applied in sequence to the ideal (I, Q) signal from
`forward_model.simulate_ideal_interferometer`. This makes each transform's
correctness checkable in isolation (Days 9-14 each test their own transform
against a known analytic property) rather than only checkable as part of one
large, hard-to-debug composite function -- and makes the "at zero distortion,
reproduces the exact ideal signal" property (this file's keystone test)
possible to state and verify precisely, since it's just "apply zero
transforms" or "apply every transform at its identity parameter."

Design decision -- WHY the composition order is quadrature-error-mixing,
THEN amplitude-imbalance-scaling, THEN DC-offset (not the reverse of the
first two, which was tried first and found wrong -- see below):

Day 2's derivation (docs/derivations/heydemann.md) established the combined
distorted signal as a single equation, Q = I0 + A*g*sin(phi+eps). Composing
"apply amplitude imbalance first, then quadrature-error mixing" was tried
first and verified WRONG by direct symbolic check: it leaves a residual term
A*(1-g)*sin(eps)*cos(phi) that only vanishes when g=1. The reason: g is the
Q-channel's overall gain, and it must scale the ENTIRE signal that
physically arrives at that channel -- including whatever cross-talk from the
I channel enters via the quadrature-phase-error mixing -- not just the
channel's "native" sin(phi) content computed before that cross-talk exists.
Composing in the OTHER order (mixing first, on the still-unscaled ideal
signal, then scaling the mixed result by g) was verified to reproduce the
combined formula EXACTLY (symbolic diff = 0, confirmed numerically too).
This order corresponds to the physical picture: quadrature-phase-error is a
property of the optical/geometric relationship between the two channels
(occurs "before" either channel's own amplifier), and each channel's gain
(amplitude imbalance) is applied downstream of that, to whatever signal --
mixed or not -- physically reaches it.

DC offset is additive and commutes with everything else algebraically (it
doesn't multiply or mix with the oscillating content), so its position
relative to the other two doesn't change the math -- applied last here to
match the natural construction order: build the distorted oscillation first,
then add each channel's constant bias on top.

Full documented order, as actually implemented by Days 9-14 (this is prose,
not an executable registry -- `apply_pipeline` takes a caller-supplied list
of already-parameterized callables, per the design decision below, so there
is no single canonical list for real code to consult; the order below is
what every caller in this codebase actually constructs, and what
`test_forward_geometry.py`'s keystone test checks against):
1. `transforms.quadrature_phase_error` -- mixing, on the still-unscaled signal
2. `transforms.amplitude_imbalance` -- scales the whole post-mixing Q content
3. `transforms.dc_offset` -- additive, commutes with 1-2, placed last by convention
4. `noise.gaussian_noise` OR `noise.poisson_noise` -- mutually exclusive in
   practice (RQ4 compares them, doesn't combine them); noise is per-sample and
   independent, so its position relative to 1-3 doesn't change the result
5. `hysteresis` -- must be last: it needs the FINAL phase trajectory (after
   every other distortion) to determine local direction of travel correctly

Pipeline position: `forward_model.simulate_ideal_interferometer` produces
the ideal (I, Q); `apply_pipeline` is called on its output, with a
caller-supplied list of transforms in the order above, before any analysis
method (Days 15-20) sees the signal.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from hoqi_bench._types import FloatArray

# A transform takes (I, Q) and returns the distorted (I, Q). Parameters are
# bound via functools.partial or a lambda at pipeline-construction time, not
# passed through apply_pipeline's signature -- keeps the pipeline itself
# distortion-agnostic (it doesn't need to know what parameters any given
# transform takes).
Transform = Callable[[FloatArray, FloatArray], tuple[FloatArray, FloatArray]]


def apply_pipeline(
    intensity_i: FloatArray,
    intensity_q: FloatArray,
    transforms: Sequence[Transform] = (),
) -> tuple[FloatArray, FloatArray]:
    """Applies each transform in `transforms`, in order, to (I, Q).

    With `transforms=()` (the default), this is a pure passthrough -- the
    keystone property this file's test verifies: zero transforms means
    bit-identical output to whatever `forward_model.simulate_ideal_interferometer`
    produced, with no hidden modification happening in between.
    """
    result_i, result_q = intensity_i, intensity_q
    for transform in transforms:
        result_i, result_q = transform(result_i, result_q)
    return result_i, result_q
