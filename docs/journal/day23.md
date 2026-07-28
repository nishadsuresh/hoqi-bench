# Day 23 — Cyclic-error harmonics, and why an FFT would have quietly ruined a quarter of the campaign

## What a cyclic error even is

Once a method recovers phase, subtract the true phase and look at what's left. If the method
corrected every distortion perfectly, that leftover is just noise — no shape to it. But if the
method missed some nonlinearity, the leftover isn't random: it repeats once or twice per fringe,
because the distortion is a fixed function of *where you are* on the ellipse, not of time. So the
residual looks like `A₁·sin(φ + θ₁) + A₂·sin(2φ + θ₂) + noise` — a first-order wiggle and a
second-order wiggle, each with its own amplitude and phase offset. `A₁` and `A₂` are exactly what
every interferometry calibration paper reports as "cyclic error," and it's a preregistered metric
here (`docs/PREREGISTRATION.md`'s Metrics section names it explicitly).

Recovering `A₁` and `A₂` from a residual is today's whole task.

## The estimator: least squares, not an FFT — and this was checked, not assumed

The first instinct for "find the amplitude at a known frequency" is an FFT. It would have been
wrong here, and wrong silently.

An FFT's frequency bins only mean what you think they mean if your record spans a whole number of
periods. This project's `arc_fraction` axis exists specifically because real measurements often
*don't* — 99 of the campaign's 359 conditions have `arc_fraction < 1.0`, meaning the record covers
only part of a fringe cycle. I checked what an FFT does there before writing anything: inject
`A₁ = 0.05`, `A₂ = 0.03` into a residual, sample it at `arc_fraction = 0.5`, take the FFT.
Bin 1 reports 0.0311 (38% too low). Bin 2 reports 0.0074 (75% too low). The bins simply aren't
the harmonics anymore once the record isn't a full cycle.

The fix is to project the residual onto `cos(kφ)` and `sin(kφ)` — evaluated at the actual known
true phase, not at sample index — by ordinary least squares, for `k = 1, 2`. That's linear
regression, not a Fourier transform, and it doesn't care whether the sampled φ range is a full
circle or a sliver of one. Checked the same way: exact to 1e-16 at every `arc_fraction` from 1.0
down to 0.02, noiseless. This is real algebra, not an approximation that happens to work at full
arc.

## The actual finding: exact algebra is not the same as a usable estimator

Here's the part that would have bitten silently if I'd shipped the least-squares version without
checking further. Being *algebraically* exact on clean data says nothing about what happens with
real noise on a small arc.

The reason: `cos(φ), sin(φ), cos(2φ), sin(2φ)` all look nearly identical to each other when φ only
covers a small slice of a cycle — imagine trying to tell a slow wiggle from a fast wiggle by
looking at one-tenth of a period of each. The regression can't tell them apart anymore, so it
starts assigning noise to whichever harmonic happens to fit slightly better, and the reported
amplitude becomes essentially arbitrary — but it never raises an exception. It just returns a
number, confidently, that has nothing to do with the truth.

I measured exactly how bad, over 200 seeds at N=60 with realistic residual noise (σ=0.005),
injecting `A₁=0.05`, `A₂=0.03`:

| `arc_fraction` | design-matrix condition number | median A₁ error | median A₂ error |
|---|---|---|---|
| 1.0 (full circle) | 1.00 | 1.3% | 2.1% |
| 0.5 | 3.50 | 1.4% | 2.7% |
| 0.35 | 10.25 | 1.6% | 9.2% |
| 0.25 | 33.4 | 6.1% | 19.4% |
| 0.15 | 180.9 | 34.1% | 35.4% |

The condition number of the regression's design matrix — a standard measure of "how close to
degenerate is this problem" — tracks the degradation almost perfectly, and it's something you can
compute directly from the data rather than having to guess from `arc_fraction` alone (which the
estimator function doesn't even receive — the check has to be a property of the actual phase
samples, not an assumed cause).

## The fix: report the conditioning, don't hide the result

I didn't make the estimator refuse to answer at small arc. That would throw away real information
— the numbers are *exact* on clean data even at `arc_fraction = 0.02`, so small arc isn't a
correctness bug, it's a noise-sensitivity issue. Instead, `cyclic_error()` returns the design
matrix's condition number and a `well_conditioned` flag alongside both amplitudes, always. The
threshold — `cond ≤ 10.0` — is the largest value at which the *harder* of the two amplitudes
(second-order, which degrades faster) stays under 10% median relative error at the campaign's own
realistic noise level. That corresponds to about `arc_fraction ≈ 0.35`.

This is the same pattern `aggregate.py` already uses for `is_rankable`: a hard condition still
gets its numbers reported, it just doesn't get to contribute to a ranking or an aggregate without
a caveat attached.

## A wrinkle found while wiring this into the sweep runner (Day 24)

`conditioning` only depends on how the true phase was sampled — it has nothing to do with whether
the *fit itself* succeeded. So a method that failed outright (all-NaN recovered phase) still
reports `well_conditioned = True`, because the phase sampling really was fine; the fit just
produced garbage. That means filtering on `well_conditioned` alone won't exclude failed fits —
Day 28's analysis needs to filter on `well_conditioned AND NOT failed`. Recorded in
`docs/PREREGISTRATION.md`'s D2 deviation note so it isn't rediscovered the hard way later.

## What was verified before trusting any of this

- Least-squares recovery of known amplitudes to 1e-12 or better, at every arc_fraction from 0.02
  to 1.0, noiseless (`test_recovers_known_amplitudes_to_machine_precision`,
  `test_exact_at_small_arc_when_noiseless`).
- The null case — no injected cyclic error — doesn't manufacture a spurious peak. The floor is
  the estimator's genuine noise floor (roughly `0.1·σ`), not exactly zero, since demanding exactly
  zero at nonzero noise would itself be wrong (`test_null_case_does_not_manufacture_a_peak`).
- The conditioning threshold, checked in both directions so it can't silently drift
  (`test_conditioning_flags_the_small_arc_regime`).
- End-to-end on a real campaign condition: `raw_atan2` (no correction) leaves far more first-order
  cyclic error than `heydemann` (whose correction model *is* this exact distortion) on a real
  quadrature-error condition — confirming the estimator responds to genuine uncorrected
  nonlinearity, not just synthetic residuals
  (`test_detects_uncorrected_distortion_on_a_real_condition`).

Full suite: 160 passed (155 before today plus 5 new). Ruff and mypy clean on the new files.

## Left uncertain, for Week 5/6 to pick up

The conditioning limit is set by the *harder* of the two amplitudes (second-order). First-order
amplitudes are individually trustworthy well past `cond = 10` — at `cond = 33.4` (arc 0.25),
first-order median error is still only 6.1% while second-order is already 19.4%. A future
analysis could reasonably report first-order cyclic error under a looser flag than second-order.
Not done here, since the preregistration doesn't distinguish the two harmonics' reporting
standards and inventing that distinction now would be adding an unpreregistered judgment call
rather than implementing the metric as committed.
