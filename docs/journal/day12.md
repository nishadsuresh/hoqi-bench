# Day 12 — Poisson shot noise

## Why photon arrival is Poisson, in plain language

Light isn't a smooth, continuous flow — it arrives at a detector as individual photons, and exactly
when each one shows up is fundamentally random, the same way radioactive decay events are random.
Over a fixed measurement window, if you'd expect (on average) some number of photons to arrive, the
*actual* count that shows up in any one measurement fluctuates around that average — and the precise
shape of that fluctuation is described by the Poisson distribution. Its single defining
mathematical property is that its variance equals its mean: a dim signal (few expected photons) and
a bright signal (many expected photons) don't fluctuate by the same *absolute* amount — the bright
one fluctuates more in absolute terms, even though, relatively, brighter signals are actually
*cleaner* (their fractional noise, `sqrt(mean)/mean = 1/sqrt(mean)`, shrinks as the signal brightens).
Day 11's Gaussian model has neither of these properties — its noise is the same absolute size
regardless of how bright the signal is at that instant, which is why it's explicitly a
simplification, not a claim of physical accuracy.

## Why signal-dependent noise is genuinely harder for phase-recovery methods

Every method in this benchmark's job is to fit a circle or ellipse to the (I,Q) trajectory. Under
Gaussian noise, every point on that trajectory is corrupted by the same amount of scatter, so the
fitting problem is uniform around the shape. Under Poisson (signal-dependent) noise, points near the
brightest part of the fringe cycle are noisier in absolute terms than points near the dimmest part —
the "cloud" of scattered points isn't uniformly thick around the ellipse, it's thicker in some
places than others depending on where in the cycle each point was measured. A fitting method that
implicitly (or explicitly) assumes uniform noise around the shape is making an assumption that's
simply false under this more realistic model — which is exactly why RQ4 asks whether the comparative
rankings between methods actually change once this assumption is violated, rather than assuming the
Gaussian-model rankings automatically carry over.

## Why most of this literature uses the simpler model anyway

Mathematical convenience, mostly, and it's rarely stated as a limitation rather than a default. A
fixed-variance noise model is far easier to reason about analytically alongside the classic
Heydemann ellipse distortions (which is exactly why Day 9-11 could derive clean, closed-form
geometric predictions to test against), and at high enough signal levels the difference between the
two models genuinely does shrink — which is part of why it's such an easy default to reach for
without checking whether it matters for the specific regime being studied.

## What got built

- **`poisson_noise`** in `src/hoqi_bench/noise.py` — converts continuous intensity into a photon-count
  scale via a tunable `photon_scale` parameter, draws real Poisson noise on that count, converts back.
  Working through the variance algebra explicitly in the docstring: `Var(noise) = intensity /
  photon_scale` — variance genuinely proportional to intensity, the actual defining property, not
  just "noise that happens to look plausible."
- **Four tests**, two of which are real physics checks rather than code-ran checks:
  - **Variance-proportional-to-intensity**, checked across five different intensity levels (not one
    cherry-picked value) — `variance/intensity` must stay approximately constant, which is the actual
    mathematical content of "signal-dependent noise," not just "noise that scales with something."
  - **Convergence to a Gaussian shape at high photon count**, using the Central Limit Theorem's
    concrete prediction that Poisson's skewness (`1/sqrt(lambda)`) shrinks toward zero as the expected
    photon count grows — checked as an actual decreasing trend across four increasing photon scales,
    landing near zero skewness at the highest scale, rather than merely checking the implementation
    "looks noisy."

## A small process note

Ruff's suggested `zip(..., strict=True)` auto-fix was applied to two loops without checking each one
individually, and one of them broke a test — the consecutive-pairs loop (`zip(list, list[1:])`) is
*intentionally* comparing sequences of different lengths, so `strict=True` is wrong there even
though it's the generally-safer default. Caught immediately by rerunning the full suite after
applying the lint fix, rather than assuming a lint auto-fix is always safe to accept blindly.
