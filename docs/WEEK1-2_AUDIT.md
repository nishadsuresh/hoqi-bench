# Weeks 1-2 Audit (Days 0-14)

Run 2026-07-26, before Week 3 begins and before any campaign data exists. Commissioned because the
project is ahead of schedule, and the cheapest time to find a design defect is before the code that
depends on it is written.

**Method.** Every finding below was verified by executing code, not by reading it. Two hypotheses
that looked like defects were tested and **falsified**; they are recorded here as falsified rather
than deleted, because a list that only contains confirmed findings hides its own selection process.
The confirmed list was then pressure-tested through a 5-advisor adversarial council with anonymized
peer review (the same process used at Day 6).

**Standing at the time of audit:** 47/47 tests passing, `ruff` clean, `mypy --strict` clean on
`src/`, 18 commits, 10 unpushed.

---

## Part 0 — What the audit falsified

Recorded first, deliberately. Both of these were plausible enough to be worth testing, and both are
wrong. Neither should be revived.

| Hypothesis | Verdict | Evidence |
|---|---|---|
| DC offset applied before hysteresis breaks hysteresis's radius/angle computation (it centres on `mean_intensity`, but DC offset moves the true centre) | **FALSIFIED — second-order, not worth acting on** | Measuring about the true centre, up-minus-down radius difference stays within 0.02% of the model's `2h` at `dc=0.02`, and 0.62% at `dc=0.10`. Measuring about a shifted centre perturbs the up and down radii almost equally, so the *difference* survives. Real but negligible. |
| The 117,950-run campaign is a runtime/schedule risk | **FALSIFIED — a non-issue by ~4 orders of magnitude** | All 117,950 Kasa-equivalent fits at N=60 take **1.3 s** total (11.2 µs/fit, measured). Even at 50× for the iterative EIV method, the campaign is minutes. `docs/experimental_design.md`'s Day 26 "reduce grid resolution if runtime exceeds 12 hours" fallback is dead code. **This inverts into an opportunity — see A1.** |

---

## Part 1 — Confirmed findings

Ordered by severity, with the measurement that establishes each.

### F1 — Hysteresis reads direction-of-travel from the *noisy* signal (CRITICAL, threatens RQ3)

`transforms.hysteresis` computes local phase direction via `sign(gradient(unwrap(arctan2(q_ac, i_ac))))`
on whatever signal it receives. Per `pipeline.py`'s documented order, noise is applied at step 4 and
hysteresis at step 5 — so the direction signal is derived from noise-corrupted data.

Measured agreement with the clean-signal direction:

| `noise_std` | as % of A | direction agreement | |
|---|---|---|---|
| 0.000 | 0.0% | 100.0% | OK |
| 0.005 | 0.6% | 98.2% | OK |
| 0.010 | 1.1% | 84.3% | degraded |
| 0.020 | 2.2% | 68.8% | degraded |
| 0.050 | 5.6% | **57.2%** | ~chance (50%) |
| 0.100 | 11.1% | **53.4%** | ~chance |

The campaign sweeps noise to 0.1. So wherever hysteresis and noise coexist, the hysteresis effect is
**not the modelled physical effect** — it is a noise-driven random radial perturbation. RQ3 asks
whether static-correction methods survive direction-dependent nonlinearity; on this implementation
it would instead measure their response to noise, and the two are not distinguishable in the output.

**The council sharpened the framing, and the correction matters.** This is not primarily a
noise-robustness bug — it is a *category error*. Direction of travel is a property of the mirror's
commanded motion, which the generator owns (`x_true` is already returned by
`simulate_ideal_interferometer`). Deriving it from the measurement is modelling the wrong thing.
Stating it as "we made it noise-robust" invites the objection that the fix is an oracle leak;
stating it as "direction is a generator-side property" is correct and is not a leak, because the
*methods under test* never see it.

### F2 — Config units are fractions of A; transform APIs are absolute; no conversion layer exists

`main_campaign.toml` and `experimental_design.md` define `dc_offset` as `[0, 0.2] * A` and
`noise_std` as `[0, 0.1] * A`. `transforms.dc_offset` and `noise.gaussian_noise` take **absolute**
values. Nothing converts between them. With `A = mean_intensity * contrast = 0.9`, feeding config
values straight in makes every distortion **1.11× larger than the preregistered intent** — a
systematic error on every reported point on two of five axes, and on two of three interaction grids.

### F3 — RNG streams collide at equal seed; no seed-derivation discipline; pairing undecided

`forward_model(seed=s)` and `gaussian_noise(seed=s)` both call `np.random.default_rng(s)`. Compared
first-draw to first-draw: **correlation = +1.000000, max difference 1.1e-16 — a bit-identical
stream.** This is currently masked only by an accident: a probe using `thermal_noise_std` looked
independent purely because thermal is the *second* draw. Nothing guarantees that offset.

Separately and more consequentially: nothing records whether "seed k" means the *same* noise
realization across all 7 methods. It should — paired comparison removes the shared noise term from
every method-vs-method difference and buys a large variance reduction for free. This cannot be
retrofitted after the campaign runs.

### F4 — Samples-per-fit N is specified nowhere, and it sets every reported number

`experimental_design.md` asserts "a cheap ellipse fit on ~60 points." `grep` for `n_samples`,
`n_points`, `num_samples` across `src/`, `configs/`, and both design docs: **no matches anywhere.**
N is whatever the caller's `t` array happens to be.

Measured mean centre error vs N (200 trials, noise 0.05):

| N | 20 | 60 | 200 | 1000 |
|---|---|---|---|---|
| mean centre error | 0.0201 | 0.0116 | 0.0063 | 0.0028 |

A 7× swing. N is an unpreregistered free parameter sitting underneath the entire campaign.

### F5 — `arc_fraction` has zero implementation

Called "the single most consequential axis for numerical stability" (Day 3), it appears in 9 OFAT
conditions plus the 90-condition `arc_x_noise` grid — **99 of 337 conditions**. `grep` across `src/`:
no implementation exists. The Week 2 close-out declared the forward model complete; it is not.

### F6 — The campaign config cannot answer RQ3 or RQ4

`main_campaign.toml` sweeps `amplitude_ratio`, `quadrature_error_rad`, `dc_offset`, `arc_fraction`,
`noise_std`. It contains **no hysteresis axis and no Poisson/`photon_scale` axis**. RQ3 is about
direction-dependent hysteresis; RQ4 is Poisson-vs-Gaussian. Both were built in Week 2 and neither is
reachable from the preregistered parameter space. The preregistration commits to questions its own
locked config cannot address.

### F7 — `experimental_design.md` contradicts itself on seed count

Section 2 says seeds were raised "from 30 to **50**." Section 5 says "**Seeds per condition: 30**"
and "across the 30 seeds." The preregistration, the config, and Section 2 all say 50. Section 5 is
stale text surviving inside the document that is supposed to be locked.

### F8 — `config.py` docstring states the wrong campaign size

`src/hoqi_bench/config.py:7` claims "10,290 for the proposed main campaign." Actual: 117,950. The
value was superseded by the Day 5 expansion; the docstring was not updated.

### F9 — Config validation accepts unrunnable configs

`_validate` requires a baseline entry for every *other* swept parameter. It does not require the
baseline to cover the model's actual parameter set. `configs/smoke.toml` validates cleanly while
missing `dc_offset`, `noise_std`, and `quadrature_error_rad` — a config that passes validation and
then cannot be executed, or worse, is silently defaulted at Day 24.

### F10 — The "mypy --strict clean" claim excludes tests/ and scripts/

`pyproject.toml` sets `files = ["src/hoqi_bench"]`. `tests/` and `scripts/` are never type-checked,
though the claim is repeated in the README, the validation summary, and journal entries.

### F11 — Two parallel noise paths, one misleadingly named

`forward_model` carries `shot_noise_std` / `thermal_noise_std` / `mains` / `drift` parameters, while
`noise.py` provides composable noise transforms. Two ways to add noise. `forward_model`'s
`shot_noise_std` is **not shot noise** — it is intensity-independent Gaussian, as its own docstring
concedes. A future caller can double-apply noise, or apply the wrong model, with nothing catching it.

---

## Part 2 — Council verdict

Five advisors, anonymized peer review. **4 of 5 reviewers independently ranked the First Principles
response strongest; all 5 independently flagged the Expansionist as having the largest blind spot.**

### Where the council agreed

- **F2, F4, F5, F6, F9 are not five findings — they are one.** There is no compiler between
  `PREREGISTRATION.md` and the set of runs actually executed. Prose names parameters that no code
  reads, and code accepts configs that cannot run. The permanent fix is a **resolver that turns a
  config into an explicit run manifest and errors on any unbound parameter** — a config that does
  not specify N cannot execute. That single mechanism closes all five, and closes the *class*.
- **F1 is not a tradeoff to debate.** Use the generator's ground-truth phase. No defensible alternative.
- **F3's pairing decision is free statistical power** and must be made before the campaign, not after.

### Where the council clashed — and how it resolves

The load-bearing disagreement: **void the preregistration and re-register (First Principles,
Contrarian, Outsider) vs. patch in place and log dated deviations (Executor) vs. expand the campaign
opportunistically (Expansionist).**

**Verdict: re-preregister, and the council under-weighted the fact that makes this easy.**

Preregistration exists to stop results from steering the design. **Zero campaign results exist.**
Week 3 has not started. So revising now costs *nothing epistemically* — there is no result to be
steered by. Filing 5+ dated deviations against a flagship reproducibility artifact makes the
artifact its own counterexample; one clean, dated, honest reset before any data exists is stronger,
and the postmortem is a better portfolio artifact than a suspiciously clean sweep.

The Expansionist's expand-the-campaign instinct was rejected by all five reviewers *as framed* —
retroactively promoting discovered gaps into "planned" axes is the exact post-hoc flexibility
preregistration prevents. **But its underlying observation is correct and survives**: runtime is
falsified as a constraint, so v2 can be substantially richer than v1. The distinction that makes it
legitimate: this is a **pre-data re-registration**, not a mid-campaign amendment.

The Outsider's point stands on its own and is cheap: **the preregistration is a file in a repo the
author controls, with a rewritable history.** That is a note to self, not a preregistration. It
needs an external timestamp (OSF or a Zenodo DOI) before Week 4 runs, or the deviation log is also
just a file the author controls and the whole framing collapses.

### Blind spots the peer review surfaced

- **The test suite validates the wrong things.** 47/47 passed while 11 defects existed, including a
  completely unimplemented axis. Tests confirm each transform matches its own formula; nothing tests
  that the *config-to-run path* is coherent, because that path does not exist yet. Adding more
  Week-3 tests of the same shape will not catch defects of this class.
- **No fit-failure contract.** Kasa on a 2% arc will return garbage or hit a singular matrix, across
  thousands of runs. If a failed fit drops its row, Week 5 silently averages over survivors and every
  method looks equally good. Decide now: NaN plus a reason code, never a dropped row.
- **No primary endpoint, and the wrong error metric.** 337 conditions × 7 methods with no declared
  primary metric is a garden of forking paths. And **phase error requires circular statistics** —
  errors must be wrapped to (−π, π] before RMS, or a wrap at ±π registers as a ~2π error and
  dominates the mean.
- **Ranking by circle parameters ≠ ranking by recovered phase**, and phase is what interferometry
  is for. The loss has never been defined.
- **No cross-check against published reference values.** Reproducible wrongness is still wrongness.
- **Day 21's cross-validation gate has no pass criterion.** Write the tolerances before writing the
  methods, or the gate degrades to "looks close enough."
- **Nobody has cloned this fresh and run it**, and bit-identity claims will not survive BLAS
  nondeterminism across machines.

### One domain point the council could not supply

**Halir & Flusser is a numerically stable reformulation of Fitzgibbon — in exact arithmetic they
solve the same problem and should return the same ellipse.** Taubin and Kasa are both circle fits
differing in bias correction. So near-identical results between certain method pairs are *expected*,
not a bug, and Day 21's gate should assert exactly that: F and H&F must agree to tight tolerance in
well-conditioned regimes and diverge only where conditioning degrades — which is precisely the Day 3
finding. That turns an interpretation risk into a positive test.

---

## Part 3 — The three lists

### A. Alter *now* to make the experiment better

Authorized to disrupt the existing plan; downstream schedule to be re-fitted afterward.

| # | Change | Why now |
|---|---|---|
| **A1** | **Promote N (`samples_per_fit`) to a config field *and* a sweep axis.** | Closes F4. Runtime is falsified as a constraint (1.3 s), so this is nearly free. N is the parameter a real experimentalist actually controls (integration time vs. drift). Yields a practitioner-facing design chart — "for noise σ, use N points to reach accuracy ε" — which does not currently exist for HQI. |
| **A2** | **Add `hysteresis_magnitude` and `photon_scale` axes.** | Closes F6. Without these, RQ3 and RQ4 are unanswerable and Week 2's hysteresis and Poisson work is unreachable. |
| **A3** | **Implement `arc_fraction`.** | Closes F5. 99 of 337 conditions depend on it and it does not exist. |
| **A4** | **Declare paired seeds across methods; add `derive_seed(base, stream)`.** | Closes F3. Large variance reduction on every method-vs-method comparison, at zero cost, and impossible to retrofit post-campaign. |
| **A5** | **Add a fraction→absolute resolution layer at config load.** | Closes F2. Otherwise every point on two axes and two grids is 1.11× off. |
| **A6** | **Hysteresis direction from generator ground truth.** | Closes F1. Frame as a category correction, not a robustness patch. |
| **A7** | **Define the primary endpoint: wrapped phase error, circular statistics.** | Prevents the ±π wrap artifact from dominating, and stops the forking-paths problem before data exists. |
| **A8** | **Define the fit-failure contract: NaN + reason code, never a dropped row.** | Failure rate is already a first-class preregistered metric; it is uncollectable if failures vanish. |
| **A9** | **Write Day 21's pass criteria now**, including the Fitzgibbon ≡ Halir & Flusser equivalence assertion. | A gate authored after seeing results is not a gate. |

### B. Prevalent issues that will affect later weeks

| # | Issue | Bites in |
|---|---|---|
| **B1** | No compiler between prereg and runs — prose parameters no code reads (root cause of F2/F4/F5/F6/F9) | Week 4, campaign launch |
| **B2** | Test suite validates transforms against their own formulas; nothing tests config→run coherence | Week 3 onward — more tests of the same shape will not help |
| **B3** | Preregistration has no external timestamp; repo history is rewritable | Weeks 5-6, at DOI/release — retroactively fatal to the central claim |
| **B4** | No methods cross-checked against published reference values | Week 3, Day 21 gate |
| **B5** | Reproducibility never demonstrated — no fresh clone, no second machine, BLAS nondeterminism unaddressed | Weeks 5-6; it is the *stated contribution* and is currently unevidenced |
| **B6** | Two parallel noise paths (F11), one misleadingly named | Week 4 — silent double-application |
| **B7** | 10 commits unpushed; `workflow` OAuth scope still unauthorized | Continuous — an unpushed repo has no external record at all, compounding B3 |

### C. Process improvements for Weeks 3-6

| # | Improvement |
|---|---|
| **C1** | **Config is the single source of truth.** A run manifest resolver that errors on any unbound parameter. Documentation describes the config; it never *defines* parameters. |
| **C2** | **Add a doc-consistency check to CI.** F7 and F8 are contradictions a script can catch: assert claimed run counts and seed counts match the loaded config. The Day 14 triple-check found these by hand; automate it. |
| **C3** | **Extend mypy to `tests/` and `scripts/`** (F10) so the claim matches the configuration. |
| **C4** | **Independent verification gate per week, not per project.** Weeks 1-2 produced 11 defects behind a green suite; the Week 3 methods need a reviewer that is not the implementer, before Week 4 locks results in. |
| **C5** | **Tighten config validation** to require baseline coverage of the full model parameter set (F9). |
| **C6** | **Fresh-clone CI job** — clone, install, run smoke campaign, from scratch. Directly evidences the reproducibility claim rather than asserting it. |
| **C7** | **Keep recording falsified hypotheses**, as Part 0 does. It is the strongest available evidence that the audit process is real and not confirmatory. |

---

## Recommended sequencing

1. **External timestamp first** (OSF or Zenodo) — cheap, and everything else's credibility depends on it. Resolve the push blocker (B7) at the same time.
2. **Re-preregister as v2, pre-data**, keeping v1 verbatim as `prereg-v1-superseded.md` plus a one-paragraph postmortem. Fold in A1-A9. Explicitly state that this is a pre-data revision with zero results collected — that is what makes it legitimate.
3. **Build the resolver (C1)** before any Week 3 method code.
4. **Then** Week 3's methods, against Day 21 criteria written in advance (A9).

Hygiene items F7, F8, F10, F11 are a single batched commit and need not block anything.
