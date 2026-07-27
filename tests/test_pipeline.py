"""
Day 8 keystone test: with zero transforms applied, the pipeline's output
must be BIT-IDENTICAL to Day 7's ideal forward model -- not just numerically
close. This is the property every later distortion transform (Days 9-14)
will be held to at its own zero/identity parameter value, and it has to be
true before any real transform is even written.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray
from hoqi_bench.forward_model import simulate_ideal_interferometer
from hoqi_bench.pipeline import apply_pipeline


def test_empty_pipeline_is_bit_identical_to_ideal_model() -> None:
    t = np.linspace(0, 1.0, 2000)

    def displacement_fn(t: AnyFloatArray) -> AnyFloatArray:
        return np.asarray(150e-9 * np.sin(2 * np.pi * 4 * t))

    intensity_i, intensity_q, _ = simulate_ideal_interferometer(
        t, displacement_fn, contrast=0.9
    )

    piped_i, piped_q = apply_pipeline(intensity_i, intensity_q, transforms=())

    # Bit-identical, not just close: an empty pipeline is a pure passthrough.
    assert np.array_equal(piped_i, intensity_i)
    assert np.array_equal(piped_q, intensity_q)


def test_pipeline_is_deterministic_given_the_same_input() -> None:
    """The pipeline itself introduces no randomness -- any nondeterminism in
    the overall simulation must come from forward_model's seed, not from
    apply_pipeline. Calling it twice on identical input must give identical
    output."""
    t = np.linspace(0, 1.0, 500)
    rng = np.random.default_rng(0)
    intensity_i = rng.normal(size=t.shape)
    intensity_q = rng.normal(size=t.shape)

    result_a = apply_pipeline(intensity_i, intensity_q, transforms=())
    result_b = apply_pipeline(intensity_i, intensity_q, transforms=())

    assert np.array_equal(result_a[0], result_b[0])
    assert np.array_equal(result_a[1], result_b[1])


def test_transforms_apply_in_the_given_order() -> None:
    """A minimal check that apply_pipeline genuinely composes transforms in
    sequence (each seeing the previous one's output), using two trivial,
    order-sensitive stub transforms -- not yet the real Day 9-14 transforms,
    just a check on the composition mechanism itself."""

    def add_one_to_i(i: FloatArray, q: FloatArray) -> tuple[FloatArray, FloatArray]:
        return i + 1.0, q

    def double_i(i: FloatArray, q: FloatArray) -> tuple[FloatArray, FloatArray]:
        return i * 2.0, q

    i0 = np.array([1.0, 2.0, 3.0])
    q0 = np.array([0.0, 0.0, 0.0])

    # (1+1)*2 = 4, NOT 1*2+1 = 3 -- order must genuinely matter and be respected.
    result_i, _ = apply_pipeline(i0, q0, transforms=[add_one_to_i, double_i])
    assert np.array_equal(result_i, np.array([4.0, 6.0, 8.0]))
