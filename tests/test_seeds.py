"""
Tests for hoqi_bench.seeds.derive_seed: determinism, distinctness across
inputs, and the paired-comparison property Weeks 1-2 audit finding F3
identified as undecided and unretrofittable after the fact.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench.noise import gaussian_noise
from hoqi_bench.seeds import derive_seed


def test_same_inputs_give_same_seed() -> None:
    assert derive_seed(0, "axis:noise_std=0.02", "gaussian_noise") == derive_seed(
        0, "axis:noise_std=0.02", "gaussian_noise"
    )


def test_different_seed_index_gives_different_seed() -> None:
    a = derive_seed(0, "axis:noise_std=0.02", "gaussian_noise")
    b = derive_seed(1, "axis:noise_std=0.02", "gaussian_noise")
    assert a != b


def test_different_condition_gives_different_seed() -> None:
    a = derive_seed(0, "axis:noise_std=0.02", "gaussian_noise")
    b = derive_seed(0, "axis:noise_std=0.05", "gaussian_noise")
    assert a != b


def test_different_stream_gives_different_seed() -> None:
    """RQ4 compares gaussian_noise and poisson_noise at matched seed_index
    values -- but they must NOT collide the way forward_model and
    gaussian_noise did (finding F3), since they're different noise models
    being compared, not the same draw reused across them."""
    a = derive_seed(0, "axis:noise_std=0.02", "gaussian_noise")
    b = derive_seed(0, "axis:noise_std=0.02", "poisson_noise")
    assert a != b


def test_derived_seed_is_a_valid_rng_seed() -> None:
    """Must actually work as a numpy default_rng seed, not just be some
    large int -- this is the point of contact with real code."""
    seed = derive_seed(7, "axis:amplitude_ratio=1.3", "gaussian_noise")
    rng = np.random.default_rng(seed)
    assert rng.normal(size=5).shape == (5,)


def test_no_method_parameter_exists_in_the_function_signature() -> None:
    """The paired-seed guarantee is structural, not a convention a caller
    could violate: derive_seed has no way to accept a method identifier at
    all, so a harness calling it once per (condition, seed_index) and
    reusing the result across all 7 methods is the only usage the function
    permits."""
    import inspect

    params = inspect.signature(derive_seed).parameters
    assert "method" not in params
    assert set(params) == {"seed_index", "condition_name", "stream"}


def test_reusing_one_derived_seed_across_simulated_methods_gives_identical_noise() -> None:
    """The actual pairing property, demonstrated directly: two 'methods'
    (here, just two independent calls standing in for what would be two
    different phase-recovery methods in Week 3) that both derive their seed
    from the SAME (seed_index, condition_name, stream) must see the
    IDENTICAL noise realization -- the entire point of deriving seeds from
    (condition, seed_index) alone, never from a method identifier."""
    seed = derive_seed(3, "axis:noise_std=0.05", "gaussian_noise")

    intensity_i = np.ones(100)
    intensity_q = np.ones(100)

    # "method A" and "method B" each independently derive the same seed for
    # this (condition, seed_index) and draw noise against it.
    method_a_i, method_a_q = gaussian_noise(intensity_i, intensity_q, 0.05, seed=seed)
    method_b_i, method_b_q = gaussian_noise(intensity_i, intensity_q, 0.05, seed=seed)

    assert np.array_equal(method_a_i, method_b_i)
    assert np.array_equal(method_a_q, method_b_q)
