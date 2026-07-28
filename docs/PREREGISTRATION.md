# Preregistration (v2)

Committed 2026-07-26, superseding `docs/PREREGISTRATION_v1_superseded.md` -- same day, before any
main-campaign result exists and before Week 3 begins. This is a **pre-data revision**: the original
v1 document (also committed 2026-07-26) was found, by a same-day adversarial audit
(`docs/WEEK1-2_AUDIT.md`) and a second adversarial llm-council review, to commit to research
questions and a parameter space its own config file could not actually execute. See the superseded
document's postmortem header for the full reasoning on why a clean reset -- not a trail of dated
deviations -- is the right response at this point, specifically because zero campaign results exist
yet. Every change from v1 is listed in "Revision history" below, each with the finding that drove it.

## Why preregistration matters here specifically

The single biggest failure mode in solo research with no external reviewer isn't fraud — it's a
much quieter thing: unconsciously steering the analysis toward whichever result feels most
satisfying, after the fact. If the parameter ranges, the metrics, and the statistical protocol are
only decided *after* looking at some early results, it becomes very easy to retroactively justify
"well, that range made more sense anyway" in whichever direction happens to make the story cleaner
— not through dishonesty, but because a compelling narrative is a real, human pull, and nobody is
checking. Writing all of this down *before* the main campaign runs, and then holding to it (or
explicitly, visibly deviating from it and saying why), is the cheapest available substitute for
having an external reviewer who would otherwise catch that kind of drift.

**v2 addendum**: the same discipline applies to the preregistration DOCUMENT itself, not just to
the campaign it describes. A prereg that names parameters no code can actually bind is exactly the
kind of drift this document exists to prevent, just at the specification stage instead of the
analysis stage — hence this revision, made openly and dated, rather than silently.

## External timestamp

A preregistration committed to a git repository the author controls, with a rewritable history, is
not independently verifiable as having existed before the campaign ran -- it is a note to self until
an external party holds a timestamp on it.

**Resolved 2026-07-27**: registered on OSF at https://osf.io/qyw6t, Date Registered stamped
2026-07-27 10:15 AM -- before Week 3 implementation begins and well before any main-campaign
result. This is v2 of the document (see Revision history); v1 is preserved at
`docs/PREREGISTRATION_v1_superseded.md` and was never independently timestamped, since the
v1-to-v2 revision happened same-day, pre-data, specifically to avoid registering a document later
found to name unexecutable parameters. As of registration, the OSF entry showed a "Pending
approval" status pending moderator review -- the Date Registered timestamp is stamped regardless of
that review outcome, since it is set at submission, not at approval.

The GitHub push blocker (`docs/WEEK1-2_AUDIT.md`, prevalent issue B7) is also resolved as of
2026-07-27: all commits are live on `main` at `github.com/nishadsuresh/hoqi-bench`, CI passing on
both supported Python versions.

## Research questions (unchanged from v1)

- **RQ1** — Across a common controlled parameter space, how do the major phase-recovery methods
  compare on displacement accuracy, cyclic-error harmonics, robustness, and cost?
- **RQ2** — For each method, at what parameter magnitude does error exceed a stated tolerance?
- **RQ3** — Do methods built for classic static ellipse distortion retain accuracy under Lehmann et
  al.'s power-law and direction-dependent nonlinearity classes?
- **RQ4** — Under physically correct signal-dependent Poisson shot noise rather than the usual
  Gaussian assumption, do the comparative rankings change?
- **RQ5** — How does performance depend on phase-excursion regime (many-fringe ramp vs. small
  steady-state vibration)?

**v2 addition — RQ6** (a genuinely new, falsifiable deliverable the audit's council review
identified as hiding inside the existing sweep, not a new research direction): for a given noise
level, what samples-per-fit (N) is needed to reach a target accuracy? Answered directly from the new
`samples_per_fit` axis (below) -- a practitioner-facing "N-vs-noise design chart" that does not
currently exist in the HoQI literature, per the related-work search in `notes/related_work_table.md`.

## Parameter space (v2 -- see Revision history for what changed and why)

- **Methods (7, all required)**: raw atan2 (no correction), Kasa, Heydemann, Halir & Flusser,
  Fitzgibbon, Taubin, Köning/Wimmer/Witkovský.
- **OFAT axes (8, up from 5)**: amplitude ratio (10 points, `[1.0, 1.5]`), quadrature phase error
  (10 points, `[0, 0.5]` rad), DC offset (8 points, `[0, 0.2]*A`), arc coverage fraction (9 points,
  `[0.02, 1.0]`), noise level (10 points, `[0, 0.1]*A`), **samples-per-fit (7 points, `[20, 1000]`,
  new in v2)**, **hysteresis magnitude (8 points, `[0, 0.2]*A`, new in v2)**, **photon scale (7
  points, `[100, 100000]`, new in v2)**.
- **Interaction grids (3, unchanged)**: arc-fraction x noise (90 conditions), amplitude-ratio x
  quadrature-error (100 conditions), amplitude-ratio x noise (100 conditions).
- **Monte Carlo seeds**: 50 per condition, **paired across all 7 methods** (new in v2 -- see
  Statistical protocol).
- **Total**: 359 conditions x 7 methods x 50 seeds = 125,650 runs.

Note on the total: `359 x 7 x 50 = 125,650`, computed programmatically by
`config.SweepConfig.total_runs()` against `configs/main_campaign.toml` (not by hand -- this
document's own v1 predecessor had a stale hand-computed number in a different file,
`config.py`'s docstring, precisely the kind of drift a programmatic check catches and a hand
computation doesn't).

## Metrics (v2 -- circular statistics and fit-failure contract added)

- Displacement RMSE and peak absolute error (unchanged from v1).
- **Phase error uses `hoqi_bench.metrics.wrapped_phase_error`, not a naive linear difference (new in
  v2, `docs/WEEK3_METHOD_CONTRACT.md` Section 1)** — phase is periodic; a naive difference near a
  +-pi wrap boundary overstates error by orders of magnitude.
- **Cost**, defined explicitly (not left as a placeholder): wall-clock time per fit (mean and std
  across seeds, same hardware), and a secondary iteration count for iterative methods (currently
  only Köning/Wimmer/Witkovský — see below — since every other method is a single-shot linear
  solve with no iteration count to report).
- **Robustness**, defined explicitly as one number per method per condition: failure rate (fraction
  of the 50 seeds where the method returns no valid fit), reported separately from
  error-when-successful, never blended into a single combined score. **Enforced in v2 by an explicit
  fit-failure contract (`docs/WEEK3_METHOD_CONTRACT.md` Section 2): every method must return a
  result for every (condition, seed) pair -- NaN + an explicit reason code + `failed=True` on
  failure, never a silently dropped row.** Without this, failure rate as "separate from
  error-when-successful" is a commitment about the prose, not about the data: a dropped row means
  Week 5's analysis silently averages only over survivors, and every method looks equally accurate
  regardless of its real failure rate.
- Cyclic-error harmonic amplitude (first and second order).

## Statistical protocol (v2 -- paired seeds and derivation rule added)

- Bootstrap confidence intervals (percentile method) on the mean across 50 seeds per condition —
  chosen over a normal-approximation CI because failure-inflated distributions are not assumed
  normal.
- **Seeds are PAIRED across all 7 methods (new in v2)**: for a given (condition, seed_index), every
  method is evaluated against the identical noise realization, via
  `hoqi_bench.seeds.derive_seed(seed_index, condition_name, stream)` — a function that structurally
  cannot take a method identifier, so pairing is enforced by the function's signature, not left as a
  convention a harness implementation could violate. This removes the shared-noise-draw variance
  term from every method-vs-method comparison, meaningfully tightening the resulting confidence
  intervals at zero additional runtime cost. This decision could not have been made after the fact
  once the campaign had run (`docs/WEEK1-2_AUDIT.md` finding F3) — fixing it now, pre-data, is
  exactly the situation where that fact matters least.
- Breakdown-threshold: smallest swept value where mean error (excluding outright failures, tracked
  separately) first exceeds 1% relative RMS error, via linear interpolation between grid points.
  **Applies only to the amplitude-ratio and arc-coverage axes**, both grounded in real numbers
  (Lehmann et al. 2025's reported typical/drift values, and Day 3's own findings, respectively) —
  see item 1 in v1's revision history for why quadrature-error and DC-offset breakdown thresholds
  are NOT reported as calibrated quantitative values (unchanged in v2).
- Multiple-comparison correction: **Bonferroni, family = all pairwise method comparisons WITHIN a
  single research question and a single swept condition** (i.e., 21 pairwise comparisons per
  condition for 7 methods, corrected alpha = 0.05/21 ≈ 0.0024 per condition) — not a single global
  correction across all conditions x 5 RQs (unchanged from v1).
- **Fraction-to-absolute unit conversion (new in v2)**: `dc_offset`, `noise_std`, and
  `hysteresis_magnitude` are specified in the config as fractions of oscillation amplitude
  `A = mean_intensity * contrast` (per `docs/experimental_design.md`'s "* A" notation); `resolve.py`
  performs this conversion exactly once, at condition-resolution time, before any value reaches a
  transform (`docs/WEEK1-2_AUDIT.md` finding F2: the transforms themselves take absolute values,
  and nothing previously converted between the two — a 1.11x systematic error at the campaign's own
  baseline A=0.9).

## Revision history

**2026-07-26 (v1): revised following an adversarial llm-council review**, run per Day 6's own
instructions to attack the plan rather than rubber-stamp it. Preserved verbatim in
`docs/PREREGISTRATION_v1_superseded.md`; summary: (1) RQ2's breakdown thresholds demoted to
ordinal-only on the two ungrounded axes; (2) Köning/Wimmer/Witkovský's implementation risk
de-risked via the `OEFPIL` algorithm family; (3) RQ3's power-law fork given a default (characterize,
don't inject) and a stated fallback; (4) cost and robustness given explicit formulas; (5) Bonferroni
correction fully specified. One recommendation (a small real pilot before finalizing the two guessed
axes) deliberately not actioned that day, since no method existed yet to pilot against — scheduled
for Day 15 instead.

**2026-07-26 (v2): full document superseded and re-registered, same day, before Week 3 began and
before any campaign data existed** — following a Weeks 1-2 adversarial audit
(`docs/WEEK1-2_AUDIT.md`) and a second llm-council review. Every change, with the finding that
drove it:

1. **`samples_per_fit` (N) promoted from an unspecified assumption to a config field and OFAT axis**
   (finding F4). N was previously named in no config, constant, or schema field, despite driving a
   measured 7x swing in mean center error (0.0201 at N=20 vs. 0.0028 at N=1000) — every number this
   project reports depended on an unpreregistered free parameter. Fixed: `samples_per_fit` is now a
   required baseline entry and a swept axis (`configs/main_campaign.toml`), which also produces
   RQ6's design-chart deliverable (see above) — a genuine research output the audit's council review
   found hiding inside the existing sweep, not scope creep, since runtime is not a constraint
   (117,950 fits measured at 1.3 seconds total, per the audit's Part 0).
2. **`hysteresis_magnitude` and `photon_scale` axes added** (finding F6). The prior config had no
   way to answer RQ3 (hysteresis) or RQ4 (Poisson vs. Gaussian noise) even though Week 2 built both
   mechanisms — the preregistered research questions were unanswerable from the preregistered
   config. Fixed: both are now required baseline entries and swept OFAT axes.
3. **`arc_fraction` implemented** (finding F5). Called "the single most consequential axis for
   numerical stability" (Day 3) and present in 99 of 359 conditions, it had zero implementation in
   `src/` despite the Week 2 close-out declaring the forward model complete. Fixed:
   `src/hoqi_bench/arc.py`, tested against the actual resulting phase-span property, not just the
   ramp formula.
4. **Fraction-to-absolute conversion implemented** (finding F2). `dc_offset`/`noise_std` are
   specified as fractions of A but the transforms take absolute values; nothing converted between
   them, a silent 1.11x error at the baseline. Fixed: `src/hoqi_bench/resolve.py`.
5. **Hysteresis direction-of-travel fixed to use ground truth, not the noisy signal** (finding F1).
   Measured direction-agreement with the clean signal fell to 57% (chance = 50%) at noise_std=0.05,
   the campaign's own swept range — RQ3 would have measured a response to noise, not to hysteresis.
   Fixed: `transforms.hysteresis` now takes `true_displacement` explicitly
   (`forward_model`'s `x_true`), never derived from the measured signal.
6. **Seed pairing decided and enforced structurally** (finding F3). Previously undecided whether
   "seed k" means the same noise realization across all 7 methods; also, `forward_model` and
   `noise.gaussian_noise` were measured to share a bit-identical RNG stream at equal seed. Fixed:
   `forward_model`'s own randomness removed entirely (finding F11, below); `src/hoqi_bench/seeds.py`
   provides `derive_seed`, which structurally cannot accept a method identifier, so pairing across
   methods is enforced by the function signature, not left as a convention.
7. **Wrapped (circular) phase error metric added** (council peer-review finding, not independently
   caught by the initial audit pass). Naive linear phase-difference RMSE overstates error near +-pi
   wrap boundaries by orders of magnitude. Fixed: `src/hoqi_bench/metrics.py`'s
   `wrapped_phase_error`, mandated by `docs/WEEK3_METHOD_CONTRACT.md`.
8. **Fit-failure contract and Day 21 gate criteria written in advance** (council peer-review
   findings). Without an explicit contract, a failed fit could be silently dropped rather than
   recorded, making the preregistered "failure rate reported separately" commitment unenforceable;
   without pre-written gate criteria, Day 21 risks becoming "looks close enough" after seeing
   results. Fixed: `docs/WEEK3_METHOD_CONTRACT.md`, including the Fitzgibbon <-> Halir & Flusser
   equivalence assertion as a positive test (agreement expected in well-conditioned regimes,
   divergence expected in ill-conditioned ones, per Day 3's finding).
9. **`config.py` validation tightened** (finding F9). A config could previously validate cleanly
   while its baseline covered only the axis it happened to sweep — `configs/smoke.toml` did exactly
   this, missing `dc_offset`/`noise_std`/`quadrature_error_rad` entirely. Fixed: baseline must now
   cover `REQUIRED_MODEL_PARAMS`, every parameter the model actually consumes.
10. **Internal seed-count contradiction fixed** (finding F7): `docs/experimental_design.md` Section 5
    said 30 seeds, contradicting 50 everywhere else, including this document. Fixed directly (hygiene).
11. **`forward_model`'s duplicate, misleadingly-named noise path removed** (finding F11):
    `shot_noise_std`/`thermal_noise_std`/`mains_amplitude`/`drift_amplitude` were unused by any
    config or test, duplicated `noise.py`'s composable, tested noise path, and `shot_noise_std` was
    actually intensity-independent Gaussian noise, not physical shot noise. Removed.

**What was NOT changed**: the five research questions (RQ1-RQ5, RQ6 is additive, not a
replacement), the core 5 classic OFAT axes' ranges and justifications, the 3 interaction grids, the
50-seeds-per-condition decision, the Bonferroni correction scheme, and the breakdown-threshold
ordinal/quantitative distinction — all of v1's actual research judgment survives unchanged; only the
mechanisms that turn that judgment into an executable config were broken, and are what this revision
fixes.

## What counts as deviating from this plan

Any change to the parameter ranges, metrics, or statistical protocol after this point must be
recorded as an explicit, dated deviation in this document (not silently edited in), with the reason
stated — exactly as both the v1 and v2 revision histories above were themselves handled.

## Deviations recorded after the v2 external timestamp

### D1 — 2026-07-27 (Day 21): arc sampling convention changed to `endpoint=False`

**What changed.** `arc.build_arc_ramp` previously placed its `samples_per_fit` samples via
`np.linspace(0, 1, n)`, i.e. inclusive of both endpoints. It now uses `endpoint=False`: the samples
sit at the left edge of `n` equal sub-intervals of a phase window of length exactly
`arc_fraction * 2π`. The window covered is unchanged; the final sample now sits one sampling step
short of its far edge instead of on it.

**Why.** Day 21's cross-validation gate (`tests/test_cross_validation_gate.py`, Tier 1b) was
designed to ask whether the exactness the analytic oracle proves for each method survives the
project's own simulation path. It did not. At `arc_fraction = 1.0` the inclusive convention samples
phase `0` and phase `2π` — the same physical point — so one sample in every full-circle record was a
duplicate. That makes `mean(I) = I₀ + A/N` rather than `I₀`, which biases the Heydemann method's
second-order-moment estimator, and only that method, by `~1/N` radians. Measured on the
**noiseless, undistorted** condition: 3.8e-2 rad RMSE at N=20, 1.3e-2 at N=60, 3.9e-3 at N=200,
7.9e-4 at N=1000 — against 1.1e-7 rad for the other six methods at every N.

**Why this rose to the level of changing a preregistered mechanism.** Three things, none of which
were known when Day 17 first found the bias and deliberately left it (`docs/journal/day17.md`,
"Bias 1"):

1. `arc_fraction = 1.0` is the **campaign baseline**, so this applied to every condition on every
   OFAT axis and every interaction grid except the arc sweep itself — not to one corner case.
2. The `1/N` scaling lands squarely on the preregistered `samples_per_fit` axis (**RQ6**), where it
   would have produced a clean, monotone, entirely artifactual "Heydemann's error falls as 1/N"
   curve, five orders of magnitude above every other method, indistinguishable on inspection from a
   real finding about moment-estimator sample efficiency. RQ6's whole purpose is a practitioner-
   facing "for noise σ, use N points to reach accuracy ε" chart; publishing a sampling artifact into
   that chart is a worse outcome than changing the convention.
3. The three preregistered *classic* axes would have shown Heydemann — the method
   `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` classifies as tautologically guaranteed to win there —
   as roughly twelve orders of magnitude *worse* than the other conic fitters at the low-noise end.
   That is a falsification of the project's own structural prediction produced entirely by a
   `linspace` argument.

**Why this does not flatter any method.** Verified directly: the other six methods' outputs are
identical to ~1e-15 under both conventions. The change removes an artifact that penalised one
method; it does not add information to any. `endpoint=False` is also the standard periodic-sampling
convention — a record of `N` samples covering exactly one cycle contains each phase exactly once.

**Timing.** Made before any campaign data exists, which is the cheapest possible moment and the same
reasoning v2's own revision history gives for its pre-data fixes.

**What was NOT changed.** No parameter range, no metric definition, no statistical protocol, no
research question. `arc_fraction` still means exactly what it always meant.

### D2 — 2026-07-28 (Day 23): cyclic-error amplitudes carry a conditioning flag

**What changed.** The Metrics section commits to reporting first- and second-order cyclic-error
harmonic amplitude. `hoqi_bench.harmonics.cyclic_error` implements this via least-squares
projection of the wrapped phase residual onto `[cos(kφ), sin(kφ)]` for `k=1,2`, evaluated at the
*true* phase — not an FFT, and not evaluated at sample index. It now also reports the harmonic
design matrix's condition number and a boolean `well_conditioned` flag alongside both amplitudes.

**Why least squares and not an FFT.** An FFT assumes the record spans a whole number of periods.
99 of the main campaign's 359 conditions have `arc_fraction < 1.0`, where that assumption is false
and the FFT's bins no longer correspond to the harmonics of interest. Measured on a residual with
injected `A₁ = 0.05`, `A₂ = 0.03`: at `arc_fraction = 0.5` the FFT reports `A₁ = 0.0311` (38%
wrong) and `A₂ = 0.0074` (75% wrong), while the least-squares projection is exact to 1e-16 at
every `arc_fraction` tested down to 0.02, noiseless.

**Why the conditioning flag was added.** Algebraic exactness on noiseless data is not the same as
usability with realistic noise. `cos(φ), sin(φ), cos(2φ), sin(2φ)` become nearly collinear as the
sampled arc shrinks — a fragment of a cycle cannot distinguish "some first harmonic" from "some
second harmonic" — so the estimator degrades badly while still returning a confident number, with
no exception and no warning. Measured over 200 seeds, N=60, residual noise σ=0.005, injected
`A₁=0.05`/`A₂=0.03`:

| `arc_fraction` | design-matrix `cond` | median A₁ rel. err | median A₂ rel. err |
|---|---|---|---|
| 1.0 | 1.00 | 1.3% | 2.1% |
| 0.5 | 3.50 | 1.4% | 2.7% |
| 0.35 | 10.25 | 1.6% | 9.2% |
| 0.25 | 33.4 | 6.1% | 19.4% |
| 0.15 | 180.9 | 34.1% | 35.4% |

`cond` tracks this degradation monotonically and is a property of the data (`true_phase`
sampling), not of `arc_fraction` directly — so it is measured and reported, not inferred from the
axis value. `HARMONIC_CONDITIONING_LIMIT = 10.0` is the largest `cond` at which the harder of the
two quantities (second-order amplitude) stays under 10% median relative error at the campaign's
own noise baseline; it corresponds to `arc_fraction ≈ 0.35`.

**This does not remove or replace the preregistered metric.** Both amplitudes are computed and
reported at every condition, always — `well_conditioned=False` is a reporting flag, matching
`aggregate.is_rankable`'s existing choice to report a hard condition's numbers while withholding
its ordering, not a silent drop. Week 5/6 analysis must not aggregate cyclic-error amplitudes
across conditions, or rank methods by them, without conditioning on this flag.

**A caveat for aggregation, found while writing the Day 24 sweep runner.** `conditioning` depends
only on the true-phase sampling, so a *failed* fit (all-NaN `recovered_phase`) still reports
`well_conditioned=True` alongside NaN amplitudes — the phase sampling genuinely was
well-conditioned even though the fit itself failed. Filtering on `well_conditioned` alone
therefore does not exclude failed fits; Day 28's analysis must filter on
`well_conditioned AND NOT failed`.

### D3 — 2026-07-28 (Day 25): breakdown-threshold's denominator, interpolation scale, and
crossing semantics, resolved via `llm-council` before implementation

**What was ambiguous.** The Statistical protocol section's breakdown-threshold definition
("smallest swept value where mean error ... first exceeds 1% relative RMS error, via linear
interpolation between grid points") leaves three operational questions unanswered: what "1%
relative" is relative to; whether "linear interpolation" means linear in the raw parameter even on
`arc_fraction`'s log-spaced grid; and what "first exceeds" means when a curve isn't monotonic or is
already above tolerance at the first grid point. Rather than resolve these by individual
judgment, they were put to a 5-advisor `llm-council` session (Contrarian, First Principles
Thinker, Expansionist, Outsider, Executor), followed by a full 5-way anonymized peer review —
matching the adversarial-review discipline this document's own v2 revision history and D1 already
used for decisions of comparable weight.

**Denominator, resolved: `hoqi_bench.reference_scale.PREREGISTERED_TOLERANCE_M`, identical on
both axes** (`amplitude_ratio` and `arc_fraction`) — an absolute meters comparison
(`displacement_rmse_m > PREREGISTERED_TOLERANCE_M`), not a per-condition percentage. All 5
advisors converged on a fixed physical denominator over the record's own displacement range,
which would make `arc_fraction`'s own threshold self-referential (the yardstick shrinking along
with the phenomenon being measured, as `arc_fraction` itself shrinks). One advisor (assigned the
Contrarian role) correctly caught that the analogy first offered to the council — that this
mirrors Day 21's choice of an explicit denominator — was imprecise: Day 21's denominator
(`arc_fraction * 2*pi`) is condition-*dependent*, the literal opposite of a fixed constant's
condition-*independence*. Peer review resolved this without overturning the majority conclusion:
the principle Day 21 actually established was **anti-circularity** — the denominator must not be
a function of the noisy, fitted quantity the metric is scoring — not fixedness per se.
`arc_fraction * 2*pi` is condition-dependent but not self-referential (a deterministic nominal,
known before any fit is attempted); `PREREGISTERED_TOLERANCE_M` satisfies the same principle even
more strongly. Verified before reuse (per the Contrarian's "theater risk" challenge that this
might be rubber-stamping an existing default): `git log --follow` confirms `reference_scale.py`
was introduced in Day 22 for displacement-error classification, a different purpose, before any
breakdown-threshold code existed.

**Interpolation scale, resolved: match each grid's own design — unanimous, zero disagreement
across all 5 advisors.** Linear interpolation in the raw value for `amplitude_ratio` (linearly
spaced); linear interpolation in `log(arc_fraction)` for `arc_fraction` (log-spaced, spanning two
orders of magnitude). `hoqi_bench.statistics.breakdown_threshold`'s `log_scale` parameter is an
explicit boolean the caller sets per axis, never inferred from grid spacing at runtime.

**Scan direction and crossing semantics, resolved.** Scan proceeds in the order the caller
supplies `parameter_values`/`mean_errors` — an explicit contract (easiest-to-hardest), not
inferred from array order or grid direction. First crossing in that order wins; later
re-crossings are ignored, never averaged. **Two edge cases the original three ambiguities did not
name, surfaced independently by all 5 peer reviews**: (1) a method already above tolerance at the
first, easiest grid point (e.g. `raw_atan2`); (2) a method that never crosses tolerance anywhere in
the swept range — the mirror image of (1), and per `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`
almost certainly the *more* common case for this benchmark's near-ceiling conic fitters on these
axes. A `float | None` return type cannot distinguish these two cases from each other or from a
genuine crossing at the first grid point. Resolved via `hoqi_bench.statistics.BreakdownThreshold`,
a three-outcome result (`status` one of `"found"`, `"broken_at_start"`, `"no_breakdown_in_range"`,
with `value` populated only for `"found"`).

**Left as an explicit, unresolved limitation** (escalated by 3 of 5 peer reviews as beyond what
the council could decide on its own, not silently ignored): no uncertainty quantification on the
interpolated crossing point itself. The estimate comes from noisy per-condition means on a finite
grid, and noise near the threshold could shift which grid point registers as "first." Not
addressed in Day 25's implementation — left for a Week 6 judgment call on whether it belongs in
this benchmark's scope, per this document's standing rule that a statistical test not
preregistered is flagged, not silently added.

**A fourth detail, not put to the council because an existing preregistered decision already
settles it: which test underlies the Bonferroni-corrected pairwise comparison.**
`docs/experimental_design.md` names "an uncorrected pairwise t-test" as the baseline this project
corrects, deferring "full detail" to Day 25. The v2 seed-pairing decision above (every method
evaluated against the identical noise realization at a given `(condition, seed_index)`,
specifically to remove shared-noise-draw variance from method-vs-method comparisons) resolves it
without ambiguity: `hoqi_bench.statistics.pairwise_comparisons` uses a **paired** t-test
(`scipy.stats.ttest_rel`) on same-seed-index differences, since an unpaired test would discard
exactly the variance reduction the pairing was built to provide. A seed where either method has a
NaN result (Week 3's fit-failure contract) is excluded from that specific pair's comparison only,
not from every pair.

**What was NOT changed.** No parameter range, no other metric definition, no other statistical
protocol, no research question. The breakdown-threshold statistic itself — what it measures and
which two axes it applies to — is unchanged; only its previously-unstated operational definition
is now explicit.

### D4 — 2026-07-28 (Day 26): cross-platform byte-identical reproducibility is Linux-specific

**What was found.** Day 26 added a CI job running the smoke campaign on a 3-OS x 2-Python-version
matrix, asserting a single committed SHA-256 hash. Linux matched on both Python versions. macOS
produced one different hash, identical across its own two Python versions. Windows produced a
third different hash, likewise identical across its own two Python versions. Each platform is
internally deterministic — the discrepancy is not flaky — but the three platforms do not agree
with each other.

**Why this is not a bug.** A real algorithmic bug would not reproduce byte-for-byte identically
across two independent Python versions on each of three different operating systems. This is the
expected signature of genuine floating-point non-portability: transcendental functions
(`sin`/`cos`/`arctan2`, used throughout `forward_model.py`) and LAPACK routines (the SVD underlying
`kasa.py`'s `np.linalg.lstsq`) are not required by IEEE 754 to round identically across different
platforms' math libraries, only within a platform.

**Decision (Nishi, 2026-07-28, presented per this document's stop-and-ask trigger for exactly this
scenario).** Linux's exact hash remains the source of truth — it is the environment Day 27's actual
125,650-run main campaign executes in. macOS and Windows are instead verified NUMERICALLY against
the same reference values, within a tolerance (`rtol=1e-9`, `atol=1e-15`) chosen to be far looser
than machine epsilon (so ordinary ULP-level platform noise passes) while remaining many orders of
magnitude tighter than any real regression this project's own bugs have produced (D1's arc-sampling
defect was ~1e-2 relative). See `tests/test_reproducibility.py` for the two-tier implementation.

**What was NOT changed.** No parameter range, no metric definition, no statistical protocol, no
research question, and no change to how the actual main campaign runs — this affects only how
cross-platform CI verification is scored, not the campaign itself.
