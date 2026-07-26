# Day 11 — Gaussian detector noise

## What detector noise is, physically, and why the simple model is the conventional starting point

Even a perfectly clean, undistorted interferometer signal doesn't come out of a real detector
exactly right — there's always some random jitter added on top, from a mix of causes: photon
arrival is fundamentally a random (quantum) process (shot noise), the electronics reading the
detector have their own thermal jitter, and there are other small stray sources besides. The
physically correct description of the dominant source, shot noise, has its randomness *scale with*
how much light is actually hitting the detector — a bright fringe peak is noisier in absolute terms
than a dim one, even though both are noisy by the same relative fraction.

The model built today is deliberately simpler than that: constant-strength, intensity-independent
Gaussian noise, the same amount of jitter regardless of how bright the signal is at that instant.
This isn't because the simpler model is thought to be more accurate — it's explicitly not, and the
module docstring says so in the first paragraph, not buried in a caveats section — it's used because
it's the conventional starting point in this literature (matching how the prior
`quadrature-interferometer-sim` project modeled it, and how most of the classic ellipse-fitting
papers in this project's reading list treat noise), simple enough to reason about analytically
alongside the classic Heydemann distortions, and it sets up the real comparison this project cares
about: Day 12 builds the physically correct, signal-dependent Poisson alternative, and RQ4
(`docs/PREREGISTRATION.md`) directly asks whether the comparative method rankings change once the
noise model gets more realistic — a real, answerable question, not one to quietly avoid by only ever
using the convenient model.

## What got built

- **`src/hoqi_bench/noise.py`**, `gaussian_noise` — intensity-independent additive Gaussian noise,
  drawn independently for I and Q (two separate RNG calls, not one draw reused for both — a
  specific, real bug this design choice rules out structurally rather than by convention), exact
  identity at `noise_std=0`.
- **`tests/test_noise.py`** — five tests, each checking a real statistical property with a
  calculated (not arbitrary) tolerance: empirical noise standard deviation matches the specified
  value within the standard error expected for the sample size used (`sigma/sqrt(2N)`, a real
  statistical bound derived in the test itself); determinism under a fixed seed; that two *different*
  seeds actually produce different output (catching the specific bug where a seed is silently
  ignored, which a determinism-only test would miss); and that I and Q's added noise are
  uncorrelated, with the correlation-coefficient tolerance also derived from sample-size statistics
  rather than picked by feel.

## Why "independence between I and Q" gets its own dedicated test

It would be easy to add noise to both channels using one array of random numbers reshaped or split
in half, and it would even look correct in a superficial read — both channels end up noisy. But that
would silently correlate the two channels' noise, which is physically wrong (I and Q come from
separate photodiodes with independent electronic noise) and could bias a downstream ellipse-fitting
method's error statistics in a way that's hard to notice without specifically checking for it. Using
two separate RNG calls makes the independence structurally guaranteed rather than something to
verify after the fact and hope stays true as the code evolves — but the test still checks it
directly, rather than trusting the implementation's structure alone.
