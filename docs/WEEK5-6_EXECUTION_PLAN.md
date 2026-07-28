# Weeks 5-6 Execution Plan — Days 29-42

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking. **Read §0 and §2 in full before touching any code.**
> §2 is not background — it changes what four of the six remaining research questions are allowed
> to claim.

**Goal:** Take hoqi-bench from "RQ1/RQ2 answered against a campaign with four undiscovered
defects" to "every research question is either honestly answered or explicitly declared
unanswered-with-cause, the defect class that produced all four is permanently guarded in CI, and
the package is released to PyPI with an immutable Zenodo DOI that will not need a correction."

**Architecture:** No new estimation code. Two new `src/` modules (`waveforms.py`,
`noise_equivalence.py`), one runner change (P3's timing wiring), two supplementary configs, four
new `scripts/` analysis entry points, and a new CI test file whose only job is to make Weeks 1-4's
defect class impossible to reintroduce. The preregistered 125,650-fit campaign in `results/raw/`
is **never regenerated** — supplementary runs write to `results/supplementary/`, a physically
separate tree, so no analysis can silently blend preregistered and post-hoc data.

**Tech Stack:** Python 3.10/3.11, numpy, scipy, pandas + pyarrow, pytest, ruff, mypy --strict,
GitHub Actions, `build` + `twine` (Day 39-40), Zenodo (Day 41).

---

## Global Constraints

Every task's requirements implicitly include this section. Carried forward verbatim from
`docs/WEEK4_EXECUTION_PLAN.md` §Global Constraints, which remains binding, plus three new entries
(the last three) that exist because of this plan's own §2 audit.

- **Python interpreter is `/home/nishadrobotics/venvs/hoqi-bench/bin/python`.** Bare `python` does
  not exist on this machine. Every command below uses the venv path explicitly.
- **BLAS threading must be pinned to 1** (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
  `MKL_NUM_THREADS`) in every process that imports numpy, **before** the first numpy import.
  `conftest.py` does this for pytest; `runner.py` does it per worker. Without it the campaign hard-
  crashes (`SystemError: attempting to create PyCFunction with class but no METH_METHOD flag`).
- **Never re-derive a seed.** `hoqi_bench.seeds.derive_seed(seed_index, condition_name, stream)` is
  the only seeding path. Its signature structurally cannot accept a method name — that is what
  enforces the preregistered paired-seeds guarantee. Supplementary runs use it too.
- **Never re-derive the phase wrapping.** Any error on recovered *phase* goes through
  `hoqi_bench.metrics.wrapped_phase_error`.
- **Never silently patch a method's known weakness.** Fitzgibbon's fragility, Kasa's unguarded
  `lstsq`, Heydemann's radius guard, and Köning's `_MAX_ITER=20` are all scientifically
  load-bearing. If a method looks broken, the fix goes in the harness or the docs, never the method.
- **Preregistered statistics only.** Bootstrap percentile CIs, interpolated breakdown thresholds
  (`statistics.breakdown_threshold`, with its three-outcome `BreakdownThreshold` result), and
  Bonferroni over 21 pairwise comparisons *per condition*. If something looks missing, flag it —
  do not add it.
- **Every threshold is measured before it is written down.** No round-number constants chosen by
  taste. See `heydemann.py`'s `_RADIUS_CONSISTENCY_THRESHOLD` and
  `harmonics.HARMONIC_CONDITIONING_LIMIT` for the pattern: probe, tabulate, pick a value with
  margin on both sides, document the data at the constant.
- **Documentation standard** (`docs/DOCUMENTATION_STANDARD.md`) applies to every new module, plus a
  `docs/journal/dayNN.md` entry per day.
- **NEW — preregistered data is immutable.** `results/raw/` and `results/main_campaign_summary.csv`
  are read-only for the rest of the project. Any supplementary run writes to
  `results/supplementary/<experiment_name>/`. No script may read from both trees into one frame
  without an explicit `provenance` column distinguishing them. This is enforced by a test (Task 1).
- **NEW — every supplementary experiment's protocol is committed and pushed BEFORE it is run.**
  See §0.6. This is the single mechanism neutralising the forking-paths objection, and it is not
  optional.
- **NEW — the Zenodo DOI is immutable and is the LAST irreversible action of the project.** It is
  gated on Tasks 1, 9, and 10 all being complete. Do not mint it early to "get it out of the way."

---

## 0. How to use this document

### 0.1 Who this is written for

This plan assumes an executor who is a competent Python developer but who has **not** read this
codebase, has **not** read the papers, and was **not** present for Weeks 1-4. Every non-obvious
decision is explained where it is made. Where a probe has already been run, the numbers are in the
plan — you should not have to rediscover them. Where something is deliberately left open, it says
so and tells you how to close it.

**The specific failure mode this plan is written against:** Weeks 1-4 produced a green 181-test
suite, clean `mypy --strict`, CI passing on 3 OSes, an OSF-timestamped preregistration, two
adversarial council reviews, and a formal cross-validation gate — and *still* shipped a campaign in
which one research question measured the wrong phenomenon entirely, another was arithmetically
unanswerable, and a third preregistered metric was never recorded at all. Every one of those was
found by **executing code and looking at the actual numbers**, not by reading the code and not by
running the test suite. Assume the same is true of anything this plan asks you to verify.

### 0.2 The defect-resolution rule (standing instruction from Nishi, 2026-07-28)

> "If something is marked as incorrect or could be marked as a bug, I want you to loop back to fix
> it. Do not stop until it is solved."

This overrides the instinct to note a problem and move on. Operationally:

1. When you find something that looks wrong, **stop the current task.** Do not finish the step first.
2. **Invoke `superpowers:systematic-debugging`** and follow it. Do not start guessing at fixes. Its
   first requirement is a written hypothesis before any code change.
3. Classify the cause explicitly as one of:
   - **(i) implementation error** — fix it, commit with the root cause in the message.
   - **(ii) a difference in test conditions** — write it up as a finding. Do *not* silently align
     the test to the code.
   - **(iii) a genuine discrepancy worth reporting** — write it up, record it as a dated deviation
     in whichever document made the claim.
4. **Only (i) is fixed silently.** (ii) and (iii) get a paragraph in the relevant doc and a journal
   line.
5. Do not proceed until the defect is fixed or recorded as an explicit dated deviation with a
   reason. "I'll come back to it" is not a resolution.
6. If unresolved after two genuine attempts, escalate to Nishi with three candidate causes and a
   recommendation — escalation means *stopping and asking*, not working around it.

**What "widening the tolerance until it passes" looks like:** a test fails at `< 1e-6`; you change
it to `< 1e-3`; it passes; you move on. That is the single failure mode this project's entire gate
structure exists to prevent. If a tolerance genuinely needs changing, the change comes with a
measurement showing the old value was wrong — never with the observation that the new value passes.

### 0.3 When to invoke which superpowers skill

Plugin installed at `~/.claude/plugins/cache/superpowers-dev/superpowers/6.2.0/skills/`. Per Nishi's
`CLAUDE.md` severity gating, do **not** invoke heavy process skills for one-line fixes.

| Situation in this plan | Skill | Why here specifically |
|---|---|---|
| Starting any task below | `test-driven-development` | Every task is written test-first; the plan gives you the failing test before the implementation. |
| A test fails unexpectedly, or a number looks wrong | `systematic-debugging` | Mandatory per §0.2. Most important row in this table. |
| Task 4 (`waveforms.py`) — before writing code | `brainstorming` | The bidirectional waveform is the one genuinely new forward-model component in Weeks 5-6, and its design determines whether RQ3's supplementary experiment is valid. Not fully settled by this plan. |
| Task 1 and Task 9 | `subagent-driven-development` | Both are several independent, well-specified sub-pieces. Fresh subagent per piece, review between. |
| Task 9 (documentation-drift audit) | `dispatching-parallel-agents` | Auditing ~15 docs against code is embarrassingly parallel. |
| Before declaring ANY task done | `verification-before-completion` | This project has been burned four separate times by "tests pass" meaning "tests pass, and a preregistered axis is measuring the wrong thing." |
| After Task 1, Task 6, and Task 10 | `requesting-code-review` then `receiving-code-review` | The guardrails, the supplementary campaign, and the release build are the three hardest-to-reverse steps. |
| Merging Weeks 5-6 work | `finishing-a-development-branch` | Only at the very end, after Task 12. |

**Do not** invoke `writing-plans` — this document *is* the plan. **Do not** invoke `brainstorming`
for any task except Task 4; the rest are settled below.

### 0.4 When to invoke llm-council

`llm-council` runs 5 independent advisors, peer-reviews them anonymously, and synthesises a verdict.
It has earned its cost four times on this project (the circularity threat; the independence
reasoning error; Day 25's breakdown-threshold ambiguities; Day 28's overclaim). It has also twice
produced a *self-correction mid-review* rather than a clean verdict — which is the actual reason to
use it.

Invoke it at exactly these two points:

1. **Task 5, before deciding RQ4's noise-equivalence protocol.** Comparing Poisson and Gaussian
   *rankings* requires a defensible mapping between `photon_scale` and an equivalent `noise_std`.
   §2.5 gives a measured mapping, but the *decision of what "equivalent" should mean* (matched
   realized σ? matched SNR? matched Fisher information?) is a judgment call about what to claim,
   is hard to reverse once published, and has no objectively checkable answer. **Prompt:** give it
   the measured table in §2.5, `noise.poisson_noise`'s variance derivation, and RQ4's exact
   preregistered text; ask which definition of equivalence makes "do the rankings change" a
   meaningful question rather than an artifact of the matching choice.

2. **Task 8, before writing any RQ3-RQ6 interpretation.** Highest-stakes writing left in the
   project, and it now has to communicate two *unanswered* research questions without either
   burying them or overdramatising them. **Prompt:** give it
   `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`, `docs/WEEK5_PREFLIGHT_AUDIT.md`, the actual result
   tables, and ask it to identify every claim that is tautological-by-construction, every claim
   where CIs overlap, every place the draft implies causation the design cannot support, and every
   place a defect is being spun as a finding.

**Do not** invoke it for: choosing a file layout, a config schema, a CI matrix, or anything with an
objectively checkable answer. Run the experiment instead. Do not use it as a substitute for
`systematic-debugging` on an actual defect — five opinions about a numerical bug are strictly worse
than one traced root cause.

### 0.5 Standing rules inherited from Weeks 3-4

Binding without restatement in each task:

1. Commit at the end of every task, separately, with the reasoning in the message. Push and
   **verify CI is green after the push**, not just that the local suite passed.
2. Write `docs/journal/dayNN.md` for each day, in plain language, assuming the reader has not seen
   the code and did not read yesterday's entry. Include actual numbers, not "it works." Include what
   was left uncertain.
3. Any deviation from a preregistered or contracted claim goes in the document that made the claim,
   dated, with the reason — never as a silent edit.
4. Run `ruff check .`, `ruff format --check .`, and `mypy` before every commit. All three are
   CI-enforced.
5. Tests are oracle-independent: a test's reference must not import the code it checks. Where a
   reference formula is needed, reconstruct it in the test file.

### 0.6 NEW — the pre-commitment protocol for supplementary experiments

**Why this section exists.** RQ1/RQ2 results are already known. You (and I) now know which methods
win where. Any supplementary experiment *designed* after that knowledge exists is not a neutral
test — the choice of waveform, grid density, seed count, and reported metric are all
researcher degrees of freedom that can, without any dishonest intent, be nudged toward a cleaner
story. The llm-council session that reviewed this plan flagged this as live and underweighted, and
peer review added that a *self-dated note in a repo the author controls* carries no more evidentiary
weight than the preregistration violation it is meant to document.

**The protocol. For every supplementary experiment in this plan (Tasks 4, 6):**

1. Write the full protocol into `docs/SUPPLEMENTARY_PROTOCOLS.md` **before writing any experiment
   code**: the exact grid, the exact waveform, seed count, which metrics will be reported, the
   pre-specified pass/fail or confirm/contradict criterion, and what result would *falsify* the
   hypothesis.
2. **Commit and push it as its own commit, containing no code.** The commit message must say the
   experiment has not been run yet.
3. Only then write the code and run it.
4. If the protocol turns out to be wrong or unrunnable, **do not edit it in place** — append a dated
   amendment explaining what changed and why, exactly as `docs/PREREGISTRATION.md` handles D1-D4.
5. Report the result against the criterion as written in step 1, including when it is null or
   uninteresting.

**Do not skip step 2 on the grounds that the result is obvious.** A protocol committed after the
run is indistinguishable, to any external reader, from one written to match it.

---

## 1. State at start (verified 2026-07-28)

Confirm you are starting where this plan assumes:

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && git log --oneline -1 && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest -q 2>&1 | tail -2
```

Expected: HEAD at `686361e feat(Day 28): RQ1+RQ2 analysis, revised after llm-council caught a real
overclaim`, and `181 passed`.

**What already exists and must not be rebuilt:**

| Module | Provides |
|---|---|
| `config.py` | `load_sweep_config(path) -> SweepConfig` (`.axes`, `.grids`, `.baseline`, `.methods`, `.n_seeds`, `.tolerance`) |
| `resolve.py` | `iter_conditions(config) -> list[ResolvedCondition]` — 359 conditions, `.name` and `.resolved` (absolute units) |
| `seeds.py` | `derive_seed(seed_index, condition_name, stream)` — the only seeding path |
| `arc.py` | `build_arc_ramp(arc_fraction, n_points)` — **monotonic**; this is P1's root cause |
| `simulate.py` | `simulate_condition(resolved, condition_name, seed_index) -> SimulatedSignal` (`.i`, `.q`, `.x_true`, `.true_phase`) |
| `transforms.py` | `amplitude_imbalance`, `quadrature_phase_error`, `dc_offset`, `hysteresis` |
| `noise.py` | `gaussian_noise`, `poisson_noise` (mutually exclusive per `pipeline.py`) |
| `methods/` | `METHOD_REGISTRY`, `fit_by_name(name, i, q, *, mean_intensity)`, `timed_fit(fn, *a, **kw)` |
| `metrics.py` | `wrapped_phase_error`, `phase_error_to_displacement`, `displacement_errors`, `rmse`, `peak_absolute_error` |
| `aggregate.py` | `SeedOutcome`, `MethodConditionSummary`, `outcome_from_fit`, `is_gross_error`, `summarize`, `is_rankable` |
| `harmonics.py` | `cyclic_error`, `HARMONIC_CONDITIONING_LIMIT = 10.0` |
| `statistics.py` | `bootstrap_ci`, `breakdown_threshold` → `BreakdownThreshold`, `pairwise_comparisons` |
| `power_law.py` | `fit_power_law_exponent(magnitudes, errors) -> (exponent, coefficient, r_squared)` — raises on non-positive input |
| `runner.py` | `run_campaign(...)`, parallel, resumable, deterministic |
| `reference_scale.py` | `classify_displacement_error`, `PREREGISTERED_TOLERANCE_M`, `INSTRUMENT_NOISE_FLOOR_M` |

**Campaign size:** 359 conditions × 7 methods × 50 seeds = **125,650 fits**, measured end-to-end at
**14.32 s**. Runtime is not a constraint anywhere in this plan. Do not let a performance argument
justify a design that compromises determinism, and do not let a *schedule* argument justify skipping
a supplementary run — see §2.6 for the arithmetic.

---

## 2. What the pre-flight audit constrains about Weeks 5-6

**Read this section in full.** It is the reason this plan exists in its current form. All four
findings were verified by executing code against the real campaign config and data on 2026-07-28.
The full write-up with reproduction commands becomes `docs/WEEK5_PREFLIGHT_AUDIT.md` in Task 1.

### 2.1 P1 (CRITICAL) — RQ3's hysteresis axis never activates its direction-dependence

`transforms.hysteresis` computes `direction = np.sign(np.gradient(true_displacement))`. Every
campaign condition's waveform comes from `arc.build_arc_ramp`, which returns
`x_true = total_displacement_m * linspace(0, 1, N, endpoint=False)` — **strictly monotonic**.

Measured on `axis:hysteresis_magnitude=0.2`, seed 0:
- `np.unique(sign(gradient(x_true)))` → `[1.]`. Fraction at `+1` = **1.0**. Fraction at `-1` = **0.0**.
- Transform output is **bit-identical** (max abs diff exactly `0.0`) to the same call with an
  arbitrary monotonic ramp substituted for `true_displacement`.

So the campaign injected a **uniform radial inflation by +h**, not path-dependent hysteresis. This
is still a real, non-conic distortion — adding a constant to an ellipse's polar radius does not
yield another ellipse, which is why the response is large (33.9× dynamic range for conic fitters
over `hysteresis_magnitude ∈ [0, 0.2]`) — it is simply **not the phenomenon RQ3 names.**

**Why it was missed:** `tests/test_hysteresis.py` builds its waveform with `_up_and_down_iq()`, a
**sinusoid** (`2e-6*sin(2π·2·t)`) whose own docstring says it exists to give "'direction of travel'
[something] to be direction-dependent about." Production uses a monotonic ramp. The unit test
validates a waveform the campaign never generates.

**Constraint on Weeks 5-6:** RQ3's hysteresis half is **declared unanswered as written**. The
preregistered data may be reported only as a *static radial-inflation* sensitivity result, under
that name. Task 4's supplementary bidirectional experiment is the only thing that may speak to
direction-dependence, and only under §0.6's protocol.

**Secondary trap you must not fall into:** Kasa, Taubin and `raw_atan2` are **flat (1.0×)** against
`hysteresis_magnitude`. This is **floor-masking, not immunity** — their baseline error (3.6e-9 m,
dominated by uncorrected `amplitude_ratio=1.1` / `quadrature_error_rad=0.1`) swamps hysteresis's
largest contribution (~6e-10 m). Reporting "the circle fits are robust to hysteresis" would be
false. Any such claim must be checked against the floor first.

### 2.2 P2 (CRITICAL) — RQ6 is unanswerable from the preregistered grid

RQ6 promises "for a given noise level, what N is needed to reach a target accuracy" — a
practitioner-facing N-vs-noise design chart, described in the preregistration as a genuine research
output that does not exist in the HoQI literature.

- All 7 `samples_per_fit` conditions run at **`noise_std = 0.0`**.
- All 10 `noise_std` conditions run at **`N = 60`**.
- The three interaction grids are `arc_x_noise`, `amplitude_x_quadrature`, `amplitude_x_noise`.
  **There is no `samples_per_fit × noise_std` grid.**

Measured displacement RMSE vs N at noise = 0, N=20 → N=1000 (a 50× sample increase):

| method | ratio |
|---|---|
| fitzgibbon / halir_flusser | 1.10× |
| koning | 1.09× |
| heydemann | 0.94× (slightly *worse*) |
| kasa / taubin / raw_atan2 | **1.00× (flat to 4 significant figures)** |

The curve is flat. At σ=0 the honest answer is "N doesn't matter," which is true and useless.

**On the record:** `PREREGISTRATION.md` v2 justified *adding* this axis by citing "a measured 7x
swing in mean center error (0.0201 at N=20 vs. 0.0028 at N=1000)." That 7× is a *noise-averaging*
effect. Swept at zero noise it collapses to 1.10×. The preregistration's own stated justification is
contradicted by the axis as configured.

**Defect class:** identical to Weeks 1-2 audit finding F6 ("the preregistered research questions
were unanswerable from the preregistered config"). RQ6 was introduced *by the v2 revision that fixed
F6*, and its own answerability was never checked. It then survived the v2 council review, OSF
registration, Day 21's gate, the Week 3 review, and all of Week 4.

**Constraint:** RQ6 is **declared unanswered as written**. Task 6's supplementary N×noise grid is
the only thing that may produce a design chart, under §0.6's protocol, reported as supplementary and
never blended into the preregistered tables.

### 2.3 P3 (HIGH) — the preregistered `cost` metric is 100% unmeasured

RQ1 asks methods be compared on "displacement accuracy, cyclic-error harmonics, robustness, **and
cost**." The preregistration defines cost explicitly: "wall-clock time per fit (mean and std across
seeds, same hardware), and a secondary iteration count for iterative methods."

- `methods/base.py:154` `timed_fit()` is documented as "the ONE place runtime is measured."
- `runner.py:135` calls `fit_by_name(...)` **directly**. It never calls `timed_fit`. So
  `result.runtime_s` is always `None`.
- Measured: `runtime_s` null fraction = **1.0** in the raw parquet; `runtime_s_mean` null fraction =
  **1.0** across all 2,513 summary rows.
- It failed **silently**: `aggregate.py:241` emits `float("nan")` on an empty runtime list rather
  than raising.

`docs/RQ1_RQ2_ANALYSIS.md` omits cost entirely and does not flag the omission — so **RQ1 is
currently three-quarters answered and reads as if it were complete.**

**Constraint:** this is *not* a preregistration deviation — nothing about the ranges, metrics, or
protocol changed. It is unfinished execution of already-specified instrumentation, and Task 3
completes it. But see §2.7: the fix may require revising the already-drafted RQ1 document, which is
a real possibility the plan must not assume away.

### 2.4 P4 (MEDIUM) — RQ5's "many-fringe ramp" half was never in the grid

RQ5 asks about "many-fringe ramp vs. small steady-state vibration." `arc.build_arc_ramp` sets total
phase excursion to `arc_fraction * 2π`, and `arc_fraction` spans `[0.02, 1.0]`. So the grid spans a
0.72° arc up to **exactly one fringe**, and never reaches multi-fringe.

`docs/experimental_design.md` (§"Design choices independent of any single paper") re-describes the
top of the range as "full-circle ramp measurement" rather than "many-fringe," **without recording
that narrowing as a deviation.** That silent re-description is itself the finding: it is evidence
that a preregistered term drifted in the prose and was caught only by an audit, not by the process.

**Constraint:** RQ5 is answerable **only over the sub-fringe regime**, and must say so in those
words. Do not extend the grid — see Task 7.

### 2.5 What is NOT broken (checked, healthy) — and RQ4's one open decision

**RQ4 (`photon_scale`) is healthy.** 32.6× dynamic range for conic fitters, 1.8–1.9× for circle
fits — a real, strong response. Sweeping it at `noise_std = 0.0` is *correct by design*, not P2's
mistake.

**But be precise about *why*, because the obvious phrasing is wrong.** The two noise models are
**not** mutually exclusive by any runtime branch. `simulate.py:178-179` applies `poisson_noise`
**then** `gaussian_noise` **unconditionally, on every condition** — there is no `if`. Exclusivity is
an *emergent property of the config's baseline values*, as `simulate.py`'s own docstring states:
`noise_std = 0.0` is `gaussian_noise`'s exact identity, and `photon_scale = 1e7` at the OFAT
baseline is `poisson_noise`'s documented "negligible, **not** off."

Two consequences the RQ4 analysis must handle rather than assume away:

- The "pure Gaussian" arm is not literally pure — every `noise_std` condition also carries Poisson
  noise at `photon_scale = 1e7`, i.e. σ ≈ `sqrt(1/1e7)` ≈ 0.00032. That is ~14× below the smallest
  non-zero Gaussian level in the grid (0.0045 absolute), so it is genuinely negligible — but at
  `noise_std = 0.0` it is the *only* noise present, which is why that condition is not noiseless.
- Any claim of the form "these two arms differ only in noise model" must be stated with that caveat
  attached, not asserted flatly.

**The one open decision.** RQ4 asks whether the *rankings change* under Poisson vs Gaussian noise.
That requires comparing the two at matched noise levels, and nothing in the repo defines a mapping.
`noise.poisson_noise`'s own derivation gives `Var(intensity-domain noise) = intensity / photon_scale`,
so `σ_eff ≈ sqrt(intensity / photon_scale)`. **Measured (20 seeds per point, realized residual std
against a `photon_scale=1e12` clean reference):**

| `photon_scale` | measured σ | `sqrt(1/P)` | as fraction of A=0.9 |
|---|---|---|---|
| 100 | 0.09837 | 0.10000 | 0.1093 |
| 500 | 0.04595 | 0.04472 | 0.0511 |
| 1,000 | 0.03338 | 0.03162 | 0.0371 |
| 5,000 | 0.01423 | 0.01414 | 0.0158 |
| 10,000 | 0.01025 | 0.01000 | 0.0114 |
| 50,000 | 0.00459 | 0.00447 | 0.0051 |
| 100,000 | 0.00313 | 0.00316 | 0.0035 |

The `noise_std` grid in absolute units is `[0, 0.0045, 0.009, 0.018, 0.027, 0.036, 0.045, 0.054,
0.072, 0.09]`. The two ranges **overlap well**, so a matched comparison is possible. The measured σ
tracks `sqrt(1/P)` to within ~5% (the gap is real, from intensity varying about its mean, and must
be reported rather than rounded away).

**This mapping is measured, not assumed — but *which* definition of "equivalent" to use is the
judgment call reserved for `llm-council` in Task 5.** Do not just pick matched-σ because it is the
one already tabulated here.

**Also healthy:** `power_law.fit_power_law_exponent` exists, is tested, and correctly raises on
non-positive input — so the caller must exclude the zero-distortion condition. Its documented
fallback (low r² ⇒ model power-law as an injected transform instead) is intact and is the trigger
Task 2 must honour.

### 2.6 The schedule objection, and why it does not hold

An `llm-council` advisor argued P2's supplementary grid is "a new campaign, not a patch," and should
be skipped for schedule reasons. **The measured runtime contradicts this**, and it is worth stating
plainly so the argument is not re-litigated mid-week:

- Full preregistered campaign: 125,650 fits in **14.32 s**.
- Task 6's supplementary N×noise grid: 7 N-values × 10 noise-values = 70 conditions × 7 methods ×
  50 seeds = **24,500 fits ≈ 2.8 s**.
- Task 4's supplementary hysteresis grid: 8 magnitudes × 7 methods × 50 seeds = **2,800 fits ≈ 0.3 s**.

The cost of both supplementary experiments combined is about **three seconds of compute**. The real
cost is the analysis and the writing, not the run. Schedule pressure is not a valid reason to skip
either — but it *is* a valid reason to keep their scope exactly as specified and not grow them.

### 2.7 Three risks peer review caught that no single advisor named

These shaped Tasks 1, 3, and 11. They are not optional extras.

1. **The defect class has no CI guard.** All four defects were found by executing code once. The
   test suite could not have found any of them — it tests each transform against its own formula,
   never the config→run path. This is the *same* structural criticism the Weeks 1-2 council review
   already made, and the project's answer then (`tests/test_docs_consistency.py`) covered only the
   stale-numbers case. **Task 1 builds the general guard.**
2. **A self-dated deviation in a repo the author controls proves nothing.** The deviation log needs
   an independent timestamp at the moment it is written, before any supplementary data is seen —
   git commit *and* an OSF amendment on the registration, not just a date typed into a markdown
   file. **Task 1 step 6.**
3. **Fixing P3 may invalidate part of the already-published RQ1 draft.** `RQ1_RQ2_ANALYSIS.md` was
   written with no cost data at all. Once cost is real, RQ1's comparative claims may need revision —
   and Köning, the only iterative method, is the most likely to move. **Task 3 must check this
   explicitly rather than assume the draft survives.**

---

## Task 1 (Day 29): The gate — audit record, deviations, CI guards, release scaffolding

**Nothing else in Weeks 5-6 may begin until this task is committed and pushed.** The entire point is
that the paper trail exists *before* any supplementary data is seen. This is the one ordering
constraint in the plan that is not negotiable.

### 1.1 Write `docs/WEEK5_PREFLIGHT_AUDIT.md`

- [ ] Document all four findings with: the claim, the executable reproduction command, the measured
      numbers, the root cause, why it was missed, and the consequence for the affected RQ.
- [ ] For each, state explicitly which of §0.6's routes was chosen and why: **(a)** limitation +
      dated deviation, **(b)** labeled supplementary experiment, **(c)** amend the grid and re-run.
      The chosen routes, per the council verdict:
      - **P1 → (a) + (b).** Deviation reclassifying the preregistered axis as static radial
        inflation; separate supplementary bidirectional experiment. **Never (c)** — retroactively
        editing the grid so it matches the preregistration text is the single move that defeats the
        purpose of preregistering.
      - **P2 → (a) + (b).** RQ6 declared unanswered as written; supplementary N×noise grid.
        Legitimate as (b) specifically because it *adds* an axis rather than editing existing
        conditions.
      - **P3 → not a deviation.** Completing preregistered instrumentation.
      - **P4 → (a) only.** Documentation deviation; no re-run.
- [ ] Include the honest framing, per the council's unanimous position: for P1 and P2 the RQ is
      **declared unanswered and the defect reported as the finding** — not quietly reworded into a
      narrower question that the existing data happens to answer.

### 1.2 Record the deviations in the documents that made the claims

Each must be dated 2026-07-29, follow D1-D4's established format, and be appended (never edited in
place).

- [ ] **`docs/PREREGISTRATION.md` → D5 (P1):** the `hysteresis_magnitude` axis, as executed,
      measures direction-*independent* radial inflation, because every campaign waveform is
      monotonic. RQ3's hysteresis half is unanswered by the preregistered campaign. Include the
      100%/0% direction measurement and the bit-identical result.
- [ ] **`docs/PREREGISTRATION.md` → D6 (P2):** RQ6 is not answerable from the preregistered grid.
      Include the flat-curve table from §2.2 and the note that the axis's own stated justification
      (the 7× swing) was a noise-averaging effect measured under conditions the grid does not
      contain.
- [ ] **`docs/PREREGISTRATION.md` → D7 (P4):** RQ5's scope is narrowed to the sub-fringe regime;
      record that `experimental_design.md` had already silently re-described the range top as
      "full-circle ramp measurement," and that the narrowing is being recorded now rather than left
      implicit.
- [ ] **`docs/WEEK3_METHOD_CONTRACT.md` (P3):** note that `runtime_s` was contracted but never
      populated by the Day 24 runner, and that Task 3 completes it. Record this as a **defect
      report, not a deviation** — and say why (nothing about ranges, metrics, or protocol changed).
- [ ] **`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` → D2:** its Category 3 section predicts about
      "hysteresis." Given P1, amend to state that the preregistered campaign tests radial inflation,
      and that the Category 3 hysteresis prediction is testable only by Task 4's supplementary run.

### 1.3 Build the CI guard for this defect class — `tests/test_campaign_integrity.py`

This is the permanent fix and the most valuable deliverable of Task 1. Every test below must fail
loudly on the *pre-fix* state, so write each one, watch it fail, then fix. Do not write a test that
passes immediately.

- [ ] **`test_every_swept_axis_meets_its_committed_response_floor`** — for each OFAT axis, assert the
      **maximum across methods** of (max/min mean displacement RMSE) meets a **per-axis floor from a
      committed table**, not a single global threshold.

      **Read this before writing the test — a single global threshold does not work, and the reason
      is subtle.** Measured dynamic range (max across methods) for every OFAT axis:

      | axis | max across methods | note |
      |---|---|---|
      | `arc_fraction` | 4299.79× | |
      | `noise_std` | 310.02× | |
      | `amplitude_ratio` | 179.71× | |
      | `photon_scale` | 36.57× | |
      | `hysteresis_magnitude` | 33.88× | |
      | `quadrature_error_rad` | 9.53× | |
      | **`dc_offset`** | **2.81×** | **entirely from `raw_atan2`; every correcting method is 1.00–1.11×** |
      | **`samples_per_fit`** | **1.10×** | **the P2 defect** |

      A global threshold would have to sit between 1.10× and 2.81×, and the only thing holding
      `dc_offset` above the line is the deliberately-naive uncorrected baseline. Worse, the
      correcting methods' flatness on `dc_offset` is **not a defect — it is the Category 1
      tautological prediction confirmed** (`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`): a conic
      fitter is *supposed* to absorb a DC offset perfectly. So "does the fitted error respond to
      this axis" genuinely cannot distinguish "the axis is broken" from "the methods are excellent
      at this axis," and a global constant here would be exactly the round-number-chosen-by-taste
      this project forbids.

      Therefore: commit the per-axis floors as a documented table with the measurement above at the
      constant, and state in a comment that `dc_offset`'s floor is low *because* the correcting
      methods are structurally expected to be flat there. Any future config change that flattens an
      axis below its committed floor then fails loudly and specifically.

      **This test is a regression guard, not P2's real guard** — see the RQ→grid test below, which is
      the one that would actually have caught P2 before the campaign ran.
- [ ] **`test_hysteresis_axis_actually_reverses_direction`** — for every condition where
      `hysteresis_magnitude > 0`, assert the generated waveform contains **both** `+1` and `-1`
      direction samples. This is the direct guard against P1 and will **fail on the current
      preregistered config**, which is correct: mark it `xfail` with a reason pointing at D5, and
      have it pass for Task 4's supplementary config. An `xfail` that documents a known, recorded
      defect is honest; deleting the test is not.
- [ ] **`test_every_preregistered_metric_is_populated`** — load the campaign summary and assert that
      every metric named in `PREREGISTRATION.md`'s Metrics section has a non-null rate above a
      documented floor. Direct guard against P3. Must fail now on `runtime_s_mean`.
- [ ] **`test_every_research_question_has_a_grid_that_can_answer_it`** — **this is the real guard
      against P2, and the most important test in this file.** A declarative mapping from each RQ to
      the axes *and interaction grids* it requires, asserting the config contains them. RQ6 requires
      an `N × noise` interaction; assert it. This is the only check here that would have caught P2
      at configuration time, before the campaign ever ran — because P2 is not "the axis produces no
      response," it is "the axis was swept at a baseline where it has no leverage on the question."
      An N sweep at σ=0 *does* change the signal; what it cannot do is answer a question about noise
      averaging. Only an RQ→grid mapping catches that. Expect it to fail on the main config for
      RQ6 — `xfail` against D6, pass against the supplementary config.
- [ ] **`test_preregistered_and_supplementary_results_are_not_blended`** — assert no module reads
      `results/raw/` and `results/supplementary/` into a single frame without a `provenance` column.

### 1.4 Week 6 release scaffolding, done now rather than on Day 40

Pulled forward deliberately: an `llm-council` advisor's strongest practical point was that these are
ten-minute template fills that become a Day 41 fire drill if deferred.

- [ ] `LICENSE` — MIT (confirm with Nishi; it is the one choice here that is theirs, not a default).
      **Blocks PyPI.**
- [ ] `CITATION.cff` — leave the DOI field as an explicit `TODO(Day 41)` placeholder; it cannot be
      filled before the DOI exists.
- [ ] `CHANGELOG.md` — Keep a Changelog format, `0.1.0` unreleased section summarising Weeks 1-6.
- [ ] Add all three to the package data / `MANIFEST.in` as appropriate and confirm they appear in a
      built sdist.

### 1.5 Verification and commit

- [ ] `ruff check . && ruff format --check . && mypy` all clean.
- [ ] Full suite passes, with the new `xfail`s reported as expected failures (not errors).
- [ ] Commit as **one commit containing documentation and guards only — no experiment code and no
      supplementary data.** Message must state that no supplementary experiment has been run yet.
- [ ] Push; verify CI green on **all 8 matrix jobs** — `.github/workflows/ci.yml` runs two separate
      matrices: lint/type/test on 2 Python versions (ubuntu only), plus reproducibility on
      3 OS × 2 Python. A green tick on one matrix is not a green CI run.
- [ ] **Escalate to Nishi:** the OSF registration needs an amendment pointing at D5-D7. Only Nishi
      can do this (account access). Per §2.7 risk 2, the deviations are not externally timestamped
      until this happens. **Flag it as blocking the Day 41 DOI, not as a nice-to-have.**
- [ ] `docs/journal/day29.md`.

---

## Task 2 (Day 30): RQ3 part 1 — power-law characterisation on real campaign data

This is the Day 30 anchor named back on Day 13: "the real data comes in on Day 30." Day 13 built and
validated `power_law.py` against synthetic data with a known exponent, deliberately not answering
the question prematurely. This task answers it.

### 2.1 What to characterise

Per `PREREGISTRATION.md`'s v1 revision item 3 and Day 13's confirmed decision with Nishi, power-law
is **characterised from existing sweep data via a log-log fit — not injected as a new mechanism.**

- [ ] For each method and each OFAT axis with a monotonic distortion magnitude
      (`amplitude_ratio`, `quadrature_error_rad`, `dc_offset`, `hysteresis_magnitude`), fit
      `error = c · magnitude^n` via `power_law.fit_power_law_exponent`.
- [ ] **Exclude the zero-distortion condition explicitly before calling** — the function raises on
      non-positive input by design, and that raise is the contract, not an inconvenience to work
      around. For `amplitude_ratio` the "magnitude" is `ratio - 1.0`, not the ratio itself; state
      that choice in the analysis and justify it (a ratio of 1.0 is zero distortion).
- [ ] Report exponent, coefficient, **and r²** for every fit. Never the exponent alone.

### 2.2 The honesty gate that is the actual point of this task

Day 13 built a specific safeguard: a genuinely flat relationship must be reported as low-r²,
near-zero exponent, **not** as a falsely confident "yes, power of 3."

- [ ] Pre-commit an r² floor **before looking at the fitted values**, and write it into the analysis
      script as a named constant with its justification. Below the floor, the reported result is
      "no clean power-law relationship in this data," and `power_law.py`'s documented fallback
      (model power-law as an injected transform instead) is the trigger — escalate to Nishi rather
      than silently choosing.
- [ ] Lehmann et al. 2025 report an exponent near 3 for residual-noise scaling. **Do not treat 3 as
      a target.** Recovering ~3 is a finding; not recovering it is equally a finding. Per Day 1's
      correction, Lehmann's exponent is an *observed residual-noise scaling*, not a distinct
      injectable mechanism — so a mismatch is expected as much as a match, and the analysis must say
      so before reporting the number.

### 2.3 Output

- [ ] `scripts/rq3_power_law_analysis.py` → `results/rq3_power_law.csv`.
- [ ] Tests: at minimum, that the zero-condition exclusion happens, and that a synthetic flat input
      routes to the low-r² branch.
- [ ] Commit, push, CI green, `docs/journal/day30.md`.

---

## Task 3 (Day 31): P3 — wire up cost, and check whether it changes RQ1

### 3.1 The fix

**The obvious one-line fix does not type-check. Read this before writing code.** The signatures are:

```python
# methods/base.py:154
def timed_fit(fit_fn: PhaseRecoveryMethod, *args: FloatArray, **kwargs: object) -> FitResult
# methods/__init__.py:44
def fit_by_name(method_name: str, intensity_i: FloatArray, intensity_q: FloatArray,
                *, mean_intensity: float) -> FitResult
```

So `timed_fit(fit_by_name, method_name, signal.i, signal.q, mean_intensity=...)` passes a `str`
into `*args: FloatArray` — **`mypy --strict` rejects it**, and CI enforces `mypy --strict`. Widening
`timed_fit`'s `*args` to `object` would silence it at the cost of weakening a shared contract that
currently documents exactly what a fit function receives.

- [ ] **Preferred fix:** add `timed_fit_by_name(method_name, i, q, *, mean_intensity)` to
      `methods/__init__.py`, implemented in terms of the existing `timed_fit` and `fit_by_name`, and
      call *that* from `runner.py`. This keeps timing measured in exactly one place (the invariant
      `FitResult.runtime_s`'s docstring depends on), keeps the strict signature intact, and puts the
      name→callable dispatch in the one module that already owns it — the same consolidation
      Week 3's R5 finding required when `raw_atan2`'s kwarg had been copy-pasted to three call
      sites. Do **not** create a second dispatch path in `runner.py`.
- [ ] If you choose differently, record why — this is a real design choice, not a mechanical fix.
- [ ] Add a regression test asserting `runtime_s` is non-null for every row of a small run, and that
      it is strictly positive (a zero would mean the clock was never read).

### 3.2 The measurement design — serial, not parallel

The campaign runs under `ProcessPoolExecutor`. Per-fit wall-clock measured inside contending workers
measures scheduler contention as much as algorithm cost, and the preregistration says "same
hardware," which a contended pool does not honour in any stable way.

- [ ] Run a **serial, single-worker** timing pass with BLAS pinned to 1, over a pre-specified subset
      of conditions.
- [ ] **Pre-commit the subset selection before looking at any timing result**, and — per the council
      Contrarian's specific objection — **before consulting which methods already win on accuracy.**
      Otherwise the subset is a second free parameter available for cherry-picking. Recommended
      subset, chosen on structural grounds only: the baseline condition plus the extreme point of
      each OFAT axis, which covers every method's easy and hard regimes without reference to any
      result.
- [ ] Report mean **and std** across seeds, per the preregistration's exact wording, plus the
      secondary iteration count for Köning (the only iterative method).
- [ ] Record in `WEEK3_METHOD_CONTRACT.md` that cost comes from a serial pass rather than the
      parallel campaign, **with the reason** — this is a genuine methodological choice a reader
      could reasonably question, so it must be visible, not buried.

### 3.3 The check no advisor asked for (§2.7 risk 3)

- [ ] Re-read `docs/RQ1_RQ2_ANALYSIS.md` against the new cost numbers and answer explicitly, in
      writing: **does any claim in it change?** RQ1 promises a comparison on cost; the draft
      currently makes none. At minimum the document needs a cost section. If cost materially
      reorders any practical recommendation — Köning is the likeliest, being the only iterative
      method — that is a revision to a document already presented to Nishi as a draft, and must be
      flagged to Nishi rather than silently patched.
- [ ] Do **not** rewrite the RQ1 draft's existing conclusions unilaterally. Add the cost section,
      flag any tension, escalate.
- [ ] Commit, push, CI green, `docs/journal/day31.md`.

---

## Task 4 (Day 32): RQ3 part 2 — the supplementary bidirectional-waveform experiment

**§0.6 applies in full. Write and push the protocol before any code.** Invoke
`superpowers:brainstorming` first — this is the one genuinely new forward-model component in Weeks
5-6 and the plan does not settle its design.

### 4.1 Protocol first (commit with no code)

- [ ] Write into `docs/SUPPLEMENTARY_PROTOCOLS.md`: grid, waveform, seed count, metrics reported,
      and the pre-specified criterion. Suggested criterion, to be confirmed or replaced during
      brainstorming: *direction-dependence is demonstrated if, at matched `hysteresis_magnitude`,
      N, and phase span, the bidirectional waveform produces a displacement RMSE that differs from
      the monotonic waveform by more than the seed-to-seed spread.* State what would falsify it.
- [ ] Commit and push. Message must say the experiment has not been run.

### 4.2 `src/hoqi_bench/waveforms.py`

- [ ] `build_bidirectional_ramp(arc_fraction, n_points)` — a triangle wave: the first `n_points//2`
      samples ramp phase `0 → arc_fraction·2π`, the remainder ramp back down.
- [ ] **The design constraint that makes the comparison valid:** it must match `build_arc_ramp` on
      **total sample count and total phase span**, differing *only* in path. Otherwise a difference
      in result is confounded with a difference in sampling density or coverage, and the experiment
      answers nothing. Assert both properties in tests.
- [ ] Each phase value is visited twice — once ascending (radius `R+h`), once descending (`R−h`) —
      which is precisely the hysteresis loop. Verify directly that `sign(gradient(x_true))` contains
      both `+1` and `−1`, and that the `-1` fraction is ≈0.5.
- [ ] Handle the odd-`n_points` and turning-point cases explicitly. `np.gradient` at the apex
      returns ~0, so `np.sign` gives `0` there — decide and document what a zero-direction sample
      means (recommendation: it is a real, physical turning point; leave it unperturbed, matching
      `hysteresis`'s existing zero-radius guard convention, and test that it is a single isolated
      sample rather than a region).

### 4.3 Run and analyse

- [ ] `configs/supplementary_hysteresis.toml` — same 8 `hysteresis_magnitude` values, same baseline,
      bidirectional waveform. 2,800 fits, ≈0.3 s.
- [ ] Write to `results/supplementary/hysteresis_bidirectional/`.
- [ ] Compare against the preregistered monotonic result at matched magnitude, and report **both**
      under their correct names: preregistered = radial inflation; supplementary = direction-
      dependent hysteresis.
- [ ] Re-check the §2.1 floor-masking trap on the new data before making any claim about Kasa,
      Taubin, or `raw_atan2` robustness.
- [ ] Flip `test_hysteresis_axis_actually_reverses_direction` from `xfail` to passing against the
      supplementary config.
- [ ] Commit, push, CI green, `docs/journal/day32.md`.

---

## Task 5 (Day 33): RQ4 — Poisson vs Gaussian, and whether the rankings change

### 5.1 Decide what "equivalent noise" means — llm-council first

- [ ] Invoke `llm-council` per §0.4 item 1, **before implementing**. The measured mapping in §2.5 is
      an input to that decision, not the decision itself.
- [ ] Record the verdict and the reasoning in `docs/PREREGISTRATION.md` as a dated operational
      clarification (matching D3's precedent, where an ambiguous preregistered definition was
      resolved by council and recorded — not as a change to the research question).

### 5.2 `src/hoqi_bench/noise_equivalence.py`

- [ ] Implement the chosen mapping. Whatever it is, it must be **measured against realized residuals,
      not assumed from the closed form** — §2.5 shows the closed form is ~5% off, and that gap is
      real (intensity varies about its mean), so it must be reported, not rounded away.
- [ ] Test against the §2.5 table as an independent oracle (reconstruct the reference in the test
      file; do not import the module under test to build its own expectation).

### 5.3 Analyse

- [ ] At matched effective noise, compare method **rankings** (not just errors) between the
      `photon_scale` and `noise_std` axes. RQ4's question is specifically whether the ordering
      changes.
- [ ] Use `aggregate.is_rankable` — a condition where too many methods are unusable is not rankable,
      and reporting an ordering there would repeat exactly the R1 error this project already
      documented once.
- [ ] Report failure rate, gross-error rate, and unusable rate alongside every error number, per R1.
- [ ] **Execution-audit RQ4's own path while you are here**, per §2.7 risk 1 and the council's
      convergent warning: RQ4 is the one remaining RQ whose data path has never been checked by
      execution. Confirm the Poisson conditions actually draw Poisson noise (variance ∝ intensity,
      **measured**, not read off the docstring).
- [ ] **Do NOT go looking for a runtime mutual-exclusion branch — there isn't one, and §2.5 explains
      why that is correct.** Both noise functions are applied unconditionally at
      `simulate.py:178-179`. Finding that is the *expected* state, not a defect, and must not
      trigger §0.2's defect-resolution protocol. What you should verify instead is the thing that
      actually matters: that `gaussian_noise(std=0.0)` is an exact identity, and that the residual
      Poisson noise at `photon_scale=1e7` is negligible at the scale of the smallest swept Gaussian
      level — both by measurement.
- [ ] `scripts/rq4_analysis.py` → `results/rq4_*.csv`. Commit, push, CI green, `docs/journal/day33.md`.

---

## Task 6 (Day 34): RQ6 — the supplementary N × noise design chart

**§0.6 applies in full. Protocol committed and pushed before any code.**

- [ ] Protocol into `docs/SUPPLEMENTARY_PROTOCOLS.md`: the full 7 × 10 grid (`samples_per_fit` ×
      `noise_std`, both at their existing preregistered values — **do not invent new grid points**,
      which would be an unnecessary extra degree of freedom), 50 paired seeds, 24,500 fits, ≈2.8 s.
      State the target-accuracy definition **before** seeing results: use
      `reference_scale.PREREGISTERED_TOLERANCE_M`, the same fixed physical denominator D3 already
      established for breakdown thresholds, rather than inventing a new one here.
- [ ] Commit and push the protocol alone.
- [ ] `configs/supplementary_n_x_noise.toml`; write to `results/supplementary/n_x_noise/`.
- [ ] Produce the chart: for each method and each noise level, the smallest N reaching tolerance.
      Reuse `statistics.breakdown_threshold`'s three-outcome `BreakdownThreshold` type — the
      `broken_at_start` / `no_breakdown_in_range` distinction matters exactly as much here as it did
      for RQ2, and inventing a second convention would be a real inconsistency.

- [ ] **CRITICAL — you must pass N in DESCENDING order, and every existing precedent in this
      codebase will lead you to do the opposite.** `statistics.breakdown_threshold` requires
      `parameter_values`/`mean_errors` in **scan order, easiest-to-hardest**, and its docstring
      states it "does not sort or validate that ordering, per the design decision recorded above
      that scan direction is an explicit caller contract." The only existing call site,
      `scripts/rq1_rq2_analysis.py`'s `build_rq2_table`, passes `amplitude_ratio` and `arc_fraction`
      in **ascending** config order — correct for those axes, because larger `amplitude_ratio` and
      (in its own scan sense) the arc sweep get *harder*.

      For `samples_per_fit` the relation is **inverted**: larger N is *easier*. So easiest-to-hardest
      is `[1000, 500, 200, 100, 60, 40, 20]`. Passing the natural ascending order would silently
      run the crossing search backwards and produce spurious `no_breakdown_in_range` results or a
      wrongly-located crossing — with no exception raised, because the function deliberately does
      not validate.

      **Measured demonstration** (run 2026-07-28, `tolerance = 1.0`, synthetic error falling as N
      rises: `N = [1000, 500, 200, 100, 60, 40, 20]`, `err = [0.2, 0.3, 0.5, 0.8, 1.2, 1.6, 2.0]`):

      | call | result |
      |---|---|
      | descending (easiest→hardest, **correct**) | `BreakdownThreshold(value=80.0, status='found')` |
      | ascending (natural order, **wrong**) | `BreakdownThreshold(value=None, status='broken_at_start')` |

      Note what the wrong call produces: not an error, not a NaN, but a clean
      `broken_at_start` — a result that reads as a legitimate scientific finding. That is precisely
      the failure shape this project has been burned by three times (D1's 1/N artifact, R1's
      inverted reliability ranking, P2 itself).

      Write a test that pins the scan direction explicitly, using the table above as the known-good
      answer: assert the descending call returns `80.0`/`found` and the ascending call does not. Note also from §2.2 that the N-response is not strictly monotone
      for every method (heydemann measured 0.94×, i.e. slightly *worse* at N=1000 than N=20) — D3's
      "first crossing in scan order wins; later re-crossings are ignored, never averaged" rule
      governs that case and must not be re-litigated here.
- [ ] **Report this as supplementary throughout.** It answers a preregistered question with
      post-hoc data; the design chart is a genuine deliverable, but it is not a preregistered result
      and must never appear in a table alongside preregistered ones without the `provenance` column.
- [ ] Flip `test_every_research_question_has_a_grid_that_can_answer_it`'s RQ6 case to pass against
      the supplementary config.
- [ ] Commit, push, CI green, `docs/journal/day34.md`.

---

## Task 7 (Day 35, part 1): RQ5 — the sub-fringe regime, honestly scoped

- [ ] Analyse performance vs `arc_fraction` across `[0.02, 1.0]`, plus the `arc_x_noise` interaction
      grid.
- [ ] **State the scope limitation in the RQ5 section's own opening sentence**, not in a footnote:
      this answers the sub-fringe half of RQ5 only; the many-fringe half was never in the grid
      (D7). Do not present a sub-fringe result as if it answered the whole question.
- [ ] Do **not** extend the grid past `arc_fraction = 1.0`. Adding multi-fringe conditions now is
      post-hoc scope growth on the axis whose sub-fringe result is already the campaign's headline
      finding (RQ1b) — the highest forking-paths exposure in the project. If Nishi wants it, it is a
      future-work item with its own preregistration, not a Week 5 patch.
- [ ] Cross-check against RQ1b's existing `arc_fraction = 0.02` result and confirm the numbers still
      reproduce. Per Week 4's constraint: when citing a prior finding, **re-run it** — Day 21 already
      caught one Week-1 finding that no longer reproduced.

## Task 8 (Day 35, part 2): The RQ3-RQ6 analysis document

- [ ] Write `docs/RQ3_RQ6_ANALYSIS.md`, marked **DRAFT INTERPRETATION** exactly as
      `RQ1_RQ2_ANALYSIS.md` is — Nishi revises, does not rubber-stamp.
- [ ] Binding framing rules, carried from Day 28 and extended:
      1. Category 1 (tautological) results are captioned as construction checks, never rankings.
      2. Every error number carries its failure, gross-error, and unusable rates.
      3. Cyclic-error amplitudes only where `well_conditioned AND NOT failed` (D2's caveat).
      4. Significance reported alongside, never instead of, practical magnitude.
      5. **NEW:** every preregistered-vs-supplementary result is labeled as such, in the table, not
         only in surrounding prose.
      6. **NEW:** RQ3's hysteresis half and RQ6 are reported as **unanswered by the preregistered
         campaign**, with the supplementary results presented separately and clearly subordinate.
- [ ] Invoke `llm-council` per §0.4 item 2 **before** presenting anything to Nishi, hunting
      specifically for overclaiming and for defects spun as findings. Revise in place against the
      review and record what changed, as Day 28 did.
- [ ] Commit, push, CI green, `docs/journal/day35.md`.

## Task 8b (Day 35, part 3): Clean-clone reproduction check

The Day 35 anchor named back on Day 7. This is the check the whole CI investment was for.

- [ ] `git clone` the pushed repo into a **fresh temp directory** (not a copy of the working tree),
      create a clean venv, `pip install -e ".[dev]"`, run the full suite, and re-run the smoke
      campaign.
- [ ] Verify results match to the documented tolerance (`rtol=1e-9`, `atol=1e-15` per D4 — **not**
      byte-exact; D4 established that no platform holds byte-exactness even against itself).
- [ ] Anything that fails here is a real defect in the reproducibility claim that is this project's
      stated core contribution. Apply §0.2 and do not proceed to Week 6.

---

# Week 6 (Days 36-42) — audit, write-up, release

## Task 9 (Day 36): The documentation-drift audit

Motivated by the council Outsider's strongest point: P4 proves a preregistered term already drifted
silently in the prose and was caught only by an audit. That is a **search problem**, and the search
has not been done.

- [ ] Use `superpowers:dispatching-parallel-agents`. For each document in `docs/` and `notes/`,
      dispatch an agent whose sole job is to verify every quantitative and definitional claim against
      the actual code and config, reporting only mismatches.
- [ ] Specifically check the class P4 belongs to: **prose that re-describes a preregistered
      parameter in different words.** Every such re-description is a candidate drift.
- [ ] Verify every number in every doc programmatically where possible — extend
      `tests/test_docs_consistency.py`, which already does this for `total_runs`/`n_seeds`, to cover
      whatever this audit finds. A one-time manual fix without a guard just resets the clock.
- [ ] Record findings in `docs/WEEK6_DOC_AUDIT.md`; fix or record each per §0.2.

## Task 10 (Day 37): README, API docs, and usage examples

- [ ] Rewrite `README.md` for a first-time external reader: what the benchmark is, what it found,
      what it explicitly does *not* answer (RQ3-hysteresis, RQ6, RQ5-many-fringe), install, and a
      runnable quickstart.
- [ ] **The "does not answer" section is not optional and does not go at the bottom.** A benchmark
      whose stated contribution is reproducibility infrastructure and whose preregistration caught
      four of its own defects before release is *stronger* for saying so plainly — but only if it
      says so where a reader will actually see it.
- [ ] Verify every command in the README by executing it in the clean clone from Task 8b.

## Task 11 (Day 38): Abstract and contribution claim

The Day 38 anchor from `notes/contribution_claim.md`.

- [ ] Write the abstract. Per that note, the honest contribution — reproducibility infrastructure
      plus the extension to Lehmann's newer nonlinearity classes — belongs *in the abstract itself*,
      not buried later.
- [ ] Re-check the claim against what Weeks 5-6 actually established. The Lehmann-extension half of
      the contribution claim is now **weaker than written**: P1 means the preregistered campaign did
      not test direction-dependent hysteresis at all, and only Task 4's supplementary run speaks to
      it. Update the claim to match reality rather than restating the Week 1 version.
- [ ] Do not describe the four defects as a headline achievement. Per the peer-review consensus
      against the Expansionist's framing: documenting them accurately is the deliverable; marketing
      them as a triumph is its own form of overclaiming.

## Task 12 (Day 39): Packaging dry-run

- [ ] `python -m build`; inspect both sdist and wheel contents — confirm `LICENSE`, `CITATION.cff`,
      and `CHANGELOG.md` are present.
- [ ] `twine check dist/*`.
- [ ] Upload to **TestPyPI** and install from it into a fresh venv; import the package and run a
      minimal end-to-end example.
- [ ] Confirm the version is `0.1.0` and that pinned exact dependencies (Day 26) resolve on both
      3.10 and 3.11.

## Task 13 (Day 40): PyPI release — **Nishi required**

- [ ] Nishi supplies PyPI credentials / API token. Claude cannot and must not do this.
- [ ] Upload; verify install from real PyPI in a fresh venv.
- [ ] Tag the release in git and push the tag.

## Task 14 (Day 41): Zenodo DOI — **Nishi required, and gated**

- [ ] **Gate check before anything else, per §2.7 and the council's sharpest single point: a Zenodo
      DOI is immutable.** Minting it converts any remaining defect from a fixable draft bug into a
      permanent citable one. Confirm ALL of: Task 1 committed and OSF-amended; Task 9's doc audit
      clean; Task 8b's clean-clone reproduction passing; Task 12's TestPyPI install verified.
- [ ] If any gate item is open, **stop and escalate to Nishi** rather than proceeding. Slipping the
      DOI by a day costs nothing; a wrong DOI is permanent.
- [ ] Nishi performs the Zenodo upload / GitHub-release integration.
- [ ] Fill the `TODO(Day 41)` DOI placeholder in `CITATION.cff` and the README; commit and push.

## Task 15 (Day 42): Retrospective and close

- [ ] `docs/journal/day42.md` — the honest project retrospective. What the benchmark answers, what
      it does not, what the six-week process caught and what it missed until an audit on Day 29.
- [ ] Update `docs/PREREGISTRATION.md` with a final status: which RQs were answered, which were
      declared unanswered, and where each result lives.
- [ ] Verify every claim in the vault page `02-projects/hoqi-bench.md` still matches the repo.

---

## Decision points reserved for Nishi

Do not resolve these; escalate with a recommendation and stop.

1. **LICENSE choice** (Task 1.4) — MIT is the default recommendation, but it is Nishi's call.
2. **The OSF amendment** (Task 1.5) — account access; blocks the Day 41 DOI.
3. **RQ4's noise-equivalence definition** (Task 5.1) — council advises, Nishi decides.
4. **Any revision to the already-presented RQ1/RQ2 draft** triggered by cost data (Task 3.3).
5. **Whether to pursue multi-fringe RQ5 as future work** with its own preregistration (Task 7).
6. **Köning's `amplitude_ratio = 1.495` breakdown** — carried over unresolved from Day 28's "Left
   for Nishi." This plan does not investigate it; if Nishi wants it, it is a supplementary
   experiment under §0.6, not an inline fix.
7. **The `power_law` fallback trigger** (Task 2.2) — if r² falls below the pre-committed floor,
   whether to switch to an injected-transform model is a scope decision, not Claude's call.

## Self-review — known weaknesses of this plan

Stated plainly, because a plan that claims to be complete is making exactly the error §2 documents.

- **Task 4's waveform design is the weakest link.** It is the only new forward-model component, and
  a subtly wrong triangle wave (turning-point handling, odd `n_points`, phase-span mismatch) would
  produce a confident, wrong answer about direction-dependence — the same shape as P1 itself. This
  is why it is the one task that mandates `brainstorming` and explicit matched-span assertions.
- **The `test_every_swept_axis_produces_a_response` threshold is not yet measured.** The plan tells
  you to calibrate it rather than giving a number, because the honest value depends on a probe not
  yet run. Do not let that become a round number chosen by taste.
- **This audit found four defects by executing code once.** It has not been shown that there is no
  fifth. Task 5 execution-audits RQ4, and Task 9 audits the docs, but the packaging path is only
  exercised on Day 39, and no adversarial pass has been run over `statistics.py` or `aggregate.py`.
  Treat a surprise there as expected, not as a crisis.
- **Days 36-42 are back-loaded with irreversible steps** (PyPI, DOI) that depend on Nishi's
  availability. The Day 41 gate exists to make slipping cheap. Use it.
