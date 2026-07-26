# Experimental Design

This proposes the forward-model equations, parameter ranges, metrics, and statistical protocol for
`hoqi-bench`'s main campaign. Per Day 5's instruction, every range is justified — grounded in
Lehmann et al. 2025's actual measured values where the paper gives them, explicitly flagged as a
reasoned design choice (not a paper-derived number) where it doesn't. **This is a proposal. Nothing
below is locked in until Nishad approves it — see the approval request at the bottom.**

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
  variation "within at most 20%" over an hour of real measurement (their Fig. 12). Proposed sweep:
  `[1.0, 1.05, 1.1, 1.2, 1.3]` — `1.0` is the no-distortion control, `1.1` is their reported typical
  hardware value, `1.2-1.3` extends beyond their observed range specifically to find where methods
  break (RQ2), not just where real hardware currently sits.

### NOT directly numerically grounded in the paper — flagged honestly, not disguised as paper-derived

- **Quadrature phase error `eps`**: the paper states the rotation angle is "poorly constrained" at
  typical radius ratios and varies "significantly... without a clear trend," but does not give an
  explicit numeric range for `eps` itself. Proposed sweep: `[0, 0.05, 0.1, 0.2, 0.3]` rad
  (approximately 0 to 17 degrees) — a physically reasonable range for a "few-degree" quadrature
  imperfection, chosen by engineering judgment, not read from the source. **This is exactly the kind
  of arbitrary-range risk this project's own task description warns about, named here rather than
  quietly assumed to be as well-grounded as the amplitude-ratio range above.**
- **DC offsets `I0, Q0`**: no explicit number found in Lehmann et al. 2025. Proposed sweep:
  `[0, 0.02, 0.05, 0.1] * A` (as a fraction of signal amplitude) — same caveat as `eps` above.
- **Hysteresis magnitude**: no explicit number given (see Section 1) — swept as a free parameter
  specifically to characterize the shape of the relationship (RQ3), not to reproduce one specific
  reported value.

### Design choices independent of any single paper (methodology, not physics)

- **Arc coverage fraction**: `[1.0, 0.5, 0.25, 0.1, 0.05]` — chosen to span "full-circle ramp
  measurement" down to "small steady-state dwell," directly motivated by Day 3's finding that this
  axis dominates numerical stability, and by the real bug from the prior `quadrature-interferometer-sim`
  project (RQ5's whole motivation) where a whole-record-mean DC estimator worked only because every
  test happened to include a ramp.
- **Noise level**: `[0, 0.01, 0.02, 0.04, 0.06] * A` (0-6%) — matching the range already validated in
  the prior `quadrature-interferometer-sim` project (chosen there, and reused here, for continuity
  and because it was itself empirically checked to be a reasonable operating range in that project's
  own validation report).
- **Monte Carlo seeds per condition**: 30 (matching Day 3's already-run study, which is itself a
  small pilot validating that 30 seeds is enough to distinguish real effects from single-seed noise
  — see Day 3's finding that a single seed near the degenerate boundary was actively misleading).

## 3. Sweep structure (not a full factorial — total_runs would be combinatorially explosive)

A full cross of every axis above would be `5(g) x 5(eps) x 4(dc) x 5(arc) x 5(noise) = 2500`
conditions before even multiplying by 7 methods and 30 seeds (525,000 runs) — combinatorially
excessive for what the research questions actually need. Instead:

- **One-factor-at-a-time (OFAT) sweeps**: each classic non-ideality (`g`, `eps`, `dc`) and each of
  arc-fraction and noise-level swept independently, holding all other parameters at a "typical
  hardware" baseline (`g=1.1, eps=0.1, dc=0.02*A, arc_fraction=1.0, noise=0`). This directly answers
  RQ1/RQ2 (how does each factor affect each method, where does each cross a tolerance) without a full
  cross.
- **One 2D grid, arc-fraction x noise-level** (5x5=25 conditions): the one interaction Day 3's
  findings showed actually matters (arc coverage and noise combine to break ellipse fitting in ways
  neither does alone) — this is the one place a fuller cross is scientifically justified, not just
  convenient.

Total conditions: `5(g) + 5(eps) + 4(dc) + 5(arc) + 5(noise) + 25(arc x noise grid) = 49`.
`total_runs = 49 conditions x 7 methods x 30 seeds = 10,290` — the config schema's
`total_runs` calculator (built today, see below) computes this automatically from the TOML config,
so this number is checked programmatically, not by hand.

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

## Approval requested

The two ranges flagged above as **not directly paper-grounded** (`eps` and DC offset ranges,
plus the hysteresis-magnitude sweep) are the ones most worth a second look before they're locked
into `docs/PREREGISTRATION.md` tomorrow — everything else either comes from a number Lehmann et al.
2025 actually reports, or from a range already validated in the prior `quadrature-interferometer-sim`
project. `total_runs = 10,290` is the other thing worth a sanity check before this becomes the
committed plan.
