"""
Seed derivation for hoqi-bench's Monte Carlo sweep, with a paired-comparison
guarantee built into the function signature rather than left as a convention.

Why this exists (Weeks 1-2 audit, 2026-07-26, finding F3): two problems, both
now closed here.

(1) RNG stream collision. `forward_model.simulate_ideal_interferometer(seed=s)`
and `noise.gaussian_noise(seed=s)` were measured to produce a BIT-IDENTICAL
draw at equal seed (correlation exactly 1.000000) -- previously masked only
by an accidental draw-order offset between the two call sites. Finding F11
(forward_model.py) already removes forward_model's own randomness entirely,
so this specific collision is now structurally impossible; this module
exists for the more general problem below, and for any future RNG-consuming
transform this project adds.

(2) Paired vs. unpaired seeds across methods, previously undecided. All 7
methods (Days 15-20) are meant to be evaluated against the SAME noise
realization for a given (condition, seed_index) -- a paired comparison,
which removes the shared noise term from every method-vs-method difference
and meaningfully tightens the resulting confidence intervals, at zero
runtime cost. This is a decision that CANNOT be retrofitted after the main
campaign runs (the audit's own point), so it is fixed here, structurally:
`derive_seed` below takes NO method argument at all -- there is no way for a
caller to accidentally make two methods' noise draws diverge for the same
condition and seed_index, because the function has nothing in its signature
a method name could be passed through.

Pipeline position: consumed by Week 4's sweep harness (not yet built) at the
point where it derives the concrete integer seed to pass to
`noise.gaussian_noise`/`noise.poisson_noise` for a given (condition,
seed_index) pair -- called once per (condition, seed_index), reused across
all 7 methods evaluated against that same seed_index.
"""

from __future__ import annotations

import hashlib

# Number of bytes of the SHA-256 digest consumed to build the derived seed --
# 8 bytes (64 bits) comfortably exceeds numpy's default_rng seed range
# without risking collisions at this project's scale (max ~350 conditions x
# 50 seeds x a handful of streams -- far below the birthday bound for a
# 64-bit space).
_SEED_BYTES = 8


def derive_seed(seed_index: int, condition_name: str, stream: str) -> int:
    """Derives a concrete RNG seed for one (condition, seed_index, stream)
    triple, via SHA-256 of their string concatenation.

    Deliberately excludes any method identifier: this is the paired-seed
    guarantee, enforced structurally rather than by convention -- a harness
    calling this once per (condition, seed_index) and reusing the result
    across all 7 methods' noise draws is the ONLY way to call it, since
    there is no method parameter to (mis)use.

    `stream` distinguishes genuinely different randomness sources within the
    same condition/seed_index (e.g. "gaussian_noise" vs "poisson_noise" --
    RQ4 compares them on paired seed_index values, not on a shared draw,
    since they are different noise MODELS being compared, not the same
    draw reused) -- without `stream`, two different noise models evaluated
    at the same seed_index would otherwise collide exactly as F3 found
    `forward_model` and `gaussian_noise` did.

    Design decision: hash-based rather than a simple arithmetic combination
    (e.g. `seed_index * 1000 + hash(condition_name)`) -- arithmetic
    combination risks structured collisions (e.g. two different
    condition_name/seed_index pairs landing on the same combined integer);
    a cryptographic hash's near-uniform output makes that practically
    impossible to hit by accident, and makes the derivation reproducible
    from its three literal inputs alone, which is the whole point of naming
    it as a documented, dated derivation rule (per the audit's
    recommendation) rather than an ad hoc per-call choice.

    Failure mode: none at any input -- SHA-256 is defined for any input
    string, and the truncation to `_SEED_BYTES` bytes always produces a
    valid non-negative integer.
    """
    payload = f"{seed_index}:{condition_name}:{stream}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:_SEED_BYTES], byteorder="big")
