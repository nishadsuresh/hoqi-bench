# Supplementary Experiment Protocols

Per `docs/WEEK5-6_EXECUTION_PLAN.md` §0.6: every supplementary experiment's full protocol is
written and committed here, as its own commit containing no experiment code, **before** any code
implementing it is written. RQ1/RQ2 results from the preregistered main campaign are already known,
so any post-hoc experiment designed after seeing them carries a forking-paths risk this document
exists to neutralize — a protocol committed before the run carries the same evidentiary weight, for
the same reason, that `docs/PREREGISTRATION.md` itself does.

Amendments to a protocol already committed here are appended, dated, never edited in place —
matching `docs/PREREGISTRATION.md`'s own D1-D7 discipline.

---

## Protocol 1 — RQ3 supplementary: does hysteresis direction-dependence actually change the result?

**Committed:** 2026-07-29 (Day 32), before `src/hoqi_bench/waveforms.py` exists.

### Why this experiment exists

`docs/PREREGISTRATION.md` deviation D5 (Day 29): the main campaign's `hysteresis_magnitude` axis
measures direction-**independent** radial inflation, because every campaign waveform
(`arc.build_arc_ramp`) is strictly monotonic — `transforms.hysteresis`'s direction-reversal branch
is never exercised. RQ3's hysteresis half was declared unanswered by the preregistered campaign.
This experiment is the only thing permitted to speak to actual path-dependence.

### The waveform: `build_bidirectional_ramp(arc_fraction, n_points)`

A triangle wave, fully specified here before implementation:

- **Ascending half** (`n_asc = n_points // 2` samples): `phase[k] = k * peak / n_asc` for
  `k = 0 .. n_asc - 1`, where `peak = arc_fraction * 2 * pi`. This is `linspace(0, peak, n_asc,
  endpoint=False)` — the same "never sample the far edge" convention `arc.build_arc_ramp` uses
  (D1), applied to the ascending leg specifically.
- **Descending half** (`n_desc = n_points - n_asc` samples): `phase[k] = peak - k * peak / n_desc`
  for `k = 0 .. n_desc - 1`. The descending half's FIRST sample is exactly `peak` — deliberately
  different from `build_arc_ramp`'s convention, and the reason is not the same situation D1 fixed:
  D1's `endpoint=False` exists specifically to avoid double-sampling a **wraparound** duplicate
  (phase 0 and phase 2*pi are the same physical point on a full circle). The peak of a triangle wave
  is not a wraparound — it is a genuine, physically distinct turning point that must be sampled
  exactly once for the waveform to represent a real reversal. Excluding it would understate the
  waveform's own peak displacement for no principled reason.
- **Total samples**: exactly `n_points` (`n_asc + n_desc`), matching `build_arc_ramp`'s own
  `n_points` argument exactly — same N as the corresponding preregistered condition.
- **Peak phase**: the descending half's first sample equals `arc_fraction * 2 * pi` exactly, i.e.
  the SAME peak `build_arc_ramp`'s docstring defines as its own target. Verified empirically before
  this protocol was committed (not assumed): `build_arc_ramp`'s own `endpoint=False` convention
  means its actual maximum SAMPLED value falls slightly short of `arc_fraction * 2 * pi` (e.g.
  2.9845 rad vs. a true peak of 3.1416 rad at `arc_fraction=0.5`, N=20 — a ~5% shortfall that
  shrinks as N grows, ~1.7% at N=60). The bidirectional waveform's sampled peak is closer to the
  nominal value than the monotonic ramp's own sampled maximum is. This is reported as a known,
  explained asymmetry between the two waveforms' sampling conventions, not silently equalized —
  the two data-generation mechanisms are not expected to be bit-identical in their sampled maxima,
  only to cover the same nominal phase regime at the same sample count.

**Direction signal, verified empirically before this protocol was committed:**
`sign(gradient(phase))` is `+1` throughout the ascending half and `-1` throughout the descending
half, with exactly ONE sample at exactly `direction = 0` when `n_points` is even (the single
turning-point sample, where `np.gradient`'s central-difference formula is exactly symmetric) and
ZERO such samples when `n_points` is odd. Measured at `arc_fraction=0.5`: `frac(-1)` ranges 0.45–0.49
across N in {20, 60, 61} — balanced, not exactly 0.5 because the ascending/descending sample counts
differ by at most one when N is odd, or because the single zero-direction sample at even N is
counted in neither bucket.

**The zero-direction sample requires no special-case code.** `transforms.hysteresis`'s existing
formula, `scale = (radius + hysteresis_magnitude * direction) / radius`, evaluates to `scale = 1.0`
(the exact identity) when `direction = 0` — verified directly before this protocol was committed.
The single turning-point sample is therefore automatically, correctly left unperturbed by code that
already exists and is already tested; `transforms.py` requires no modification.

### Grid

Identical `hysteresis_magnitude` values to the preregistered campaign — `[0.0, 0.01, 0.02, 0.05,
0.08, 0.1, 0.15, 0.2]`, same baseline for every other parameter, same 7 methods, same 50 seeds
(via `seeds.derive_seed`, unchanged — no new seeding path). **The only change from the preregistered
condition is the waveform generator**: `build_bidirectional_ramp` in place of `build_arc_ramp`.
2,800 fits total (8 magnitudes x 7 methods x 50 seeds), ≈0.3 s measured runtime for the equivalent
preregistered grid size.

### Metrics reported

Displacement RMSE mean/std across seeds, failure rate, gross-error rate, unusable rate — identical
metric set to the preregistered campaign, so the two are directly comparable at matched
`hysteresis_magnitude`. Every reported number is labeled with its provenance
(`preregistered_monotonic` vs. `supplementary_bidirectional`) in the output table; the two are never
merged into one column without that label.

### Pre-specified criterion

**Direction-dependence is demonstrated at a given `hysteresis_magnitude` if the supplementary
(bidirectional) displacement RMSE differs from the preregistered (monotonic) displacement RMSE, at
the same magnitude and method, by more than the preregistered run's own seed-to-seed standard
deviation** (i.e., the difference exceeds 1 SD of the monotonic run's own noise floor at that
condition — a difference smaller than the run's own measurement noise is not evidence of anything).

This is **not** expected to hold uniformly across all 7 methods: per
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`, no method models path-dependence at all, so any
direction-sensitivity found would be an emergent numerical-conditioning effect (e.g., an
ellipse/circle fit responding differently to a trajectory that revisits the same phase values twice,
once at each radius, vs. one that visits each phase once), not a designed correction. A **null
result** (no method's error changes materially) is itself a real, reportable finding — it would mean
this project's methods are insensitive to the ellipse-fitting question specifically, even though
D5 already showed they are NOT insensitive to the underlying radial-inflation magnitude itself.

### What would falsify the hypothesis that direction matters

If every method's displacement RMSE under the bidirectional waveform falls within 1 SD of its
monotonic-waveform value, at every swept `hysteresis_magnitude`, the honest conclusion is that
path-dependence — as implemented by this project's `transforms.hysteresis` model — does not
meaningfully affect displacement recovery for any of the 7 methods under test, distinct from (and
not contradicting) D5's finding that the magnitude-only radial inflation itself clearly does.

### What this experiment does NOT do

It does not re-run or modify any preregistered condition. It does not claim to answer RQ3's
hysteresis question with the same evidentiary weight as a preregistered result — it is reported
throughout as supplementary, in `results/supplementary/hysteresis_bidirectional/`, never blended
into `results/main_campaign_summary.csv` or any table built from it without an explicit
`provenance` column.

---

## Protocol 2 — RQ6 supplementary: samples_per_fit x noise_std design chart

Not yet committed. Scheduled for Week 5 Task 6 (Day 34).
