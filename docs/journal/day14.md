# Day 14 — Hysteresis + full forward-model validation (Week 2 close)

## Hysteresis, with a physical analogy

Picture bending a metal coat hanger back and forth. If you bend it a little and let go, it doesn't
spring back to *exactly* its original shape — there's a small, permanent difference depending on
which direction you last bent it. Magnetic materials have a much cleaner version of this same idea:
the classic "hysteresis loop" plot of magnetization vs. applied field traces a genuinely different
curve depending on whether the field is increasing or decreasing, tracing out a loop instead of
retracing a single line. Interferometer hysteresis is the same shape of problem, in a different
physical setting: whatever residual imperfection remains in the detector response depends not just
on the current phase, but on which direction the phase was moving to get there.

## Why path-dependence is fundamentally harder to correct than static distortion — the conceptual heart of RQ3

Every classic distortion built this week (amplitude imbalance, quadrature phase error, DC offset) is
a *function of phase alone* — given the current phase, the distorted signal is completely determined,
no matter how the system got there. This is exactly what makes ellipse fitting work as a correction
strategy: fit one ellipse to the whole trajectory, and that single fitted shape correctly describes
every point on it, regardless of when or how it was visited. Hysteresis breaks this assumption at
its root: the *same* phase value maps to *two different* (I,Q) points depending on direction of
travel, so there is no single ellipse that correctly describes the whole trajectory — fitting one
ellipse necessarily averages over two genuinely different shapes, and no choice of ellipse parameters
can make that averaging disappear. This is precisely why Lehmann et al. 2025 report their own
attempted fix (fitting a separate ellipse per direction and stitching results) as only a partial
correction, not a solved problem — and it's why RQ3 treats this as the genuinely open edge of the
whole project rather than a box to check off.

## What got built

- **`hysteresis`** in `src/hoqi_bench/transforms.py` — the first transform in this project that
  cannot be pointwise. Every other transform computes its output for sample *i* using only sample
  *i*'s own value; this one needs the *local phase gradient* across neighboring samples to know
  which direction phase is moving at each point, and perturbs radius (not phase) by a fixed amount
  in that direction, preserving angle exactly.
- **`tests/test_hysteresis.py`** — five tests, including confirming (empirically, *before* writing
  the assertion, not guessed) that loop area scales *exactly linearly* with the hysteresis
  magnitude for this specific radial-perturbation model — checked at five magnitudes, ratio constant
  to within 0.1%. A companion test confirms the measurement method itself is sound: zero hysteresis
  gives exactly zero loop area, since a perfectly retraced path has zero signed area by construction.
- **`docs/forward_model_validation_summary.md`** — the full Week 2 summary table this day's task
  calls for: every distortion class, its test count, and the *specific* independently-derived
  analytic property each passing test actually establishes (not just "tests pass").
- **An auto-refine quality pass** over the full Week 2 forward model, using a fresh `quality-judge`
  sub-agent per round. Round 1 scored 7/10 and found a real, checkable violation of
  `docs/DOCUMENTATION_STANDARD.md`: section banners (Rule 2) were present in `config.py` but
  entirely absent from every Week 2 module, plus three minor items (an unused `TRANSFORM_ORDER`
  tuple at risk of drifting out of sync with real call sites, `FloatArray` redefined identically in
  four modules, one unused variable binding). All four fixed — banners added to every function with
  genuinely multiple logical blocks, `TRANSFORM_ORDER` folded into prose documentation (since
  `apply_pipeline` has no real registry to wire it into), `FloatArray` consolidated into a new
  `src/hoqi_bench/_types.py`, the unused binding renamed to `_`. Round 2 scored 8/10, confirmed
  three of four fixes clean, and caught one dangling cross-reference the first fix pass left behind
  (`power_law.py` still named the now-deleted `TRANSFORM_ORDER` tuple) — fixed, verified clean.

## Week 2, closed

47 of 47 tests pass, `ruff check` and `mypy --strict` both clean, across `forward_model.py`,
`pipeline.py`, `transforms.py`, `noise.py`, and `power_law.py`. Every distortion class from the
original 6-week plan (amplitude imbalance, quadrature phase error, DC offset, Gaussian noise,
Poisson noise, power-law characterization, hysteresis) is implemented, tested against an
independently-derived analytic property rather than just "the code runs," and two real bugs were
caught and root-caused along the way — one in the transform composition order itself (Day 8), one in
a test's own arithmetic (Day 9) — both fixed by investigation, not by loosening a tolerance until the
number happened to pass.
