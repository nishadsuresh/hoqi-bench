# Week 4 Execution Plan — Days 23-28

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking. Read §0 in full before touching any code.

**Goal:** Take hoqi-bench from "seven validated methods and a metrics layer" to "the full
125,650-run campaign has been executed reproducibly and RQ1/RQ2 are answered," without
introducing a single result that is an artifact rather than a finding.

**Architecture:** Three new `src/` modules (`harmonics.py`, `runner.py`, `statistics.py`), one
new `scripts/` entry point, and a CI matrix. Everything reads the grid from
`configs/main_campaign.toml` and writes one Parquet file per condition into `results/raw/`,
which the statistics and analysis layers then consume. Nothing hardcodes the grid; nothing
re-derives a seed; nothing computes a metric that `metrics.py` already provides.

**Tech Stack:** Python 3.10/3.11, numpy, scipy, pandas + pyarrow (Parquet), pytest, ruff,
mypy --strict, GitHub Actions.

---

## Global Constraints

Every task's requirements implicitly include this section. These are copied verbatim from
`docs/PREREGISTRATION.md`, `docs/WEEK3_METHOD_CONTRACT.md`, and `docs/WEEK3-4_PLAN.md`.

- **Python interpreter is `/home/nishadrobotics/venvs/hoqi-bench/bin/python`.** Bare `python`
  does not exist on this machine and bare `python3` is a system 3.10 without the package
  installed. Every command in this plan uses the venv path explicitly. If you type `python`
  and get "command not found," that is this constraint, not a broken environment.
- **BLAS threading must be pinned to 1** (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
  `MKL_NUM_THREADS`) in every process that imports numpy, *before* the first numpy import.
  `conftest.py` does this for pytest. Day 24's runner must do it for each worker. This is not
  a determinism nicety — running the full campaign without it produced a hard crash
  (`SystemError: attempting to create PyCFunction with class but no METH_METHOD flag`).
- **Never re-derive a seed.** `hoqi_bench.seeds.derive_seed(seed_index, condition_name, stream)`
  is the only seeding path. Its signature structurally cannot accept a method name, which is
  what enforces the preregistered paired-seeds guarantee. Do not add a second path.
- **Never re-derive the phase wrapping.** Any error computed on recovered *phase* goes through
  `hoqi_bench.metrics.wrapped_phase_error`. A naive difference overstates errors near ±π by
  ~300x.
- **Never silently patch a method's known weakness.** Fitzgibbon's fragility, Kasa's unguarded
  `lstsq`, and Heydemann's radius guard are all scientifically load-bearing. If a method looks
  broken, the fix goes in the harness or the docs, never in the method.
- **Preregistered statistics only.** Bootstrap percentile CIs, interpolated breakdown
  thresholds, and Bonferroni over 21 pairwise comparisons *per condition*. If something looks
  missing, flag it for Nishi — do not add it.
- **`tolerance = 0.01`** and the grid come from `configs/main_campaign.toml`, never hardcoded.
- **Every threshold is measured before it is written down.** This project has no round-number
  constants chosen by taste. See `heydemann.py`'s `_RADIUS_CONSISTENCY_THRESHOLD` and
  `aggregate.py`'s `MAX_UNUSABLE_RATE_FOR_RANKING` for the pattern: probe, tabulate, pick a
  value with margin on both sides, document the data at the constant.
- **Documentation standard** (`docs/DOCUMENTATION_STANDARD.md`) applies to every new module:
  module docstring answering what/why/pipeline-position, numbered section banners, purpose
  comments not syntax comments, equation provenance, design-decision notes, failure-mode notes,
  and a `docs/journal/dayNN.md` entry.

---

## 0. How to use this document

### 0.1 Who this is written for

This plan assumes an executor who is a competent Python developer but who has **not** read this
codebase, has **not** read the papers, and was **not** present for Weeks 1-3. Every non-obvious
decision is therefore explained where it is made rather than referenced. Where I already ran a
probe and know the answer, the numbers are in the plan — you should not have to rediscover
them. Where I deliberately left something open, it says so explicitly and tells you how to
close it.

The specific failure mode this plan is written against: a capable model reads "implement cyclic
error harmonics," writes a clean FFT-based implementation, all tests pass, and the campaign
silently produces garbage on 99 of its 359 conditions. §Task 1 exists in its current form
because I ran that exact experiment and watched it happen.

### 0.2 The defect-resolution rule (standing instruction from Nishi, 2026-07-28)

> "If something is marked as incorrect or could be marked as a bug, I want you to loop back to
> fix it. Do not stop until it is solved."

This overrides the natural instinct to note a problem and move on. Operationally:

1. When you find something that looks wrong, **stop the current task**. Do not finish the step
   first.
2. **Invoke `superpowers:systematic-debugging`** and follow it. Do not start guessing at fixes.
   The skill's first requirement is a written hypothesis before any code change; this project's
   own Day 21 failure branch requires the same thing independently.
3. Classify the cause explicitly as one of:
   - **(i) implementation error** — fix it, commit the fix with the root cause in the message.
   - **(ii) a difference in test conditions** — write it up as a finding. Do *not* silently
     align the test to the code.
   - **(iii) a genuine discrepancy worth reporting** — write it up as a finding, record it as a
     dated deviation in whichever document made the claim.
4. **Only (i) is fixed silently.** (ii) and (iii) get a paragraph in the relevant doc and a
   line in the journal.
5. Do not proceed to the next task until the defect is either fixed or recorded as an explicit,
   dated deviation with a reason. "I'll come back to it" is not a resolution.
6. If you cannot resolve it after two genuine attempts, escalate to Nishi with the three
   candidate causes and a recommendation — but escalation means *stopping and asking*, not
   working around it.

**What "widening the tolerance until it passes" looks like, so you can catch yourself doing
it:** a test fails at `< 1e-6`; you change it to `< 1e-3`; it passes; you move on. That is the
single failure mode this entire project's gate structure exists to prevent. If a tolerance
genuinely needs to change, the change must come with a measurement showing why the old value
was wrong, not with the observation that the new value passes.

### 0.3 When to invoke which superpowers skill

The plugin is installed at `~/.claude/plugins/cache/superpowers-dev/superpowers/6.2.0/skills/`.
Per `using-superpowers`, process skills come first and set the approach; implementation follows.
Per Nishi's `CLAUDE.md` severity gating, do **not** invoke the heavy process skills for
one-line fixes — the mapping below is the gate.

| Situation in this plan | Skill | Why here specifically |
|---|---|---|
| Starting any task below | `test-driven-development` | Every task in this plan is written test-first. The plan gives you the failing test before the implementation, deliberately. |
| A test fails unexpectedly, or a number looks wrong | `systematic-debugging` | Mandatory per §0.2. This is the most important entry in this table. |
| Task 2 (Day 24 runner) — before writing any code | `brainstorming` | The runner is a genuinely new subsystem with real architecture choices (parallelism granularity, resume semantics, schema). It is the one task here where the design is not fully settled by this plan. |
| Task 2 and Task 4 — dispatching work | `subagent-driven-development` | Both have several independent, well-specified sub-pieces. Fresh subagent per piece, review between. |
| Running the same probe across many parameter values | `dispatching-parallel-agents` | Task 1's calibration and Task 4's cross-OS check are both embarrassingly parallel. |
| Before declaring any task done | `verification-before-completion` | This project has been burned by "tests pass" meaning "tests pass, and also a 1/N artifact is silently corrupting a preregistered axis." |
| After Task 2 and after Task 5 | `requesting-code-review` then `receiving-code-review` | The runner and the campaign launch are the two irreversible-ish steps. |
| Merging Week 4 work back | `finishing-a-development-branch` | Only at the very end, after Task 6. |
| Task 5 (campaign launch) | `using-git-worktrees` | Optional. The campaign takes ~15s, so isolation buys little here; skip unless you want to keep the working tree clean while it runs. |

**Do not** invoke `writing-plans` — this document *is* the plan. **Do not** invoke
`brainstorming` for Tasks 1, 3, 5, or 6; their designs are settled below and re-opening them
wastes the work that produced this document.

### 0.4 When to invoke llm-council

`llm-council` runs 5 independent advisors, has them peer-review each other anonymously, and
synthesizes a verdict. It cost real money and real time, and it earned both when it was run
against the draft of `docs/WEEK3-4_PLAN.md` — it caught the circularity threat (§0.1 of that
document, the single most important constraint on this whole benchmark) and demolished a
reasoning error about independence that would otherwise have shaped Day 21.

It is worth running on a decision that is (a) hard to reverse, (b) about *what to claim* rather
than *how to build*, and (c) where being wrong is expensive. That is a narrow set. Invoke it at
exactly these three points:

1. **Task 3, before implementing the breakdown-threshold detector.** The preregistration says
   "smallest swept value where mean error first exceeds 1% relative RMS error, via linear
   interpolation between grid points," and applies it "only to the amplitude-ratio and
   arc-coverage axes." There are real, load-bearing ambiguities in that sentence — 1% relative
   to what (see §Task 3), interpolate on which scale (linear in the parameter? log?), and what
   to do when the curve crosses the threshold more than once. Getting this wrong produces
   numbers that look authoritative and are meaningless. **Prompt to use:** give the council the
   exact preregistration text, the three ambiguities, `reference_scale.py`'s bands, and ask
   which reading is most defensible *and* most consistent with what the interferometry
   literature means by a breakdown threshold.

2. **Task 6, before writing any interpretation.** This is the highest-stakes writing in the
   project. The council's specific value here is adversarial: it will attack overclaiming,
   which is exactly the failure mode `docs/WEEK3-4_PLAN.md` Day 28 names ("this distinction is
   where benchmark papers most often overclaim"). **Prompt to use:** give it
   `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`, the actual RQ1/RQ2 result tables, and ask it to
   identify every claim that is tautological-by-construction, every claim where the CIs
   overlap, and every place the draft implies causation the design cannot support.

3. **Any time a Week 3 finding turns out to constrain Week 4 in a way this plan did not
   anticipate**, and the resolution is a judgment call rather than a bug. Do not use it as a
   substitute for `systematic-debugging` on an actual defect — a council of five opinions about
   a numerical bug is strictly worse than one traced root cause.

**Do not** invoke it for: choosing a Parquet schema, deciding on a filename convention, picking
a parallelism strategy, or anything else with an objectively checkable answer. Those are
engineering decisions with right answers; run the experiment instead.

### 0.5 Standing rules inherited from Week 3

These were binding on Days 15-21 and remain binding, without restatement in each task:

1. Commit at the end of every task, separately, with the reasoning in the message. Push and
   **verify CI is green after the push**, not just that the local suite passed.
2. Write `docs/journal/dayNN.md` for each day, in plain language, assuming the reader has not
   seen the code and did not read yesterday's entry. Include actual numbers, not "it works."
   Include what was left uncertain.
3. Any deviation from a preregistered or contracted claim goes in the document that made the
   claim, dated, with the reason — never as a silent edit.
4. Run `ruff check .`, `ruff format --check .`, and `mypy` before every commit. All three are
   CI-enforced.
5. Tests are oracle-independent: a test's reference must not import the code it checks. Where a
   reference formula is needed, reconstruct it in the test file. See `tests/test_kasa.py` and
   `tests/test_taubin.py` for the established pattern.

---

## 1. State at start (verified 2026-07-28)

Run these to confirm you are starting from where this plan assumes:

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && git log --oneline -3 && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest -q 2>&1 | tail -2
```

Expected: HEAD at `43c9041 feat(Day 22): metrics, the survivorship-bias fix, and the physical
reference scale`, and `155 passed`.

**What already exists and must not be rebuilt:**

| Module | Provides | Notes for Week 4 |
|---|---|---|
| `config.py` | `load_sweep_config(path) -> SweepConfig` | `SweepConfig` has `.axes`, `.grids`, `.baseline`, `.methods`, `.n_seeds`, `.tolerance` |
| `resolve.py` | `iter_conditions(config) -> list[ResolvedCondition]` | 359 conditions. `.name` and `.resolved` (absolute units) |
| `seeds.py` | `derive_seed(seed_index, condition_name, stream)` | The only seeding path |
| `simulate.py` | `simulate_condition(resolved, condition_name, seed_index) -> SimulatedSignal` | `.i`, `.q`, `.x_true`, `.true_phase` |
| `methods/__init__.py` | `METHOD_REGISTRY`, `fit_by_name(name, i, q, *, mean_intensity)` | **Use `fit_by_name`.** It handles `raw_atan2`'s non-uniform signature — added in the Week 3 review precisely so Day 24 would not become the fourth copy of that branch |
| `metrics.py` | `wrapped_phase_error`, `phase_error_to_displacement`, `displacement_errors`, `rmse`, `peak_absolute_error` | Day 22 |
| `aggregate.py` | `SeedOutcome`, `MethodConditionSummary`, `outcome_from_fit`, `is_gross_error`, `summarize`, `is_rankable`, `GROSS_ERROR_PHASE_RAD=0.5`, `MAX_UNUSABLE_RATE_FOR_RANKING=0.20` | Day 22 |
| `reference_scale.py` | `classify_displacement_error(error_m)`, the physical bands | Day 22 |

**Campaign size:** 359 conditions × 7 methods × 50 seeds = **125,650 fits**, previously measured
end-to-end at **14.32 s** single-threaded with BLAS pinned. Runtime is not a constraint in Week
4; do not optimize for it, and do not let a performance argument justify a design that
compromises determinism.

---

## 2. What Week 3's findings constrain about Week 4

Read `docs/WEEK3_REVIEW.md` and `docs/journal/day21.md` before Task 1. The short version, and
why each one changes what you build:

- **R1 — `failed` measures self-detection, not failure.** Heydemann self-reports 24.51% failure
  and has a 0.00% gross-error rate; Fitzgibbon self-reports 0.00% and has a 13.48% gross-error
  rate. Reported naively, the campaign would rank Fitzgibbon as flawless and Heydemann as the
  worst of the seven — exactly backwards. **Constraint:** every results table in Tasks 5 and 6
  reports failure rate, gross-error rate, and unusable rate *together*. `aggregate.py` already
  computes all three; do not report one without the others.
- **The `arc.py` sampling defect (Day 21).** `build_arc_ramp` used `endpoint=True`, duplicating
  the phase-0 sample at `arc_fraction=1.0` and biasing Heydemann by exactly `1/N` rad. Fixed.
  **Constraint:** this is the template for the class of bug Week 4 must keep hunting — an
  artifact that scales cleanly with a preregistered axis and therefore looks like a finding.
  Task 1's conditioning guard exists because the same shape of bug is waiting there.
- **§3.2's gate criterion was stated backwards, and Day 3's Finding 1 does not reproduce.**
  **Constraint:** when Task 6 cites a Week 1-3 finding, re-run it. Do not cite a journal entry
  as evidence without confirming the number still holds.
- **Taubin was misclassified in `STRUCTURAL_ADVANTAGE_PREDICTIONS.md`** (grouped with the
  ellipse fitters; it is a circle fit). Corrected. **Constraint:** Task 6's tautology-vs-finding
  captions must use the corrected classification — Taubin on `amplitude_ratio` and
  `quadrature_error_rad` is *not* a tautology, it is a genuine prediction.
- **R3 — Köning's `_MAX_ITER = 20` is load-bearing.** Validated and pre-committed. **Constraint:**
  do not change it during Week 4. If Task 5 shows a convergence problem, that is a finding.

---

## Task 1 (Day 23): Cyclic-error harmonics

**Why this matters.** Cyclic (periodic) error amplitude is *the* standard figure of merit in
interferometry nonlinearity work. It is what makes these results comparable to published
literature at all — displacement RMSE is a generic number, but "first-order cyclic error of
X nm" is the quantity Lehmann et al. and every calibration paper actually report. It is
preregistered (`docs/PREREGISTRATION.md` line 106, "Cyclic-error harmonic amplitude (first and
second order)").

**What it is, physically.** After a method recovers phase, subtract the truth. If the method has
residual uncorrected nonlinearity, the leftover error is not random — it repeats once or twice
per fringe, because the distortion is a fixed function of where you are on the ellipse. So the
residual looks like `A₁·sin(φ + θ₁) + A₂·sin(2φ + θ₂) + noise`. `A₁` is the first-order cyclic
error, `A₂` the second-order. Recovering `A₁` and `A₂` from the residual is this task.

### The design decision I already settled, with evidence

I probed this before writing the plan. **Use a least-squares projection onto
`[cos kφ, sin kφ]` at harmonics of the *true* phase. Do not use an FFT.**

The reason is `arc_fraction`. An FFT assumes the record spans a whole number of periods. 99 of
the campaign's 359 conditions have `arc_fraction < 1.0`, where that assumption is false and the
FFT's bins no longer correspond to the harmonics you want. Measured, on a residual with
injected `A₁ = 0.05`, `A₂ = 0.03`:

| method | `arc_fraction=1.0` | `arc_fraction=0.5` |
|---|---|---|
| FFT bin magnitude | A₁=0.0500, A₂=0.0300 ✅ | A₁=0.0311, A₂=0.0074 ❌ (38% and 75% wrong) |
| least-squares projection | exact to 1e-16 ✅ | exact to 1e-16 ✅ |

Least-squares is exact at *every* arc down to 0.02 on noiseless data. This is not a close call.

### The failure mode I found, which is the real content of this task

Least-squares being algebraically exact does **not** mean it is usable at small arc. With
realistic noise, it degrades catastrophically and **silently** — it returns a confident number
with no error and no warning. Measured over 200 seeds, `n=60`, injected `A₁=0.05`/`A₂=0.03`,
residual noise σ=0.005:

| `arc_fraction` | design-matrix `cond` | median A₁ rel. err | median A₂ rel. err | p90 A₂ rel. err |
|---|---|---|---|---|
| 1.0 | 1.00 | 1.3% | 2.1% | 4.9% |
| 0.75 | 1.67 | 1.2% | 2.3% | 5.6% |
| 0.6 | 2.05 | 1.4% | 2.0% | 4.8% |
| 0.5 | 3.50 | 1.4% | 2.7% | 7.5% |
| 0.45 | 4.83 | 1.4% | 3.7% | 10.2% |
| 0.4 | 6.87 | 1.5% | 6.2% | 16.1% |
| **0.35** | **10.25** | **1.6%** | **9.2%** | **24.1%** |
| 0.3 | 17.7 | 3.0% | 13.6% | 33.8% |
| 0.25 | 33.4 | 6.1% | 19.4% | 46.3% |
| 0.2 | 71.0 | 14.1% | 19.8% | 64.5% |
| 0.15 | 180.9 | 34.1% | 35.4% | 164.9% |

The cause is that `cos φ, sin φ, cos 2φ, sin 2φ` become nearly collinear when φ spans only a
small arc — you cannot distinguish "a bit of first harmonic" from "a bit of second harmonic"
when you only see a fragment of a cycle. The condition number of the design matrix tracks this
exactly and monotonically, which makes it the right thing to report.

**Design consequence:** the estimator returns the conditioning as a first-class field, and there
is a pre-committed threshold above which the amplitudes are flagged as not
well-conditioned. `HARMONIC_CONDITIONING_LIMIT = 10.0` — chosen because it is the largest
`cond` at which the second-order amplitude's median relative error stays under 10% at the
campaign's own noise baseline. It corresponds to `arc_fraction ≈ 0.35`. This is a reporting
flag, not a silent drop: the same pattern `aggregate.py` uses for `is_rankable`.

**Files:**
- Create: `src/hoqi_bench/harmonics.py`
- Create: `tests/test_harmonics.py`
- Create: `docs/journal/day23.md`
- Modify: `docs/PREREGISTRATION.md` (append the conditioning-limit deviation note)

**Interfaces:**
- Consumes: `hoqi_bench.metrics.wrapped_phase_error`, `hoqi_bench._types.{FloatArray, AnyFloatArray}`
- Produces, relied on by Tasks 2/5/6:
  - `HARMONIC_CONDITIONING_LIMIT: float`
  - `@dataclass(frozen=True) CyclicError` with fields `first_order_rad: float`,
    `second_order_rad: float`, `conditioning: float`, `well_conditioned: bool`
  - `cyclic_error(true_phase: AnyFloatArray, recovered_phase: AnyFloatArray) -> CyclicError`
  - `cyclic_error_m(result: CyclicError, wavelength_m: float) -> tuple[float, float]`

- [ ] **Step 1: Write the failing test for exact recovery**

Create `tests/test_harmonics.py`:

```python
"""
Tests for hoqi_bench.harmonics -- Day 23's cyclic-error estimator.

Oracle-independence: the reference residual is BUILT here from known
amplitudes rather than imported from the module under test, so a shared
sign or normalisation error cannot cancel out between the two.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.harmonics import HARMONIC_CONDITIONING_LIMIT, cyclic_error


def _phase_and_residual(
    n_points: int, arc_fraction: float, amp1: float, amp2: float,
    noise_std: float = 0.0, seed: int = 0,
) -> tuple[FloatArray, FloatArray]:
    """A true phase ramp plus a residual with KNOWN cyclic amplitudes."""
    rng = np.random.default_rng(seed)
    true_phase = np.linspace(0.0, arc_fraction * 2 * np.pi, n_points, endpoint=False)
    residual = amp1 * np.sin(true_phase + 0.4) + amp2 * np.sin(2 * true_phase + 1.1)
    residual = residual + rng.normal(0.0, noise_std, n_points)
    return np.asarray(true_phase, dtype=np.float64), np.asarray(residual, dtype=np.float64)


def test_recovers_known_amplitudes_to_machine_precision() -> None:
    """Noiseless, full circle: this is algebra, so it must be exact."""
    for amp1, amp2 in ((0.05, 0.0), (0.0, 0.03), (0.05, 0.03), (0.001, 0.002)):
        true_phase, residual = _phase_and_residual(60, 1.0, amp1, amp2)
        result = cyclic_error(true_phase, true_phase + residual)
        assert abs(result.first_order_rad - amp1) < 1e-12, f"A1: {result.first_order_rad}"
        assert abs(result.second_order_rad - amp2) < 1e-12, f"A2: {result.second_order_rad}"
        assert result.well_conditioned
```

- [ ] **Step 2: Run it and confirm it fails for the right reason**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest tests/test_harmonics.py -q
```

Expected: `ModuleNotFoundError: No module named 'hoqi_bench.harmonics'`. If it fails any other
way, stop and read the error — a different failure means a different problem.

- [ ] **Step 3: Write the module**

Create `src/hoqi_bench/harmonics.py`:

```python
"""
Cyclic-error harmonic amplitudes -- the interferometry field's standard
figure of merit for residual nonlinearity, and a preregistered metric
(`docs/PREREGISTRATION.md`, Metrics: "Cyclic-error harmonic amplitude
(first and second order)").

What it measures: after a method recovers phase, the leftover error is not
random if the method failed to correct some distortion -- it repeats once
or twice per fringe, because the distortion is a fixed function of position
on the ellipse. The residual therefore looks like
`A1*sin(phi + th1) + A2*sin(2*phi + th2) + noise`, and `A1`/`A2` are the
first- and second-order cyclic errors every calibration paper reports.

Why least squares and NOT an FFT (a real decision, measured before being
made): an FFT assumes the record spans a whole number of periods. 99 of the
main campaign's 359 conditions have `arc_fraction < 1.0`, where that is
false and the FFT's bins stop corresponding to the harmonics of interest.
Measured on a residual with injected A1=0.05, A2=0.03: at
`arc_fraction=0.5` the FFT reports A1=0.0311 and A2=0.0074 (38% and 75%
wrong) while the least-squares projection below is exact to 1e-16. The
projection is exact at every arc down to 0.02 on noiseless data.

**The failure mode this module guards, which is why `conditioning` is a
first-class output**: being algebraically exact is not the same as being
usable. `cos(phi), sin(phi), cos(2*phi), sin(2*phi)` become nearly
collinear when `phi` spans only a small arc -- a fragment of a cycle cannot
distinguish "some first harmonic" from "some second harmonic" -- so with
realistic noise the estimator degrades badly while still returning a
confident number, with no exception and no warning. Measured over 200
seeds at n=60 with residual noise 0.005, injected A1=0.05/A2=0.03:

    arc_fraction  cond    median A1 err  median A2 err
    1.0           1.00    1.3%           2.1%
    0.5           3.50    1.4%           2.7%
    0.35          10.25   1.6%           9.2%
    0.25          33.4    6.1%           19.4%
    0.15          180.9   34.1%          35.4%

The design matrix's condition number tracks this monotonically, so it is
reported directly rather than inferred from `arc_fraction` (which this
function never receives -- the check must be a property of the data).

Pipeline position: called by Day 24's sweep runner once per fit, on the
residual between `simulate.SimulatedSignal.true_phase` and a method's
`FitResult.recovered_phase`; its outputs become two columns of the raw
results table that Day 28's RQ1 analysis reads.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hoqi_bench._types import AnyFloatArray, FloatArray
from hoqi_bench.metrics import wrapped_phase_error

# Calibrated 2026-07-28 by direct measurement (see module docstring's table),
# not chosen as a round number: the largest design-matrix condition number at
# which the SECOND-order amplitude's median relative error stays under 10% at
# the campaign's own noise baseline. Corresponds to arc_fraction ~= 0.35.
# The first-order amplitude is far more robust (1.6% at this same point), so
# this limit is set by the harder of the two quantities, deliberately.
HARMONIC_CONDITIONING_LIMIT = 10.0

# Harmonic orders the preregistration commits to. Not a parameter: adding a
# third order after seeing results would be exactly the forking-paths problem
# docs/PREREGISTRATION.md exists to prevent.
_ORDERS = (1, 2)


@dataclass(frozen=True)
class CyclicError:
    """First- and second-order cyclic error amplitudes for one fit.

    first_order_rad, second_order_rad: amplitudes in RADIANS of phase.
        Converted to meters by `cyclic_error_m` -- kept in radians here
        because that is the unit the estimator natively produces, and a
        single conversion point is harder to get inconsistently wrong than
        two representations of the same quantity.
    conditioning: condition number of the `[cos k*phi, sin k*phi]` design
        matrix. 1.0 is a full circle; it grows without bound as the sampled
        arc shrinks. Reported always, not only on failure.
    well_conditioned: `conditioning <= HARMONIC_CONDITIONING_LIMIT`. A
        REPORTING FLAG, not a silent drop -- the amplitudes are still
        returned, matching `aggregate.is_rankable`'s own choice to keep a
        non-rankable condition's numbers while withholding its ordering.
    """

    first_order_rad: float
    second_order_rad: float
    conditioning: float
    well_conditioned: bool


def cyclic_error(true_phase: AnyFloatArray, recovered_phase: AnyFloatArray) -> CyclicError:
    """Projects the wrapped phase residual onto the first two harmonics of
    the TRUE phase, by ordinary least squares.

    Equation provenance: the residual model
    `r(phi) = sum_k [a_k*cos(k*phi) + b_k*sin(k*phi)]` is linear in
    `(a_k, b_k)`, so the amplitudes are `|A_k| = hypot(a_k, b_k)` -- the
    standard harmonic-regression form, not specific to interferometry.
    Harmonics are taken of the true phase (known here, since this is a
    simulation) rather than of sample index, which is what makes the
    estimator correct for a non-uniform or partial phase sweep.

    Failure mode: none that raises. On a degenerate input (all-identical
    phase, or a residual of length < 4) `np.linalg.lstsq` returns a
    minimum-norm solution rather than erroring, and `conditioning` becomes
    very large -- which is precisely what `well_conditioned` reports. The
    caller decides what to do with a badly-conditioned result; this
    function never silently substitutes one.
    """
    # ---- 1. The residual, via the contract's wrapped metric (never a raw
    # difference -- docs/WEEK3_METHOD_CONTRACT.md sec1) ----
    residual = wrapped_phase_error(true_phase, recovered_phase)
    phase = np.asarray(true_phase, dtype=np.float64)

    # ---- 2. Harmonic design matrix, [cos phi, sin phi, cos 2phi, sin 2phi] ----
    columns: list[FloatArray] = []
    for order in _ORDERS:
        columns.append(np.cos(order * phase))
        columns.append(np.sin(order * phase))
    design = np.column_stack(columns)

    # ---- 3. Least-squares solve, plus the conditioning that decides whether
    # the answer means anything (module docstring's table) ----
    coefficients, *_ = np.linalg.lstsq(design, residual, rcond=None)
    conditioning = float(np.linalg.cond(design))

    amplitudes = [
        float(np.hypot(coefficients[2 * index], coefficients[2 * index + 1]))
        for index, _ in enumerate(_ORDERS)
    ]

    return CyclicError(
        first_order_rad=amplitudes[0],
        second_order_rad=amplitudes[1],
        conditioning=conditioning,
        well_conditioned=conditioning <= HARMONIC_CONDITIONING_LIMIT,
    )


def cyclic_error_m(result: CyclicError, wavelength_m: float) -> tuple[float, float]:
    """Converts both amplitudes from radians of phase to meters of
    displacement, via the same `phi = 4*pi*x/lambda` relation
    `metrics.phase_error_to_displacement` uses -- so a cyclic error can be
    compared directly against `reference_scale.py`'s physical bands, which
    are in meters. Returned as a plain tuple rather than a second dataclass:
    this is a unit conversion, not a new concept."""
    scale = wavelength_m / (4 * np.pi)
    return result.first_order_rad * scale, result.second_order_rad * scale
```

- [ ] **Step 4: Run the test and confirm it passes**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest tests/test_harmonics.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Add the null-case test — the one that catches a spurious peak**

The preregistration requires "a null case (no cyclic error must yield ~zero, not a spurious
peak)." Measured floor: with residual noise σ, the estimator reports a spurious amplitude of
about `0.096·σ` for the first order and `0.128·σ` for the second (this is just the projection
of white noise onto two basis functions — it is not a bug, it is the estimator's noise floor,
and a test that demanded exactly zero would be wrong). Append to `tests/test_harmonics.py`:

```python
def test_null_case_does_not_manufacture_a_peak() -> None:
    """No injected cyclic error must not produce one. The bound is the
    estimator's real noise floor, measured at 0.096*sigma (first order) and
    0.128*sigma (second) -- the projection of white noise onto two basis
    functions, which is a property of the estimator and not a defect. A
    test demanding exactly zero at nonzero noise would be wrong."""
    true_phase, residual = _phase_and_residual(60, 1.0, 0.0, 0.0, noise_std=0.0)
    result = cyclic_error(true_phase, true_phase + residual)
    assert result.first_order_rad == 0.0
    assert result.second_order_rad == 0.0

    for noise_std in (0.001, 0.01):
        true_phase, residual = _phase_and_residual(60, 1.0, 0.0, 0.0, noise_std=noise_std, seed=1)
        result = cyclic_error(true_phase, true_phase + residual)
        assert result.first_order_rad < 0.3 * noise_std, (
            f"spurious A1={result.first_order_rad:.3e} at noise={noise_std}"
        )
        assert result.second_order_rad < 0.3 * noise_std, (
            f"spurious A2={result.second_order_rad:.3e} at noise={noise_std}"
        )
```

- [ ] **Step 6: Add the conditioning test — the one that protects the campaign**

```python
def test_conditioning_flags_the_small_arc_regime() -> None:
    """The guard that stops 99 of the campaign's 359 conditions from
    silently reporting a confident, wrong harmonic amplitude. Thresholds
    are the module's own measured calibration, checked in both directions
    so the limit cannot drift without a test noticing."""
    well = cyclic_error(*_as_pair(_phase_and_residual(60, 1.0, 0.05, 0.03)))
    assert well.well_conditioned
    assert well.conditioning < 1.5

    marginal = cyclic_error(*_as_pair(_phase_and_residual(60, 0.35, 0.05, 0.03)))
    assert marginal.conditioning > 9.0
    assert marginal.conditioning < 12.0

    degenerate = cyclic_error(*_as_pair(_phase_and_residual(60, 0.15, 0.05, 0.03)))
    assert not degenerate.well_conditioned
    assert degenerate.conditioning > 100.0


def _as_pair(pair: tuple[FloatArray, FloatArray]) -> tuple[FloatArray, FloatArray]:
    """(true_phase, residual) -> (true_phase, recovered_phase)."""
    true_phase, residual = pair
    return true_phase, true_phase + residual


def test_exact_at_small_arc_when_noiseless() -> None:
    """The distinction that justifies reporting conditioning rather than
    just refusing: the estimator is ALGEBRAICALLY exact even at
    arc_fraction=0.02. Small arc is not a correctness problem, it is a
    noise-amplification problem -- so the right response is a flag, not a
    failure."""
    true_phase, residual = _phase_and_residual(60, 0.02, 0.05, 0.03)
    result = cyclic_error(true_phase, true_phase + residual)
    assert abs(result.first_order_rad - 0.05) < 1e-9
    assert abs(result.second_order_rad - 0.03) < 1e-9
    assert not result.well_conditioned
```

- [ ] **Step 7: Add the real-pipeline test**

```python
def test_detects_uncorrected_distortion_on_a_real_condition() -> None:
    """End-to-end: raw_atan2 leaves a large first-order cyclic error on a
    condition with real quadrature error, and heydemann -- whose correction
    model IS this distortion -- leaves far less. Not a ranking claim (that
    ordering is tautological per docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md);
    this asserts the ESTIMATOR responds to real uncorrected nonlinearity,
    which a synthetic-residual test alone cannot show."""
    from pathlib import Path

    from hoqi_bench.config import load_sweep_config
    from hoqi_bench.methods import fit_by_name
    from hoqi_bench.resolve import iter_conditions
    from hoqi_bench.simulate import simulate_condition

    config = load_sweep_config(
        Path(__file__).parent.parent / "configs" / "main_campaign.toml"
    )
    conditions = {c.name: c for c in iter_conditions(config)}
    name = "axis:quadrature_error_rad=0.3"
    resolved = conditions[name].resolved
    signal = simulate_condition(resolved, name, seed_index=0)

    raw = fit_by_name(
        "raw_atan2", signal.i, signal.q, mean_intensity=resolved["mean_intensity"]
    )
    corrected = fit_by_name(
        "heydemann", signal.i, signal.q, mean_intensity=resolved["mean_intensity"]
    )
    assert not raw.failed and not corrected.failed

    raw_cyclic = cyclic_error(signal.true_phase, raw.recovered_phase)
    corrected_cyclic = cyclic_error(signal.true_phase, corrected.recovered_phase)

    assert raw_cyclic.well_conditioned
    assert raw_cyclic.first_order_rad > 10 * corrected_cyclic.first_order_rad, (
        f"raw={raw_cyclic.first_order_rad:.4e}, "
        f"corrected={corrected_cyclic.first_order_rad:.4e}"
    )
```

- [ ] **Step 8: Run everything, lint, typecheck**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest -q && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m ruff check . && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m ruff format --check . && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m mypy
```

Expected: 160 passed, and all three tools clean. **If any test fails, §0.2 applies — invoke
`systematic-debugging`, do not adjust the assertion to match the output.**

- [ ] **Step 9: Record the conditioning limit as a preregistration deviation**

`HARMONIC_CONDITIONING_LIMIT` restricts where a preregistered metric is reported. That is a
change to the analysis plan, so it must be recorded, not just coded. Append to the deviation
section of `docs/PREREGISTRATION.md`:

```markdown
### 2026-07-28 (Day 23) — cyclic-error amplitudes carry a conditioning flag

The Metrics section commits to reporting first- and second-order cyclic-error harmonic
amplitude. Day 23's implementation found that the estimator, while algebraically exact at every
`arc_fraction` down to 0.02 on noiseless data, amplifies noise without bound as the sampled arc
shrinks — the harmonic basis functions become nearly collinear on a fragment of a cycle. At the
campaign's own noise baseline, the second-order amplitude's median relative error is 2.1% at
`arc_fraction=1.0`, 9.2% at 0.35, and 35.4% at 0.15, returned in every case with no exception
and no warning.

`hoqi_bench.harmonics` therefore reports the design matrix's condition number as a first-class
output alongside both amplitudes, and flags `well_conditioned = conditioning <= 10.0` — the
largest conditioning at which the second-order amplitude's median relative error stays under
10%, corresponding to `arc_fraction ≈ 0.35`.

This does not remove or replace the preregistered metric: both amplitudes are still reported
at every condition. It adds a flag stating where they are trustworthy, matching
`aggregate.is_rankable`'s own choice to report a hard condition's numbers while withholding its
ordering. Week 5/6 analysis must not aggregate cyclic-error amplitudes across conditions
without conditioning on this flag.
```

- [ ] **Step 10: Write the journal and commit**

Write `docs/journal/day23.md` covering: what cyclic error is in plain language, why least
squares beat the FFT (with the two numbers), the conditioning failure mode with the table, how
the threshold was calibrated, and what remains uncertain (the first/second-order asymmetry —
the limit is set by the harder quantity, so first-order amplitudes are trustworthy well past
it, and Week 5 could reasonably report them on a looser flag).

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && git add -A && git commit -m "feat(Day 23): cyclic-error harmonics, with the small-arc conditioning guard

Least-squares harmonic projection, not an FFT: measured, at arc_fraction=0.5
the FFT reports A1 38% and A2 75% wrong while the projection is exact to
1e-16. 99 of the campaign's 359 conditions have arc_fraction < 1.0.

The real finding: algebraic exactness is not usability. The harmonic basis
becomes nearly collinear on a partial arc, so with realistic noise the
estimator returns a confident, badly wrong amplitude with no exception --
median second-order error 2.1% at arc 1.0, 9.2% at 0.35, 35.4% at 0.15.
Design-matrix conditioning tracks this monotonically and is now a
first-class output, with a calibrated well_conditioned flag at cond <= 10.

Recorded as a dated deviation in docs/PREREGISTRATION.md." && git push
```

Then verify CI is green before starting Task 2 — not just that the local suite passed.

---

## Task 2 (Day 24): Sweep runner + smoke campaign

**Why this is the highest-risk task in Week 4.** Everything downstream reads this module's
output. A runner that is subtly non-deterministic invalidates the entire study's stated
contribution — `docs/WEEK1-2_AUDIT.md` item **B5** already flags reproducibility as "the stated
contribution, currently unevidenced." A runner that loses work on a crash costs an afternoon. A
runner that writes rows in worker-completion order produces files that differ byte-for-byte
between runs while containing identical data, which will look like non-determinism and burn a
day of debugging.

**Invoke `superpowers:brainstorming` before writing code for this task.** It is the one task in
this plan whose design I have deliberately left open in places — the schema and resume
semantics below are my recommendation, not a settled decision, and the skill's job is to
pressure-test them against what you find when you look at the code.

### The four requirements, and the concrete mechanism for each

| Requirement | Mechanism | Why this one |
|---|---|---|
| **Incremental** | One Parquet file per condition, in `results/raw/` | A crash loses at most one condition (~350 fits, <0.1 s of work) |
| **Resumable** | Write to `<name>.parquet.tmp`, then `os.replace()` | `os.replace` is atomic on POSIX and Windows, so a file's existence *is* proof it is complete. No partial file can ever be observed, which means resume is just "skip conditions whose file exists" — no row-count heuristics, no corruption detection |
| **Deterministic** | Sort rows by `(method_name, seed_index)` before writing; one file per condition | Worker completion order cannot affect any file's contents, because each file is written by exactly one worker from a sorted frame |
| **Parallel** | `ProcessPoolExecutor` over conditions, BLAS pinned in each worker | Conditions are fully independent — no shared mutable state. Parallelising over *seeds* instead would share the condition's resolved dict across workers for no gain |

### The cross-platform trap you must handle

Condition names look like `axis:amplitude_ratio=1.25` and
`grid:arc_x_noise:arc_fraction=0.5,noise_std=0.02`. **The `:` character is illegal in Windows
filenames.** Day 26 adds a Windows CI job, so a naive `f"{condition.name}.parquet"` will pass
every local test and then fail CI on exactly one of three platforms. Sanitise deterministically
and keep the original name inside the file as a column.

**Files:**
- Create: `src/hoqi_bench/runner.py`
- Create: `scripts/run_campaign.py`
- Create: `tests/test_runner.py`
- Create: `docs/journal/day24.md`
- Modify: `.gitignore` (add `results/raw/`)

**Interfaces:**
- Consumes: `config.load_sweep_config`, `resolve.iter_conditions`, `simulate.simulate_condition`,
  `methods.fit_by_name`, `aggregate.outcome_from_fit`, `harmonics.cyclic_error` (Task 1)
- Produces, relied on by Tasks 3/5/6:
  - `RESULT_COLUMNS: tuple[str, ...]` — the raw table's schema, in order
  - `condition_filename(condition_name: str) -> str`
  - `run_condition(condition: ResolvedCondition, methods: Sequence[str], n_seeds: int) -> pd.DataFrame`
  - `run_campaign(config: SweepConfig, output_dir: Path, *, n_workers: int | None = None, resume: bool = True) -> Path`
  - `load_results(output_dir: Path) -> pd.DataFrame`

- [ ] **Step 1: Write the failing determinism test first**

This is the test the whole task exists to satisfy, so it is written first. Create
`tests/test_runner.py`:

```python
"""
Tests for hoqi_bench.runner -- Day 24's sweep runner.

The two tests that matter here are determinism and resumability. A silently
non-reproducible sweep invalidates the entire study (docs/WEEK1-2_AUDIT.md
item B5: reproducibility is this project's STATED contribution), and a
non-resumable one turns any crash into a full restart. Both are asserted
byte-for-byte rather than approximately -- an "almost identical" result
file is exactly the thing that hides a real nondeterminism.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from hoqi_bench.config import load_sweep_config
from hoqi_bench.runner import (
    RESULT_COLUMNS,
    condition_filename,
    load_results,
    run_campaign,
)

SMOKE_CONFIG = Path(__file__).parent.parent / "configs" / "smoke.toml"


def _hash_directory(directory: Path) -> str:
    """One hash over every produced file, in sorted filename order."""
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.parquet")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_two_runs_are_byte_identical(tmp_path: Path) -> None:
    """Determinism, asserted the only way that actually proves it."""
    config = load_sweep_config(SMOKE_CONFIG)

    first = tmp_path / "first"
    second = tmp_path / "second"
    run_campaign(config, first, n_workers=2, resume=False)
    run_campaign(config, second, n_workers=2, resume=False)

    assert _hash_directory(first) == _hash_directory(second)


def test_worker_count_does_not_change_results(tmp_path: Path) -> None:
    """The specific nondeterminism this design is built to exclude: if
    output depended on worker scheduling, 1 worker and 4 workers would
    disagree. This is a stronger check than running twice at the same
    worker count, which can pass on a scheduler that happens to be
    repeatable."""
    config = load_sweep_config(SMOKE_CONFIG)

    serial = tmp_path / "serial"
    parallel = tmp_path / "parallel"
    run_campaign(config, serial, n_workers=1, resume=False)
    run_campaign(config, parallel, n_workers=4, resume=False)

    assert _hash_directory(serial) == _hash_directory(parallel)
```

- [ ] **Step 2: Run it, confirm it fails on the import**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest tests/test_runner.py -q
```

Expected: `ModuleNotFoundError: No module named 'hoqi_bench.runner'`.

- [ ] **Step 3: Write the runner**

Create `src/hoqi_bench/runner.py`. The BLAS pin must be the first thing in the module, before
numpy is imported transitively, for the same reason `conftest.py` puts it first:

```python
"""
The sweep runner: turns a validated `SweepConfig` into the raw results
table every downstream layer reads.

Why this exists: Weeks 1-3 built a forward model, seven methods, and a
metrics layer, but nothing that runs `(condition x method x seed)` at
campaign scale. This module is that, and it is held to four requirements
from `docs/WEEK3-4_PLAN.md` Day 24 -- incremental, resumable, deterministic,
parallel -- because a sweep that silently loses any one of them invalidates
the study's stated reproducibility contribution (`docs/WEEK1-2_AUDIT.md`
item B5).

Design decisions, each against a real alternative:

1. **One Parquet file per CONDITION, not one file for the campaign.** A
   single appended file cannot be made crash-safe without a write-ahead
   log, and cannot be written in parallel without a lock that serialises
   the thing parallelism was for. Per-condition files make "incremental"
   and "parallel" the same mechanism.

2. **Atomic publish via `os.replace`.** Each file is written to
   `<name>.parquet.tmp` and then renamed. `os.replace` is atomic on both
   POSIX and Windows, so a reader can never observe a partial file, so a
   file's EXISTENCE is proof of completeness. Resume is therefore just
   "skip conditions whose file exists" -- no row counting, no checksum
   recovery, no corrupt-file handling, because the corrupt state is
   unreachable by construction.

3. **Rows sorted by `(method_name, seed_index)` before writing.** Worker
   completion order must not reach the bytes on disk. Without this, two
   runs containing identical DATA produce different FILES, which reads as
   nondeterminism and costs a day to diagnose.

4. **Parallelism at the CONDITION level.** Conditions share no mutable
   state. Parallelising over seeds instead would share the resolved
   condition across workers and gain nothing -- the campaign is 14 s
   single-threaded, so parallelism here is for wall-clock comfort during
   development, not necessity.

5. **Condition names are sanitised for the filesystem.** Names contain
   `:` (`axis:amplitude_ratio=1.25`), which is ILLEGAL in Windows
   filenames -- and `docs/WEEK3-4_PLAN.md` Day 26 adds a Windows CI job.
   The unsanitised name is preserved as a column, so the mapping is never
   lossy.

Pipeline position: reads `config.py` + `resolve.py`, calls `simulate.py`
and `methods/`, computes metrics via `metrics.py`/`aggregate.py` and
`harmonics.py`, writes `results/raw/*.parquet`. Day 25's statistics layer
and Day 28's analysis both read it back through `load_results`.
"""

from __future__ import annotations

import os

# Must precede any transitive numpy import in a worker process -- see
# conftest.py's docstring for the measurement showing a post-import
# assignment does NOT take effect, and Day 20's runtime probe for the hard
# crash this prevents (not merely the nondeterminism).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import re  # noqa: E402
from collections.abc import Sequence  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402

from hoqi_bench.aggregate import outcome_from_fit  # noqa: E402
from hoqi_bench.config import SweepConfig  # noqa: E402
from hoqi_bench.forward_model import HENE_WAVELENGTH_M  # noqa: E402
from hoqi_bench.harmonics import cyclic_error  # noqa: E402
from hoqi_bench.methods import fit_by_name  # noqa: E402
from hoqi_bench.resolve import ResolvedCondition, iter_conditions  # noqa: E402
from hoqi_bench.simulate import simulate_condition  # noqa: E402

# The raw table's schema, in order. Fixed here rather than inferred from a
# dict so that a column added by mistake fails loudly instead of silently
# changing every downstream reader's expectations.
RESULT_COLUMNS: tuple[str, ...] = (
    "condition_name",
    "method_name",
    "seed_index",
    "failed",
    "reason",
    "converged",
    "n_iter",
    "displacement_rmse_m",
    "peak_absolute_error_m",
    "phase_rmse_rad",
    "cyclic_first_order_rad",
    "cyclic_second_order_rad",
    "cyclic_conditioning",
    "cyclic_well_conditioned",
    "runtime_s",
)

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._=-]")


def condition_filename(condition_name: str) -> str:
    """Maps a condition name to a filesystem-safe basename.

    `:` and `,` appear in every grid condition's name and `:` is illegal on
    Windows (Day 26's CI matrix includes it). Replacement is a pure
    character substitution, so it is deterministic and collision-free for
    this project's name grammar -- `resolve.py` builds names only from
    parameter names, `=`, `.`, digits, and the separators replaced here.
    """
    return _UNSAFE_FILENAME_CHARS.sub("_", condition_name) + ".parquet"


def run_condition(
    condition: ResolvedCondition,
    methods: Sequence[str],
    n_seeds: int,
    wavelength_m: float = HENE_WAVELENGTH_M,
) -> pd.DataFrame:
    """Every `(method, seed)` for one condition, as a sorted frame.

    Failure mode: a method that RAISES would abort the whole campaign, so
    this is the layer that must not let one through -- but no guard is
    added here, deliberately. Day 20's robustness matrix already proved
    all 7 methods return a `failed` result rather than raising on every
    adversarial input, and `tests/test_robustness_matrix.py` re-checks
    that on every commit. Catching exceptions here would convert a real
    regression in that guarantee into a silently-degraded results table.
    """
    rows = []
    for method_name in methods:
        for seed_index in range(n_seeds):
            signal = simulate_condition(condition.resolved, condition.name, seed_index)
            result = fit_by_name(
                method_name,
                signal.i,
                signal.q,
                mean_intensity=condition.resolved["mean_intensity"],
            )
            outcome = outcome_from_fit(result, signal.true_phase, wavelength_m)
            harmonic = cyclic_error(signal.true_phase, result.recovered_phase)
            rows.append(
                {
                    "condition_name": condition.name,
                    "method_name": method_name,
                    "seed_index": seed_index,
                    "failed": outcome.failed,
                    "reason": outcome.reason,
                    "converged": result.converged,
                    "n_iter": result.n_iter,
                    "displacement_rmse_m": outcome.displacement_rmse_m,
                    "peak_absolute_error_m": outcome.peak_absolute_error_m,
                    "phase_rmse_rad": outcome.phase_rmse_rad,
                    "cyclic_first_order_rad": harmonic.first_order_rad,
                    "cyclic_second_order_rad": harmonic.second_order_rad,
                    "cyclic_conditioning": harmonic.conditioning,
                    "cyclic_well_conditioned": harmonic.well_conditioned,
                    "runtime_s": result.runtime_s,
                }
            )

    frame = pd.DataFrame(rows, columns=list(RESULT_COLUMNS))
    # Design decision 3: sort before writing, so worker scheduling cannot
    # reach the bytes on disk.
    return frame.sort_values(["method_name", "seed_index"]).reset_index(drop=True)


def _run_and_write(args: tuple[ResolvedCondition, list[str], int, Path]) -> str:
    """One worker's whole job. Module-level (not a closure) because
    `ProcessPoolExecutor` pickles the callable."""
    condition, methods, n_seeds, output_dir = args
    frame = run_condition(condition, methods, n_seeds)
    final_path = output_dir / condition_filename(condition.name)
    temp_path = final_path.with_suffix(".parquet.tmp")
    frame.to_parquet(temp_path, index=False)
    os.replace(temp_path, final_path)  # design decision 2: atomic publish
    return condition.name


def run_campaign(
    config: SweepConfig,
    output_dir: Path,
    *,
    n_workers: int | None = None,
    resume: bool = True,
) -> Path:
    """Runs every condition in `config`, writing one Parquet file each.

    `resume=True` skips any condition whose output file already exists.
    That check is sound precisely because of the atomic publish above --
    a file exists only if it was completely written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    conditions = iter_conditions(config)

    pending = [
        condition
        for condition in conditions
        if not (resume and (output_dir / condition_filename(condition.name)).exists())
    ]
    if not pending:
        return output_dir

    jobs = [(c, list(config.methods), config.n_seeds, output_dir) for c in pending]

    if n_workers == 1:
        # Serial path kept explicit rather than a 1-worker pool: it makes a
        # debugging session single-process, and it is the path the
        # worker-count determinism test compares against.
        for job in jobs:
            _run_and_write(job)
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            list(pool.map(_run_and_write, jobs))

    return output_dir


def load_results(output_dir: Path) -> pd.DataFrame:
    """Reads every per-condition file back as one frame, in a
    deterministic order (sorted filename, then the within-file order that
    `run_condition` already fixed)."""
    paths = sorted(output_dir.glob("*.parquet"))
    if not paths:
        raise FileNotFoundError(f"no result files in {output_dir}")
    frames = [pd.read_parquet(path) for path in paths]
    return pd.concat(frames, ignore_index=True)
```

- [ ] **Step 4: Run the determinism tests**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest tests/test_runner.py -q
```

Expected: `2 passed`. **If the byte-identity test fails, this is the single most important
failure in Week 4 — invoke `systematic-debugging` immediately.** The likely causes, in order of
probability: (a) rows not sorted before write, (b) a Parquet writer embedding a timestamp or
`created_by` string — check with `pyarrow.parquet.read_metadata`, (c) a genuine seeding leak.
Do not proceed until it is byte-identical.

- [ ] **Step 5: Add the resumability test**

```python
def test_resume_reproduces_an_uninterrupted_run(tmp_path: Path) -> None:
    """Kill mid-run, restart, verify the result is identical to a clean
    run. Simulated by running the campaign, deleting a subset of the
    output files, and re-running with resume=True -- which exercises the
    same code path a real crash would, without needing to actually kill a
    process mid-write (the atomic publish makes a torn file unreachable,
    so there is no torn state to simulate)."""
    config = load_sweep_config(SMOKE_CONFIG)

    reference = tmp_path / "reference"
    run_campaign(config, reference, n_workers=2, resume=False)
    reference_hash = _hash_directory(reference)

    interrupted = tmp_path / "interrupted"
    run_campaign(config, interrupted, n_workers=2, resume=False)
    produced = sorted(interrupted.glob("*.parquet"))
    assert len(produced) >= 2, "smoke config must have >= 2 conditions for this test"
    for path in produced[: len(produced) // 2 + 1]:
        path.unlink()

    run_campaign(config, interrupted, n_workers=2, resume=True)
    assert _hash_directory(interrupted) == reference_hash


def test_resume_does_not_redo_completed_conditions(tmp_path: Path) -> None:
    """Resume must actually skip, not silently recompute -- otherwise the
    test above would pass even with resume broken."""
    config = load_sweep_config(SMOKE_CONFIG)
    output = tmp_path / "out"
    run_campaign(config, output, n_workers=1, resume=False)

    stamps = {path: path.stat().st_mtime_ns for path in output.glob("*.parquet")}
    run_campaign(config, output, n_workers=1, resume=True)
    for path, stamp in stamps.items():
        assert path.stat().st_mtime_ns == stamp, f"{path.name} was rewritten on resume"


def test_schema_and_row_count_are_exact(tmp_path: Path) -> None:
    config = load_sweep_config(SMOKE_CONFIG)
    output = tmp_path / "out"
    run_campaign(config, output, n_workers=1, resume=False)

    frame = load_results(output)
    assert tuple(frame.columns) == RESULT_COLUMNS
    from hoqi_bench.resolve import iter_conditions

    expected = len(iter_conditions(config)) * len(config.methods) * config.n_seeds
    assert len(frame) == expected


def test_condition_filename_is_windows_safe() -> None:
    """`:` is illegal in Windows filenames and appears in every grid
    condition's name. Day 26 adds a Windows CI job, so this would
    otherwise pass locally and fail on exactly one platform."""
    unsafe = "grid:arc_x_noise:arc_fraction=0.5,noise_std=0.02"
    name = condition_filename(unsafe)
    for character in ':,<>"|?*':
        assert character not in name
    assert name.endswith(".parquet")
    assert condition_filename(unsafe) == name  # deterministic
```

- [ ] **Step 6: Write the campaign entry point**

Create `scripts/run_campaign.py` — a thin CLI over `run_campaign`, with progress logging, so
Day 27 has something to launch:

```python
"""
Campaign entry point: `python scripts/run_campaign.py [config] [output_dir]`.

Thin by design -- every decision lives in `hoqi_bench.runner`, so that the
thing Day 27 launches and the thing Day 24's tests exercise are the same
code. A script that reimplements any part of the runner is a script that
can drift from what was tested.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from hoqi_bench.config import load_sweep_config
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.runner import condition_filename, run_campaign

DEFAULT_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "results" / "raw"


def main() -> int:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    config = load_sweep_config(config_path)
    conditions = iter_conditions(config)
    total_fits = len(conditions) * len(config.methods) * config.n_seeds

    already_done = sum(
        1 for c in conditions if (output_dir / condition_filename(c.name)).exists()
    )
    print(f"config:     {config_path}")
    print(f"output:     {output_dir}")
    print(f"conditions: {len(conditions)} ({already_done} already complete)")
    print(f"methods:    {len(config.methods)}  seeds: {config.n_seeds}")
    print(f"total fits: {total_fits:,}")

    start = time.perf_counter()
    run_campaign(config, output_dir, resume=True)
    elapsed = time.perf_counter() - start

    print(f"done in {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Run the smoke campaign end-to-end**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python scripts/run_campaign.py configs/smoke.toml /tmp/hoqi_smoke && ls /tmp/hoqi_smoke | head
```

Then confirm the data is sane, not just present:

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -c "
from pathlib import Path
from hoqi_bench.runner import load_results
frame = load_results(Path('/tmp/hoqi_smoke'))
print(frame.groupby('method_name')[['displacement_rmse_m','failed','cyclic_first_order_rad']].mean())
print('rows:', len(frame), 'nulls:', frame['displacement_rmse_m'].isna().sum())
"
```

**Sanity check, not a formality:** `raw_atan2` must have the largest displacement RMSE of the
seven. If it does not, something is wired wrong — the naive baseline cannot beat methods that
fit the distortion. §0.2 applies.

- [ ] **Step 8: Full suite, lint, typecheck, journal, commit**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest -q && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m ruff check . && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m mypy
```

Add `results/raw/` to `.gitignore` — 359 Parquet files are generated output, not source. Write
`docs/journal/day24.md` covering the four requirements and the mechanism for each, the Windows
filename trap, and the byte-identity result. Commit and push, then **use
`superpowers:requesting-code-review`** on the runner before moving to Task 3 — this is the
module everything downstream trusts.

---

## Task 3 (Day 25): Statistics layer

**Why the constraint here is "implement exactly, invent nothing."** The preregistration fixes
these three procedures precisely so that the analysis cannot be tuned after seeing results. The
temptation on this day is to notice that some other test would be more appropriate and add it.
That is the forking-paths problem, and it is the reason preregistration exists.

**Invoke `llm-council` before Step 3** (the breakdown-threshold detector) — see §0.4 item 1 for
the exact prompt. There are three real ambiguities in the preregistered sentence, and resolving
them by taste rather than by argument is how a benchmark ends up with authoritative-looking
numbers that mean nothing.

The preregistered text, verbatim:

> Breakdown-threshold: smallest swept value where mean error (excluding outright failures,
> tracked separately) first exceeds 1% relative RMS error, via linear interpolation between grid
> points. **Applies only to the amplitude-ratio and arc-coverage axes.**

> Multiple-comparison correction: **Bonferroni, family = all pairwise method comparisons WITHIN
> a single research question and a single swept condition** (21 pairwise comparisons per
> condition for 7 methods, corrected alpha = 0.05/21 ≈ 0.0024 per condition).

> Bootstrap confidence intervals (percentile method) on the mean across 50 seeds per condition.

**The three ambiguities to put to the council:**
1. **"1% relative RMS error" — relative to what?** `reference_scale.py` defines
   `PREREGISTERED_TOLERANCE_M = 0.01 * FULL_FRINGE_DISPLACEMENT_M` (1% of λ/2 = 3.16 nm), which
   is one reading. Another is 1% of the record's own displacement range, which varies with
   `arc_fraction` and would make the arc-coverage axis's threshold self-referential. Day 21's
   gate hit this same ambiguity and resolved it for that purpose by fixing the denominator
   explicitly; this needs the same treatment and the answer may differ.
2. **Interpolate on which scale?** The amplitude-ratio grid is roughly linear
   (`1.0, 1.02, 1.05, 1.1, …`) but arc-coverage is closer to logarithmic
   (`1.0, 0.75, 0.5, …, 0.05, 0.02`). Linear interpolation in the parameter is stated; linear
   interpolation in `log(parameter)` is arguably what "between grid points" means on a
   log-spaced axis.
3. **What if the curve crosses more than once?** "First exceeds" implies scanning in a
   direction. State the direction explicitly, and state what is reported when the error is
   already above tolerance at the first grid point (which will happen for `raw_atan2`).

**Files:**
- Create: `src/hoqi_bench/statistics.py`
- Create: `tests/test_statistics.py`
- Create: `docs/journal/day25.md`
- Modify: `docs/PREREGISTRATION.md` (record the three ambiguity resolutions as dated clarifications)

**Interfaces:**
- Produces:
  - `bootstrap_ci(values, *, n_resamples=10_000, confidence=0.95, seed) -> tuple[float, float]`
  - `breakdown_threshold(parameter_values, mean_errors, tolerance_m) -> float | None`
  - `BONFERRONI_FAMILY_SIZE: int` (21)
  - `corrected_alpha(alpha=0.05) -> float`
  - `pairwise_comparisons(summaries_at_condition) -> list[PairwiseComparison]`

- [ ] **Step 1: Write the breakdown-threshold test with hand-computed crossings**

The preregistration requires testing "against synthetic error curves with **known** crossing
points." Hand-compute the arithmetic in the test's comments — this is a `DOCUMENTATION_STANDARD`
requirement for metrics, and it is what makes the test an oracle rather than a restatement.

```python
def test_breakdown_threshold_on_a_hand_computed_crossing() -> None:
    """Grid [1.0, 1.1, 1.2], errors [1e-9, 2e-9, 6e-9], tolerance 3e-9.
    The crossing lies between 1.1 (2e-9, below) and 1.2 (6e-9, above).
    Linear interpolation: the tolerance is (3e-9 - 2e-9) / (6e-9 - 2e-9)
    = 0.25 of the way from 1.1 to 1.2, so the threshold is
    1.1 + 0.25 * 0.1 = 1.125. Computed by hand, not by running the code."""
    threshold = breakdown_threshold([1.0, 1.1, 1.2], [1e-9, 2e-9, 6e-9], 3e-9)
    assert threshold is not None
    assert abs(threshold - 1.125) < 1e-12


def test_breakdown_threshold_is_none_when_never_exceeded() -> None:
    """A method that stays under tolerance across the whole swept range
    has no breakdown threshold. Returning None is meaningfully different
    from returning the largest grid value, and Week 6's table must show
    the difference."""
    assert breakdown_threshold([1.0, 1.1, 1.2], [1e-9, 1e-9, 1e-9], 3e-9) is None


def test_breakdown_threshold_when_already_above_at_first_grid_point() -> None:
    """raw_atan2 will be above tolerance from the first point on several
    axes. The resolution recorded in docs/PREREGISTRATION.md's Day 25
    clarification is to return the first grid value itself, since no
    interpolation is possible below the grid's own start."""
    assert breakdown_threshold([1.0, 1.1, 1.2], [9e-9, 9e-9, 9e-9], 3e-9) == 1.0
```

- [ ] **Step 2: Write the bootstrap CI test against a known distribution**

```python
def test_bootstrap_ci_brackets_a_known_mean() -> None:
    """A percentile bootstrap on 50 draws from N(mu=5, sigma=1) must
    bracket mu comfortably, and must be reproducible from its seed."""
    rng = np.random.default_rng(0)
    values = rng.normal(5.0, 1.0, 50)

    low, high = bootstrap_ci(values, seed=42)
    assert low < 5.0 < high
    assert high - low < 1.0  # 50 samples of unit sigma -> CI width ~0.55

    assert bootstrap_ci(values, seed=42) == (low, high)  # deterministic
    assert bootstrap_ci(values, seed=43) != (low, high)  # genuinely resampling
```

- [ ] **Step 3: Implement, verify, commit**

Implement `src/hoqi_bench/statistics.py` following the council's resolutions from §0.4. Record
each resolution as a dated clarification in `docs/PREREGISTRATION.md` — these are
interpretations of an ambiguous preregistered sentence, so they must be timestamped before
results exist, which is why this task comes before Task 5 and not after.

**Hard rule restated:** if you find yourself wanting a test the preregistration does not name,
stop and flag it for Nishi. Do not add it.

---

## Task 4 (Day 26): Reproducibility hardening

**Why this is the highest-leverage day in Week 4.** `docs/WEEK1-2_AUDIT.md` item **B5** says
reproducibility is this project's stated contribution and is currently unevidenced. Everything
else in Week 4 produces results; this day produces the evidence that the results mean anything.
A benchmark whose headline claim is reproducibility, with no cross-platform evidence, is making
a claim it has not tested.

**Use `superpowers:subagent-driven-development`** — the four pieces below are independent and
well-specified.

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `tests/test_reproducibility.py`
- Create: `docs/journal/day26.md`

- [ ] **Step 1: Extend CI to a three-OS matrix**

Extend the existing workflow to `ubuntu-latest`, `macos-latest`, `windows-latest` × Python
3.10, 3.11. This is where Task 2's `condition_filename` sanitiser gets its real test — if you
skipped it, the Windows job fails here.

- [ ] **Step 2: Add the fresh-clone job (audit item C6)**

A job that clones the repo from scratch into a clean directory, installs it, runs the smoke
campaign, and asserts the result hash matches a committed expected value. This catches the
class of defect where the repo only works because of state in the developer's working tree —
an uncommitted file, a stale `.egg-info`, a locally-installed package that is not in
`pyproject.toml`.

- [ ] **Step 3: Add the cross-platform determinism assertion**

Commit the smoke campaign's expected SHA-256 to the repo, and have every OS job assert its own
run matches. **This is the one that might genuinely fail**, because BLAS implementations differ
across platforms and floating-point summation order is not guaranteed identical.

**Stop-and-ask trigger, per `docs/WEEK3-4_PLAN.md` Day 26:** if cross-OS hashes differ and the
cause is BLAS-level, **stop and present the options to Nishi** — pin a BLAS, relax to
tolerance-based comparison, or document the platform dependence as a finding. Do not silently
choose. This is one of the few places in Week 4 where §0.2's "do not stop until solved" yields
to an explicit escalation, because the resolution is a claim about what the benchmark promises,
not a bug.

- [ ] **Step 4: Pin dependencies and record the resolved environment**

Commit a lockfile or fully-pinned requirements, and record the resolved versions (numpy 2.2.6,
scipy 1.15.3 locally) in the journal. "Reproducible" without a pinned environment is a claim
about one machine on one day.

**A live instance of this exact gap, found during Day 24, not hypothetical:** `pandas>=2.0` in
`pyproject.toml` resolved to pandas 2.3.3 on CI's Python 3.10 job and **pandas 3.0.5** — a major
version — on the 3.11 job, from the *same* commit, the *same* declared constraint. It surfaced
as a stub-typing mypy failure (fixed in the Day 24 commit), but a loose floor allowing a major
version jump could just as easily produce a silent *behavioral* difference between the two CI
jobs that nothing catches. Pin `pandas` to an exact version here, not just the floor.

---

## Task 5 (Day 27): Launch the main campaign

**Pre-flight, all blocking. Do not launch if any fails.**

- [ ] **Step 1: Verify the configured grid matches the preregistration exactly**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest tests/test_docs_consistency.py -q
```

Any discrepancy between `configs/main_campaign.toml` and `docs/PREREGISTRATION.md` is a
**stop**. The whole value of a preregistered grid is that it was fixed before results existed.

- [ ] **Step 2: Verify the pre-data documents are committed and timestamped**

`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` and `docs/PREREGISTRATION.md` (including Task 1's and
Task 3's dated clarifications) must be committed **before** any result file exists. Confirm with
`git log` that their commit timestamps precede this launch. This is what separates "predicted"
from "explained after the fact."

- [ ] **Step 3: Verify Task 2's guarantees still hold**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && /home/nishadrobotics/venvs/hoqi-bench/bin/python -m pytest tests/test_runner.py tests/test_reproducibility.py -q
```

- [ ] **Step 4: Launch**

```bash
cd /mnt/c/Users/nisha/Desktop/ee-portfolio/hoqi-bench && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/nishadrobotics/venvs/hoqi-bench/bin/python scripts/run_campaign.py
```

Expected: 359 conditions, 125,650 fits, on the order of 15-60 s. **If it takes dramatically
longer than the 14.32 s previously measured, stop and find out why** — a 100x slowdown means
something is recomputing, and a runner that silently recomputes is a runner whose resume logic
is broken.

- [ ] **Step 5: Quick-look before trusting anything**

Build a small script that plots error vs. swept value per method for each axis, and **look at
it**. The specific things to check, each of which has a known correct answer:
- `raw_atan2` is the worst method on every classic axis **among usable fits** — filter to
  `not failed and not gross_error` (per `aggregate.is_gross_error`) before comparing means.
  **Correction found during Day 24 (not in the original plan): a naive `groupby(...).mean()`
  over the raw table, with no filtering, does NOT show this** — it showed Heydemann and Köning
  ranked best and Fitzgibbon near the bottom, exactly backwards. That is R1
  (`docs/WEEK3_REVIEW.md`) reproduced at full campaign scale: Heydemann self-reports failure
  24.5% of the time and excludes those attempts from its own mean, while Fitzgibbon self-reports
  0% failure while silently returning gross errors 13.5% of the time that get averaged in as if
  real. Once filtered to usable rows only, `raw_atan2` and `kasa` correctly sink to the bottom.
  Use `aggregate.summarize`/`is_rankable`, never a bare `groupby(...).mean()` on the raw table.
- `heydemann`, `halir_flusser`, `fitzgibbon`, `koning` are near-ceiling on the classic axes.
  This is the tautology (`STRUCTURAL_ADVANTAGE_PREDICTIONS.md` §0.1) — seeing it is a
  correctness check, not a finding.
- `kasa` and `taubin` track `raw_atan2` on `amplitude_ratio` and `quadrature_error_rad`
  (no free parameter for either) but beat it on `dc_offset` (a circle has a center).
- Nothing is exactly zero, and nothing is `NaN` where a fit reported success.

- [ ] **Step 6: Commit the results manifest, not the results**

Commit the run manifest (config hash, environment, per-condition file hashes, timestamps) and
the aggregate summaries. Do **not** commit 359 raw Parquet files — they are regenerable from a
committed config and a pinned environment, which is the whole point of Task 4.

---

## Task 6 (Day 28): RQ1 + RQ2 analysis

**Invoke `llm-council` before writing any interpretation** — §0.4 item 2. This is the highest-
stakes writing in the project and the council's specific value is adversarial.

**RQ1:** comparative ranking across every classic non-ideality, on displacement RMSE,
cyclic-error harmonics, runtime, and failure rate, with bootstrap CIs.
**RQ2:** breakdown thresholds per method per condition.

**Binding framing constraints:**

- **Report the tautology explicitly.** Heydemann's dominance on `amplitude_ratio`,
  `quadrature_error_rad`, and `dc_offset` is guaranteed by construction — the forward model
  *is* Heydemann's own distortion model. Caption those results as a construction check, not a
  ranking finding. Use the *corrected* classification from Day 21: Taubin is a **circle** fit,
  so its behaviour on the classic axes is a genuine prediction, not a tautology.
- **Report all three reliability rates beside every error number**, per R1. A table showing
  Fitzgibbon at 0.00% failure without its 13.48% gross-error rate is actively misleading.
- **Report cyclic-error amplitudes only with their conditioning flag**, per Task 1's deviation.
  Never aggregate them across conditions without conditioning on `well_conditioned`.
- **Be explicit about which differences are statistically distinguishable** and which fall
  within overlapping CIs. This is where benchmark papers most often overclaim.
- **Label the interpretation `DRAFT INTERPRETATION`** for Nishi to revise, not rubber-stamp.
- **Flag anything surprising separately** so Nishi can judge finding vs. bug — and per §0.2, if
  it looks like a bug, chase it down before writing it up as a finding.

---

## Decision points reserved for Nishi

Do not resolve these autonomously. Stop and ask.

| Where | Decision |
|---|---|
| Task 3 | The three breakdown-threshold ambiguities, if the council's advisors disagree |
| Task 4 Step 3 | Cross-OS hash divergence with a BLAS-level cause |
| Task 5 Step 1 | Any config/preregistration discrepancy |
| Task 6 | Whether any surprising result is a finding or a bug, once you have chased it |
| Anywhere | A statistical test that seems needed but was not preregistered |

---

## Self-review

Run against `docs/WEEK3-4_PLAN.md`'s Week 4 section (Days 22-28):

**Spec coverage.** Day 22 — complete before this plan (commit `43c9041`). Day 23 → Task 1
(harmonics, both orders, known-amplitude validation, null case, conventions settled by
measurement rather than by consulting arXiv:2207.03488, which the plan named as optional).
Day 24 → Task 2 (all four requirements with a named mechanism each; both mandatory tests;
smoke campaign). Day 25 → Task 3 (bootstrap, breakdown, Bonferroni; the "invent nothing" rule).
Day 26 → Task 4 (multi-OS matrix, fresh-clone job, cross-platform determinism, pinned deps).
Day 27 → Task 5 (all three blocking pre-flight checks, launch, quick-look). Day 28 → Task 6
(RQ1/RQ2 with all five framing constraints). **No gaps.**

**Placeholder scan.** No "TBD," no "add appropriate error handling," no "similar to Task N." The
one deliberate open item is Task 3's three ambiguities, which are explicitly routed to
`llm-council` with the exact prompt rather than left vague.

**Type consistency.** `fit_by_name(name, i, q, *, mean_intensity)` matches the real signature in
`methods/__init__.py:44`. `outcome_from_fit(result, true_phase, wavelength_m)` matches
`aggregate.py:136`. `SeedOutcome` fields used in Task 2 (`failed`, `reason`,
`displacement_rmse_m`, `peak_absolute_error_m`, `phase_rmse_rad`) match `aggregate.py:97-104`.
`CyclicError` fields are used consistently between Task 1's definition and Task 2's
`RESULT_COLUMNS`. `ResolvedCondition.name`/`.resolved` match `resolve.py:41`.

**Residual risks — both checked before publishing this plan, not left as caveats.**

1. **`cyclic_error` on a failed fit.** Task 2's `run_condition` calls it unconditionally, and a
   failed fit's `recovered_phase` is all-NaN. **Verified** (under `-W error`, so any warning
   would have raised): `np.linalg.lstsq` returns `[nan nan nan nan]` cleanly — no exception, no
   warning. Both amplitudes come out NaN, which is the correct representation of "this fit has
   no cyclic error." No short-circuit is needed.

   **But there is a real consequence to carry into Task 6.** `conditioning` is computed from
   the design matrix, which depends only on the true phase sampling, so a *failed* fit still
   reports `conditioning = 1.0` and `well_conditioned = True` alongside its NaN amplitudes.
   Filtering on `well_conditioned` alone therefore does **not** exclude failed fits. Day 28
   must filter on `well_conditioned AND NOT failed`. This is recorded here rather than
   "fixed" in `harmonics.py` because the flag is honest as it stands — the phase sampling
   genuinely was well-conditioned; the fit is what failed, and `failed` is the column that
   says so.

2. **`smoke.toml`'s size, which Task 2's resumability test depends on.** That test asserts
   `len(produced) >= 2` and deletes `produced[:len//2 + 1]`. **Verified:** the smoke config
   resolves to 3 conditions × 2 methods × 5 seeds = 30 fits. So 3 files are produced, 2 are
   deleted, and 1 survives — which exercises both the recompute path and the skip path in the
   same run. The assertion holds with margin.
