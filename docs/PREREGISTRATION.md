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

## External timestamp (open item, not yet resolved)

A preregistration committed to a git repository the author controls, with a rewritable history, is
not independently verifiable as having existed before the campaign ran -- it is a note to self until
an external party holds a timestamp on it. **This needs an OSF preregistration or a Zenodo DOI minted
before the Day 27 main-campaign launch.** This compounds with the project's still-unresolved GitHub
push blocker (`docs/WEEK1-2_AUDIT.md`, prevalent issue B7): 10+ commits are not yet live on GitHub,
so there is currently no external record of ANY of this work, preregistration included. Both need
Nishi's action before Week 4.

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
