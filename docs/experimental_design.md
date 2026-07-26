# Experimental Design

This proposes the forward-model equations, parameter ranges, metrics, and statistical protocol for
`hoqi-bench`'s main campaign. Per Day 5's instruction, every range is justified — grounded in
Lehmann et al. 2025's actual measured values where the paper gives them, explicitly flagged as a
reasoned design choice (not a paper-derived number) where it doesn't.

**Status: APPROVED (2026-07-26), as expanded.** Nishad approved the two engineering-judgment
ranges as originally proposed, and asked for the sweep itself to be expanded on four fronts: finer
per-axis resolution, more seeds, more interaction grids, and folding the two Day 20 "stretch"
methods (Taubin, Köning/Wimmer/Witkovský) into the required main-campaign method set rather than
treating them as optional. Section 2-3 below reflect the expanded, approved design; the original,
smaller proposal is preserved in git history (see the Day 5 commit) rather than deleted.

## 1. Forward model equations

Building on `docs/derivations/heydemann.md`'s notation, all lengths in meters, angles in radians,
amplitude ratio dimensionless.

**Ideal signal:**
```
I(phi) = A * cos(phi)
Q(phi) = A * sin(phi)
```

**Classic (Heydemann) non-idealities**, each independently switchable, matching Day 2's derivation:
```
I(phi) = I0 + A * cos(phi)
Q(phi) = Q0 + A * g * sin(phi + eps)
```
- `g` (amplitude ratio, dimensionless): ideal = 1.
- `eps` (quadrature phase error, rad): ideal = 0.
- `I0, Q0` (DC offsets, same units as A): ideal = 0.

**Arc coverage** (not a distortion — a measurement-regime parameter, per Day 3's finding that this
is the single most consequential axis for numerical stability): the fraction of a full `2*pi` phase
sweep the (I, Q) trajectory actually traverses during a fit window. `arc_fraction = 1.0` is a full
circle; `arc_fraction = 0.05` is a 18-degree arc.

**Noise models** (RQ4): Gaussian, intensity-independent additive noise (matching
`quadrature-interferometer-sim`'s existing model, for continuity with validated prior work), and
Poisson shot noise (signal-dependent variance, to be implemented Day 12), swept at matched-equivalent
levels (exact matching procedure to be documented in Day 12's implementation, since it's a real,
challengeable methodological choice per that day's own task).

**Power-law and hysteresis nonlinearities (RQ3)**: per the Day 13 ambiguity flagged in
`notes/lehmann_2025.md`, the power-law forward-model mechanism is not yet finalized (pending that
day's check-in). Hysteresis is a path-dependent perturbation to be implemented Day 14, magnitude
swept as a free experimental parameter (justification: Lehmann et al. 2025 doesn't report a single
hysteresis magnitude number, only that it exists and is only partially correctable — see
`notes/lehmann_2025.md`).

## 2. Parameter ranges, with justification for each

### Grounded directly in Lehmann et al. 2025's reported numbers

- **Amplitude ratio `g`**: Section III.C reports "typical radius ratio values of around 1.1" with
  variation "within at most 20%" over an hour of real measurement (their Fig. 12). Approved sweep
  (expanded from the original 5-point proposal to 10 points, per Nishad's request for finer
  resolution): `[1.0, 1.02, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4, 1.5]` — `1.0` is the no-distortion
  control, `1.1` is their reported typical hardware value, values above `1.3` extend well beyond
  their observed range specifically to find where methods break (RQ2), not just where real hardware
  currently sits.

### NOT directly numerically grounded in the paper — flagged honestly, not disguised as paper-derived

- **Quadrature phase error `eps`**: the paper states the rotation angle is "poorly constrained" at
  typical radius ratios and varies "significantly... without a clear trend," but does not give an
  explicit numeric range for `eps` itself. Approved as originally proposed (kept, per Nishad's
  answer), expanded to 10 points for resolution: `[0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4,
  0.5]` rad (roughly 0 to 29 degrees) — a physically reasonable range for a quadrature imperfection,
  chosen by engineering judgment, not read from the source. **This is exactly the kind of
  arbitrary-range risk this project's own task description warns about, named here rather than
  quietly assumed to be as well-grounded as the amplitude-ratio range above.**
- **DC offsets `I0, Q0`**: no explicit number found in Lehmann et al. 2025. Approved as proposed,
  expanded to 8 points: `[0.0, 0.01, 0.02, 0.05, 0.08, 0.1, 0.15, 0.2] * A` (as a fraction of signal
  amplitude) — same caveat as `eps` above.
- **Hysteresis magnitude**: no explicit number given (see Section 1) — swept as a free parameter
  specifically to characterize the shape of the relationship (RQ3), not to reproduce one specific
  reported value.

### Design choices independent of any single paper (methodology, not physics)

- **Arc coverage fraction**: expanded to 9 points, `[1.0, 0.75, 0.5, 0.35, 0.25, 0.15, 0.1, 0.05,
  0.02]` — chosen to span "full-circle ramp measurement" down to "small steady-state dwell,"
  directly motivated by Day 3's finding that this axis dominates numerical stability, and by the
  real bug from the prior `quadrature-interferometer-sim` project (RQ5's whole motivation) where a
  whole-record-mean DC estimator worked only because every test happened to include a ramp.
- **Noise level**: expanded to 10 points, `[0.0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08,
  0.1] * A` — the 0-6% core of this range matches what's already validated in the prior
  `quadrature-interferometer-sim` project; extended slightly to 10% for more breakdown headroom, per
  the general "expand for finer resolution and more room to find where things break" request.
- **Monte Carlo seeds per condition**: raised from 30 to **50**, per Nishad's request for tighter
  confidence intervals. Day 3's own 30-seed pilot already showed 30 was enough to distinguish real
  effects from single-seed noise (that pilot is what caught the near-degenerate-regime finding a
  single seed would have missed) — 50 tightens the resulting bootstrap CIs further without
  meaningfully changing runtime at this problem size (each run is a cheap ellipse fit on ~60 points).

## 3. Sweep structure (not a full factorial — total_runs would be combinatorially explosive)

A full cross of every axis above would be `10(g) x 10(eps) x 8(dc) x 9(arc) x 10(noise) = 72,000`
conditions before even multiplying by methods and seeds — still combinatorially excessive. Instead:

- **One-factor-at-a-time (OFAT) sweeps**: each classic non-ideality (`g`, `eps`, `dc`) and each of
  arc-fraction and noise-level swept independently, holding all other parameters at a "typical
  hardware" baseline (`g=1.1, eps=0.1, dc=0.02*A, arc_fraction=1.0, noise=0`). This directly answers
  RQ1/RQ2 (how does each factor affect each method, where does each cross a tolerance) without a full
  cross.
- **Three 2D interaction grids** (expanded from the original single grid, per Nishad's request):
  - `arc_fraction x noise_std` (9x10=90) — the interaction Day 3's findings showed actually matters
    (arc coverage and noise combine to break ellipse fitting in ways neither does alone).
  - `amplitude_ratio x quadrature_error_rad` (10x10=100) — the two classic Heydemann distortion
    parameters, to check whether they interact (e.g. does a large phase error make the method more
    or less sensitive to amplitude imbalance) rather than assuming they're independent.
  - `amplitude_ratio x noise_std` (10x10=100) — checks whether noise sensitivity itself depends on
    how distorted the ellipse already is, a natural follow-on question once both axes are being
    swept independently anyway.

Total conditions: `10(g) + 10(eps) + 8(dc) + 9(arc) + 10(noise) + 90 + 100 + 100 = 337`.

**Methods**: all 7 implemented methods are now REQUIRED in the main campaign (raw atan2 baseline,
Kasa, Heydemann, Halir & Flusser, Fitzgibbon, Taubin, and Köning/Wimmer/Witkovský's
nonlinear-constraint fit) — promoted from the original plan's Day 20 "stretch, if time allows"
framing, per Nishad's explicit request. **One honest caveat**: per `notes/koning_2014.md`, that
paper's actual method ("nonlinear constraints," as opposed to the linear reformulations the other
methods use) is currently understood only at the title/abstract level, not in enough depth to
implement faithfully. Promoting it to required now means Day 19/20 needs either (a) real access to
the 2014 paper before implementing it, or (b) a best-effort implementation explicitly labeled as an
approximation of the described method rather than a faithful reproduction — a decision to make at
that day, not silently resolved here.

`total_runs = 337 conditions x 7 methods x 50 seeds = 117,950` — the config schema's `total_runs`
calculator (built today) computes this automatically from the TOML config, so this number is
checked programmatically, not by hand. At this problem size (each run is a cheap ellipse fit on
~60 points), 117,950 runs is still fast — expected well under an hour, likely single-digit minutes,
so no grid-resolution reduction (Day 26's fallback, if runtime exceeds ~12 hours) is needed.

## 4. Metrics (built Day 22-23, referenced here for completeness)

- Displacement RMSE and peak absolute error (Day 22).
- Per-fit runtime (Day 22) — cost matters for RQ1's "cost" axis.
- Cyclic-error harmonic amplitude (Day 23) — the field's standard figure of merit, per that day's
  task description.
- Failure rate (Day 3's own finding that failure rate, not just error-when-successful, is often the
  more important number — carried forward as a first-class metric here, not an afterthought).

## 5. Statistical protocol

- **Seeds per condition**: 30 (justified above).
- **Confidence intervals**: bootstrap CI on the mean (percentile method) across the 30 seeds per
  condition — chosen over a normal-approximation CI since failure-inflated distributions (some seeds
  fail outright, per Day 3) are not obviously normal, and bootstrap doesn't assume a distributional
  shape.
- **Breakdown-threshold definition**: the smallest swept parameter value at which a method's mean
  error (excluding outright failures, which are tracked separately as a failure rate) first exceeds
  a stated tolerance (1% relative RMS error, matching the tolerance already used and validated in the
  prior `quadrature-interferometer-sim` project), found by linear interpolation between the two
  bracketing grid points rather than reported only at grid resolution.
- **Multiple-comparison handling**: since every method is compared against every other method across
  many conditions, pairwise comparisons use a Bonferroni-corrected significance threshold (simple,
  conservative, easy to justify to a skeptical reader) rather than an uncorrected pairwise t-test —
  full detail deferred to Day 25's implementation, named here as a preregistration commitment.

## Approval record

Approved 2026-07-26: both engineering-judgment ranges (`eps`, DC offset) kept as originally
proposed; sweep expanded on all four requested fronts (finer per-axis resolution, seeds 30→50,
two additional interaction grids, and Taubin/Köning promoted from stretch goals to required
methods). This is now the locked design feeding into Day 6's `docs/PREREGISTRATION.md`.
