# Lehmann et al. 2025 — "Mitigating effects of nonlinearities in homodyne quadrature interferometers"

**Access:** PRIMARY. Full text fetched directly from arXiv (arXiv:2511.04386) and read in full.

## Citation
Lehmann, J. et al. (2025). *Mitigating effects of nonlinearities in homodyne quadrature
interferometers.* arXiv:2511.04386. Max Planck Institute for Gravitational Physics
(Albert Einstein Institute), Hannover. See `refs/references.bib` (`Lehmann2025`).

## Core claim
Real homodyne quadrature interferometers (HoQIs) measured on a fused-silica mechanical
resonator do not trace a perfect circle in the (Q1, Q2) plane, as the ideal model
`Q1 = c·cos(phi), Q2 = c·sin(phi)` (their eq. 2) predicts. Three distortion sources are
identified and corrected via ellipse fitting: gain mismatch between photodiodes, non-90-degree
quadrature phase error, and DC offset — collapsing to a general ellipse rather than a circle in
the (Q1, Q2) plane. Real-time ellipse-parameter correction (from a ringdown/calibration
measurement) substantially suppresses this; further post-processing correction (per-hour or
per-segment refitting) suppresses it more, at the cost of needing the full data record in hand
rather than running live.

## Equations I need (this project's forward model)
- Eq. 2-3: ideal quadrature model and phase recovery via `atan2(Q1, Q2)`, unwrapped over one FSR.
- The general ellipse form the distorted (Q1, Q2) trace follows — gain ratio `R1/R2`, rotation
  angle `theta`, and center offset are the parameters recovered by the ellipse fit and used to
  normalize the distorted trace back to a unit circle before phase recovery. (Exact numbered
  equation for the full distorted forward model, as opposed to the ideal eq. 2-3, needs a more
  careful re-read on Day 9/13 — the paper states the *effect* precisely but I did not find one
  single canonical equation combining all three distortion sources the way `hoqi-bench`'s Day 9-10
  transforms will need; it may need to be assembled from the ellipse-parameter description in
  Section III rather than copied from one equation, and that should be double-checked, not assumed.)
- Section III.C, "Comparison of techniques": residual nonlinearity vs. motion range follows a
  power-law trend "close to power of 3."

## What it does NOT address
- The paper does not derive Heydemann's (1981) correction from first principles — it cites and
  applies ellipse fitting as an established technique, not as new theory. Day 2's derivation work
  draws on Heydemann 1981 directly, not this paper.
- No comparison across multiple ellipse-fitting algorithms (Kasa, Halir & Flusser, Fitzgibbon,
  Taubin) — this paper applies "an ellipse fit" without benchmarking fitting-method choice, which
  is exactly the gap `hoqi-bench` fills (see `notes/related_work_table.md`, Day 4).
- No simulation study — everything is measured on real hardware (a specific fused-silica
  mechanical resonator, HoQI readout electronics). `hoqi-bench` is explicitly a simulation-only
  benchmark; this paper is the real-hardware anchor being extended from, not duplicated.
- Full statistical uncertainty quantification on the ellipse-fit parameters themselves is not the
  paper's focus (contrast with Kok/Köning et al. 2014, whose stated purpose is exactly the
  statistical-uncertainty side of ellipse fitting).

## Open questions (flag for Day 13, do not silently resolve)

**This is the important one.** The Day 13 task in the build plan calls for implementing "the
power-law nonlinearity class from Lehmann et al. 2025" as if it is a third forward-model
distortion mechanism analogous to amplitude imbalance / quadrature phase error / DC offset
(the classic Heydemann triad). Having now read the paper directly: **the "power-law" content in
this paper is not a distinct injectable distortion mechanism with its own governing equation.**
It's an *empirically observed scaling relationship* in Section III.C — after ellipse correction,
the leftover residual nonlinearity (measured via a specific noise-floor harmonic's amplitude)
scales roughly as motion-range cubed, across the range of motion amplitudes they tested. This is a
description of a measured *outcome*, not a specified *cause* with a clean forward-model formula to
inject into simulated (I, Q) data the way amplitude ratio or quadrature phase error have one.

Two different things Day 13 could reasonably mean, and I do not think the paper disambiguates
which one is intended:
1. Model an *additional, distinct* nonlinear distortion mechanism (e.g., a photodiode response
   with a power-law rather than linear intensity dependence) that, when run through the same
   ellipse-fit correction pipeline, *produces* residual error that happens to scale roughly like
   motion-range^3 as an emergent result — matching the paper's finding as a downstream consequence,
   not as a directly-copied equation.
2. Retroactively fit a `residual_error ~ magnitude^n` power-law curve to sweep results from the
   *existing* classic distortion mechanisms (amplitude/quadrature/DC) and report the exponent as a
   descriptive statistic, without adding any new forward-model mechanism at all.

These lead to meaningfully different Day 13 implementations. Per that day's own instruction ("if
the specification there is ambiguous, ASK ME rather than guessing"), this should be raised
explicitly with Nishad on Day 13 rather than picked silently now — flagging it here in the notes
file on Day 1 so it's visible early rather than only surfacing seven days from now.

## Hysteresis (RQ3's other nonlinearity class — this one IS a clear mechanism)
Unlike the power-law item above, hysteresis is unambiguous in the paper: Section IV.A documents
that after ellipse correction, a residual radius deviation `Rd(phi) = R(phi) - mean(R)` traces
*different paths depending on direction of motion* — confirmed across every oscillation tested.
The paper's own attempted fix (fitting a separate ellipse per direction and stitching the
corrected phase time series back together) is described as only a partial correction ("showed a
small hysteresis, which could not be corrected," line ~995) — directly supporting this project's
framing that hysteresis is the genuinely open edge, not a solved problem being reproduced.
