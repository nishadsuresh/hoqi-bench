# Day 15 — Common interface, raw-atan2 baseline (Week 3 opens)

## Why a benchmark needs a deliberately naive baseline

A report that "Heydemann achieves 0.03% RMS error" means nothing on its own — is that good?
Compared to what? A benchmark's entire job is comparison, and the correct zero point for
that comparison is the cheapest, most naive thing a practitioner could actually do: ignore
every distortion the interferometer might have, and just take the angle. If a sophisticated
method can't measurably beat that on distorted data, the sophistication bought nothing. Raw
atan2 is that floor — Method 1 of 7, and the only one with no correction model at all.

## What atan2 is actually doing

The ideal signal from Day 7's forward model is `I = mean_intensity*(1 + contrast*cos(phi))`,
`Q = mean_intensity*(1 + contrast*sin(phi))`. Subtract `mean_intensity` from each channel and
what's left is `contrast*(cos(phi), sin(phi))` — a point tracing a circle as phase advances.
`atan2(Q_ac, I_ac)` is *defined* as the function that inverts `(cos, sin)` back to an angle,
correctly across all four quadrants — unlike plain `arctan(Q/I)`, which can't tell `phi` from
`phi + pi` (the same ambiguity `forward_model.py`'s own docstring names as the reason
quadrature detection — two detectors instead of one — exists in the first place).

The key word is "no correction": `mean_intensity` here is a known, *assumed* nominal design
constant — not something measured from the data. Every other method (Days 16-20) instead
*fits* a circle or ellipse to the actual observed trajectory, recovering its true center and
shape directly from the distorted signal. Raw atan2 skips that step entirely, so it has no
way to compensate for amplitude imbalance, quadrature phase error, DC offset drift, or
anything else — it degrades exactly as much as whatever distortion is injected. That's not a
weakness to patch; it's the point of a floor.

## What got built

- **`src/hoqi_bench/methods/base.py`** — `FitResult`, the return type every Week 3 method
  will produce, and `PhaseRecoveryMethod`, the calling convention every method's `fit()`
  satisfies. Designed against **Day 20's method**, not today's — Köning's iterative
  errors-in-variables fit needs convergence status, iteration count, and a parameter
  covariance matrix, and building that in now means Days 16-19's tests won't be invalidated
  by a forced interface refactor when Day 20 arrives. Verified directly: a test constructs a
  `FitResult` with every "iterative method" field populated, with zero changes to the
  dataclass itself.
- **`failed_result()`** — a shared factory for `docs/WEEK3_METHOD_CONTRACT.md`'s
  fit-failure contract (every numeric field NaN, `failed=True`, a *specific* reason code).
  One factory means the "every field NaN" rule can't be gotten subtly wrong in one method but
  not another once six more methods start using it.
- **`timed_fit()`** — the one place runtime is measured, wrapping any method's `fit()` call
  rather than asking all 7 implementations to self-time correctly and consistently.
- **A real design deviation, recorded in `base.py`'s own docstring**: the Week 3-4 plan's
  draft phrasing described a `typing.Protocol` with a `.name` attribute and a bound `.fit()`
  method — implying method-as-class-instance. Built instead as plain `NAME` constants plus
  `fit()` functions, collected into a `methods/__init__.py` registry dict. Every other module
  in this codebase (`transforms.py`, `noise.py`, `simulate.py`) is functional; introducing
  the first behavioral class here would be a real style discontinuity for no benefit a
  registry dict doesn't already provide.
- **`src/hoqi_bench/methods/raw_atan2.py`** — Method 1.
- **`tests/test_methods_base.py`**, **`tests/test_raw_atan2.py`** — 8 tests: near-exact on a
  fully clean condition, measurable degradation under a real preregistered
  `amplitude_ratio=1.3` condition, and a structural-failure-mode check (atan2 is defined
  everywhere, including the degenerate all-zero input).

## A test bug, caught by actually running the test

The first version of the "near-exact on clean data" test asserted RMSE `< 1e-4` rad and
failed at the real value, 3.98e-4. Not a bug in `raw_atan2` — the tolerance was picked as a
round number instead of derived. `configs/main_campaign.toml`'s baseline `photon_scale=1e7`
is documented (`noise.py`) as "negligible, not literally off": working through the actual
formula (`Var(intensity noise) = intensity/photon_scale`, then converting a small radial
perturbation to a phase error via `/contrast`) predicts almost exactly the observed
3.98e-4 rad. Fixed by deriving the tolerance from the same formula the noise model itself
documents, with a 5x margin for the approximation's own looseness — grounded, not guessed.

## Status

93/93 tests passing (was 85; +8), ruff clean, mypy --strict clean (36 files). `raw_atan2` is
live in `methods.METHOD_REGISTRY`. Day 16 next: port Kasa from
`quadrature-interferometer-sim`, with a corrected acceptance criterion (per
`docs/WEEK3-4_PLAN.md` — the original plan's "reproduce 0.0395%/0.0019%" criterion tests a
downstream composite this project's method interface doesn't build; replaced with bit-
identical port fidelity against the source project's own `fit_circle_center`).
