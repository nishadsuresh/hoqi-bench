# Day 30 — RQ3 power-law characterization on real campaign data

The anchor named all the way back on Day 13: "the real data comes in on Day 30." Day 13 built and
validated `power_law.fit_power_law_exponent` against synthetic data with a known exponent,
deliberately not answering whether this project's own sweep data shows a clean power-law
relationship until real phase-recovery methods existed and a real campaign had run. Both have
existed since Week 3/4; today is the day that question gets a real answer.

## What got built

`scripts/rq3_power_law_analysis.py` fits `error = c * magnitude^n` (via the existing, unmodified
`power_law.fit_power_law_exponent`) across the four preregistered OFAT axes with a monotonic,
zero-anchored distortion magnitude — `amplitude_ratio` (as `ratio - 1.0`, since 1.0 is that axis's
own zero-distortion point, not 0.0), `quadrature_error_rad`, `dc_offset`, and
`hysteresis_magnitude` — against every method, using the already-aggregated, contract-aware
`results/main_campaign_summary.csv` rather than re-deriving a mean from the raw table.

**Naming, per Day 29's deviation D5.** `hysteresis_magnitude` measures direction-independent
radial inflation, not path-dependent hysteresis (every campaign waveform is monotonic). It is
still a legitimate, real, monotonic distortion magnitude, so it stays in this analysis — but every
output row labels it `radial_inflation (preregistered as hysteresis_magnitude; see D5)`, never
bare "hysteresis," so this script cannot misrepresent what the axis actually measured.

**Two exclusions applied before any fit, both required by `fit_power_law_exponent`'s own
contract:** each axis's zero-distortion grid point (log of zero is undefined), and any
(method, magnitude) point where that method's own `unusable_rate` there exceeds
`aggregate.MAX_UNUSABLE_RATE_FOR_RANKING` (0.20) — the same rankability threshold the rest of the
project already uses, applied per-point so one method's bad regime doesn't silently exclude a
point from every other method's fit.

## The honesty gate: calibrated before looking at any real number

`docs/WEEK5-6_EXECUTION_PLAN.md` Task 2.2 requires an r² floor pre-committed *before* seeing the
fitted values, so a genuinely flat relationship can't get quietly reported as "yes, power of 3."
Rather than pick a round number, ran two synthetic calibrations first:

- A genuinely **flat** relationship (no power law at all), fit against the same 7-10-point grids
  this project's own axes use, at 5%/15%/30% relative noise, 3,000 trials each: r² never exceeded
  **0.890** at any noise level (mean ~0.13, p99 ~0.64).
- A genuine **n=3** power law, same grids, same noise levels: r² was **at least 0.990** in every
  single trial, even at 30% noise.

`R_SQUARED_FLOOR = 0.90` sits in the gap between those two distributions — above the null's
observed worst case across 9,000 total trials, comfortably below a real relationship's worst case
— rather than being chosen by taste. Both calibration experiments are reproduced as independent
oracle tests in `tests/test_rq3_power_law_analysis.py` (a flat-relationship test that must stay
below the floor, and a genuine-power-law test that must clear it), so the floor's own correctness
is CI-enforced, not just asserted once in a journal entry.

## The result: honest, and not what Lehmann's paper reports

**Only 7 of 28 (axis, method) fits clear the r² floor — and none of the 7 that do land near
Lehmann's reported exponent of 3.**

| axis | methods above floor | exponent range |
|---|---|---|
| `quadrature_error_rad` | raw_atan2, kasa, taubin | 0.67 – 0.71 |
| `radial_inflation` (D5) | heydemann, halir_flusser, fitzgibbon, koning | 0.85 – 0.92 |
| `amplitude_ratio` | none | — (all r² 0.79–0.85, below floor) |
| `dc_offset` | none | — (all r² ≤ 0.84, most well below) |

Two things worth naming plainly rather than smoothing over:

- Where a clean fit *does* exist, the exponent clusters near **1** (roughly linear), not near
  **3**. `radial_inflation`'s near-perfect fits (r² up to 0.9999) for the four general-conic
  fitters make sense mechanistically — a uniform radial offset is a simple, close-to-linear
  perturbation to an ellipse fit's residual, not the paper's power-of-3 relationship, which is
  reported on a completely different quantity (post-correction residual **vs. motion range**, not
  vs. distortion magnitude — this project's own Day 13 scope decision already flagged that these
  are different axes being compared, not a direct reproduction attempt).
- On `amplitude_ratio` and `dc_offset` — the two axes closest to the classic Heydemann distortion
  triad the forward model is tautologically built to match — **no method produces a clean power
  law at all.** Exponents vary by 7x across methods on the same axis (0.27 to 1.89 on
  `amplitude_ratio`), which is itself informative: a genuine shared power-law mechanism would be
  expected to show a more consistent exponent across methods solving structurally similar
  problems, not this much scatter.

## Left for Nishi (not resolved today — a scope decision, not a code decision)

Per `power_law.py`'s own documented fallback and the plan's Decision Points list (item 7): **75%
of fits (21/28) fall below the honesty floor**, which is exactly the condition the fallback
question was written for. This script does not choose for itself whether that means:
(a) this project's own sweep data simply does not show a clean power-law relationship on these
axes, and that null result is reported as-is; or (b) power-law should be modeled as a genuinely
new injected forward-model transform (the alternative Day 13 explicitly declined to build,
pending exactly this evidence). Reported here, not decided here.

## Verification

`tests/test_rq3_power_law_analysis.py` — 5 tests: the `amplitude_ratio` zero-point transform, the
zero-magnitude exclusion, the high-unusable-rate exclusion, and both calibration oracles (flat
relationship stays below the floor, genuine n=3 relationship clears it). Full suite: 207 passed, 2
xfailed (unchanged from Day 29, both still pointing at D5/D6 by name). `ruff check`, `ruff format
--check` (on the two new files — the 27 pre-existing files flagged Day 29 are still out of scope
here), and `mypy --strict` all clean on the new files and the full repo.

## What's next

Task 3 (Day 31): wire up the cost metric that's been null in 100% of rows since Week 4 (P3), and
check whether the fix changes anything already claimed in the published RQ1/RQ2 draft.
