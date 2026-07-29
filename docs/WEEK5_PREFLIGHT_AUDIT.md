# Week 5 Pre-Flight Audit

Run 2026-07-28, before writing `docs/WEEK5-6_EXECUTION_PLAN.md` and before any Week 5 code. Every
finding below was verified by **executing code against the real campaign config and data**
(`configs/main_campaign.toml`, `results/main_campaign_summary.csv`, `results/raw/`), not by reading
the code. Reproduction commands are given inline so any finding can be re-checked directly.

All four findings survived: the Weeks 1-2 audit, two adversarial `llm-council` reviews, the OSF
external timestamp, Day 21's never-skip cross-validation gate, the separate Week 3 review, and all
of Week 4 (including a second `llm-council` overclaiming check on Day 28). None of those processes
were built to catch this specific class of defect — see "Why each was missed," below, per finding.

---

## P1 (CRITICAL) — RQ3's hysteresis axis never activates its direction-dependence

**Claim.** The main campaign's `hysteresis_magnitude` axis measures a *uniform radial inflation by
+h*, not path-dependent hysteresis. The defining feature of the phenomenon RQ3 asks about — that the
distortion depends on the *direction* of phase travel — is never exercised anywhere in the
125,650-fit campaign.

**Reproduction.**

```python
import sys; sys.path.insert(0, "src")
import numpy as np
from hoqi_bench.config import load_sweep_config
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import simulate_condition
from hoqi_bench import transforms

c = load_sweep_config("configs/main_campaign.toml")
conds = {x.name: x for x in iter_conditions(c)}
cond = conds["axis:hysteresis_magnitude=0.2"]
sig = simulate_condition(cond.resolved, cond.name, 0)

d = np.sign(np.gradient(sig.x_true))
print(np.unique(d))                    # [1.]
print((d == +1).mean(), (d == -1).mean())  # 1.0  0.0

i, q = sig.i, sig.q
m = cond.resolved["mean_intensity"]
h = cond.resolved["hysteresis_magnitude"]
real = transforms.hysteresis(i, q, m, h, sig.x_true)
blind = transforms.hysteresis(i, q, m, h, np.arange(len(i), dtype=float))  # any monotonic ramp
print(max(np.abs(real[0] - blind[0]).max(), np.abs(real[1] - blind[1]).max()))  # 0.0
```

**Measured.** Direction is `+1` at **100%** of samples and `-1` at **0%**, across every condition in
the campaign. The transform's output is **bit-identical** (max absolute difference exactly `0.0`) to
the same call with an arbitrary monotonic ramp substituted for `true_displacement`.

**Root cause.** `transforms.hysteresis` computes `direction = np.sign(np.gradient(true_displacement))`
(`src/hoqi_bench/transforms.py:199`). Every campaign condition's waveform comes from
`arc.build_arc_ramp` (`src/hoqi_bench/simulate.py:140`), which returns
`x_true = total_displacement_m * np.linspace(0, 1, N, endpoint=False)` — **strictly monotonic** by
construction. A monotonic input can never produce a sign change in its own gradient, so the
`direction < 0` branch of the perturbation is dead code for every condition the campaign ever
generates.

**Is it still a real distortion?** Yes — adding a constant to an ellipse's polar radius does not
yield another ellipse, so this is a genuine non-conic perturbation, and the campaign's measured
response to it is real (33.9× displacement-RMSE dynamic range for the four conic fitters over
`hysteresis_magnitude ∈ [0, 0.2]`). It is simply **not the phenomenon RQ3 names.**

**Why it was missed.** `tests/test_hysteresis.py` builds its test waveform with a private helper,
`_up_and_down_iq()`, which is an explicit **sinusoid** (`2e-6 * sin(2π · 2 · t)`) — its own docstring
states it exists specifically to give "'direction of travel' [something] to be direction-dependent
about." The production path (`simulate.py` → `arc.build_arc_ramp`) uses a monotonic ramp instead.
The unit test validates a waveform the campaign never generates — the config→run path has no test
coverage of its own. This is the same structural gap the Weeks 1-2 audit's council review already
named in the abstract ("the 47/47 suite structurally cannot find this defect class... it tests each
transform against its own formula, never the config→run path") — this is a concrete instance of
that exact prediction, three audits later.

**Secondary trap.** Kasa, Taubin, and `raw_atan2` measure **flat (1.0×)** against
`hysteresis_magnitude`. This is **floor-masking, not immunity**: their baseline error (3.6e-9 m,
dominated by the uncorrected `amplitude_ratio=1.1` / `quadrature_error_rad=0.1` baseline distortion)
swamps hysteresis's largest contribution (~6e-10 m at `hysteresis_magnitude=0.2`). Any future
write-up must check this before claiming these methods are "robust to hysteresis."

**Consequence for Week 5.** RQ3's hysteresis half cannot be answered from the preregistered
campaign. See preregistration deviation D5 and `docs/WEEK5-6_EXECUTION_PLAN.md` Task 4 for the
supplementary experiment that speaks to actual direction-dependence.

---

## P2 (CRITICAL) — RQ6 is unanswerable from the preregistered grid

**Claim.** RQ6 promises a practitioner-facing "for a given noise level, what samples-per-fit N is
needed to reach a target accuracy" design chart. The grid cannot produce it: the two axes needed to
answer the question were never swept together.

**Reproduction.**

```python
import sys; sys.path.insert(0, "src")
from hoqi_bench.config import load_sweep_config
from hoqi_bench.resolve import iter_conditions

c = load_sweep_config("configs/main_campaign.toml")
conds = iter_conditions(c)
for x in conds:
    if x.name.startswith("axis:samples_per_fit"):
        print(x.name, x.resolved["noise_std"])   # every line prints 0.0
for x in conds:
    if x.name.startswith("axis:noise_std"):
        print(x.name, x.resolved["samples_per_fit"])  # every line prints 60
print(list(c.grids.keys()))  # ['arc_x_noise', 'amplitude_x_quadrature', 'amplitude_x_noise']
```

```python
import pandas as pd
s = pd.read_csv("results/main_campaign_summary.csv")
n = s[s.condition_name.str.startswith("axis:samples_per_fit")].copy()
n["N"] = n.condition_name.str.extract(r"=(\d+)").astype(int)
p = n.pivot_table(index="N", columns="method_name", values="displacement_rmse_mean_m")
print((p.loc[20] / p.loc[1000]))
```

**Measured.** All 7 `samples_per_fit` conditions run at `noise_std = 0.0`. All 10 `noise_std`
conditions run at `samples_per_fit = 60`. The three preregistered interaction grids are
`arc_x_noise`, `amplitude_x_quadrature`, `amplitude_x_noise` — **there is no
`samples_per_fit × noise_std` grid.** Displacement RMSE ratio N=20 → N=1000 (a 50× sample increase),
at the only noise level actually swept (σ=0):

| method | ratio |
|---|---|
| fitzgibbon / halir_flusser | 1.10× |
| koning | 1.09× |
| heydemann | 0.94× (slightly *worse* at higher N) |
| kasa / taubin / raw_atan2 | **1.00× (flat to 4 significant figures)** |

At σ=0, N genuinely does not matter — this is not noise in the measurement, it is the correct
answer to a degenerate question. A noiseless fit has no averaging to do.

**Root cause / the irony on the record.** `docs/PREREGISTRATION.md` v2 justified *adding* the
`samples_per_fit` axis by citing "a measured 7x swing in mean center error (0.0201 at N=20 vs. 0.0028
at N=1000)." That 7× swing is a **noise-averaging effect** — more samples reduce the variance of a
noisy fit. The axis, once implemented, was then swept entirely at zero noise, where that averaging
benefit structurally cannot appear. The preregistration's own stated justification for the axis is
contradicted by the axis as configured.

**Why it was missed.** RQ6 was introduced *by the v2 revision that fixed Weeks 1-2 audit finding F6*
("the preregistered research questions were unanswerable from the preregistered config"). The v2
revision added the `samples_per_fit` axis to fix F6's `arc_fraction`/`hysteresis_magnitude`/
`photon_scale` gaps, and RQ6 was framed as a bonus deliverable "hiding inside the existing sweep."
Its own answerability was never independently checked — the same defect class (a preregistered RQ
with no config path to answer it) reappeared inside the very revision meant to eliminate it, and
none of the two subsequent council reviews, the OSF registration, Day 21's gate, or the Week 3
review were built to check RQ↔grid coverage specifically.

**Consequence for Week 5.** RQ6 cannot be answered from the preregistered campaign. See
preregistration deviation D6 and `docs/WEEK5-6_EXECUTION_PLAN.md` Task 6 for the supplementary
N×noise grid.

---

## P3 (HIGH) — the preregistered `cost` metric is 100% unmeasured

**Claim.** `docs/PREREGISTRATION.md`'s Metrics section commits to reporting "wall-clock time per fit
(mean and std across seeds, same hardware)" as part of RQ1. It was never recorded.

**Reproduction.**

```python
import pandas as pd, glob
f = sorted(glob.glob("results/raw/*.parquet"))
d = pd.concat([pd.read_parquet(x) for x in f[:20]])
print(d["runtime_s"].isna().mean())  # 1.0

s = pd.read_csv("results/main_campaign_summary.csv")
print(s["runtime_s_mean"].isna().mean())  # 1.0, across all 2,513 rows
```

**Root cause.** `methods/base.py`'s `timed_fit(fit_fn, *args, **kwargs)` is documented as "the ONE
place runtime is measured" — it wraps a fit call and returns a `FitResult` with `runtime_s`
populated via `dataclasses.replace`. `runner.py:135` calls `fit_by_name(...)` **directly**, never
`timed_fit`. So `result.runtime_s` is always `None` for every one of the 125,650 fits.

**How it failed silently.** `aggregate.py:241` computes
`runtime_s_mean=float(np.mean(runtimes)) if runtimes else float("nan")` — an empty runtime list
degrades to `NaN` rather than raising, so nothing in the pipeline flagged the gap. The already-
published `docs/RQ1_RQ2_ANALYSIS.md` omits cost entirely and does not flag the omission, so RQ1
currently reads as fully answered while being three-quarters answered.

**Design consideration for the fix.** The campaign runs under `ProcessPoolExecutor`. Wall-clock
measured inside contending parallel workers is not a clean cost measurement and does not honor the
preregistration's "same hardware" wording in any stable sense. A separate **serial, single-worker**
timing pass on a representative condition subset — chosen on structural grounds before looking at
any accuracy result, to avoid handing the analysis a second free parameter — is the more defensible
design. See `docs/WEEK5-6_EXECUTION_PLAN.md` Task 3.

**Consequence for Week 5.** Not a preregistration deviation — nothing about ranges, metrics, or
protocol changed; this is unfinished execution of already-specified instrumentation. Completing it
may require revising part of the already-drafted RQ1 interpretation (Köning, the only iterative
method, is the likeliest candidate to move once cost is real) — that check must happen explicitly,
not be assumed away.

---

## P4 (MEDIUM) — RQ5's "many-fringe ramp" half was never in the grid

**Claim.** RQ5 asks about performance under "many-fringe ramp vs. small steady-state vibration." The
`arc_fraction` axis never reaches the many-fringe regime.

**Reproduction.** `arc.build_arc_ramp`'s docstring and implementation set total phase excursion to
`arc_fraction * 2 * np.pi` — so `arc_fraction = 1.0` is **exactly one 2π cycle**, not many.
`configs/main_campaign.toml`'s `arc_fraction` axis spans `[0.02, 1.0]`. The grid therefore covers a
0.72° arc up to exactly one fringe, and never reaches multi-fringe.

**Root cause.** `docs/experimental_design.md` (§"Design choices independent of any single paper")
re-describes the top of the range as "full-circle ramp measurement" — true in the sense that
`arc_fraction=1.0` is a full 2π circle, but a quiet narrowing from RQ5's original "many-fringe"
framing to "one fringe, at most." That re-description was never recorded as a deviation.

**Why this one is lower severity than P1/P2.** It is a scoping gap, not a bug: the sub-fringe half
of RQ5 is well covered by the existing grid and is where the campaign's headline RQ1b result
(`docs/RQ1_RQ2_ANALYSIS.md`) already lives. The many-fringe half simply was never attempted.

**Consequence for Week 5.** RQ5 is answerable only over the sub-fringe regime, and must say so in
those words rather than implying the full question was addressed. See preregistration deviation D7.
Do not extend the grid to multi-fringe now — see `docs/WEEK5-6_EXECUTION_PLAN.md` Task 7's reasoning
on why that specific extension is the highest forking-paths exposure available in this project (it
would touch the axis whose sub-fringe result is already the headline finding).

---

## What is NOT broken (checked, healthy)

- **RQ4 (`photon_scale`)**: 32.6× dynamic range for conic fitters, 1.8–1.9× for circle fits — a
  real, strong response, correctly swept at `noise_std = 0.0` (the two noise models are not blended
  by any runtime branch — `simulate.py` applies both `poisson_noise` and `gaussian_noise`
  unconditionally, and exclusivity at a given condition is an emergent property of the config's
  baseline values: `noise_std=0.0` is Gaussian's exact identity, `photon_scale=1e7` at the noise-axis
  baseline is documented as "negligible, not off"). The one open question — what "equivalent noise"
  means for comparing rankings across the two models — is not a defect, it is a genuine judgment
  call, routed to `llm-council` in Task 5. A measured mapping (`σ_eff ≈ sqrt(intensity/photon_scale)`,
  confirmed against realized residuals to within ~5% across the full `photon_scale` grid) is
  available as an input to that decision.
- **RQ3's power-law fork**: `power_law.fit_power_law_exponent` exists, is tested, and correctly
  raises on non-positive input (caller must exclude the zero-distortion condition). Its documented
  fallback — low r² triggers "model power-law as an injected transform instead" — is intact.
- **181/181 tests passing**, `ruff` and `mypy --strict` both clean, CI green on the full 3-OS ×
  2-Python reproducibility matrix plus the 2-version lint/test matrix (8 jobs total).

## Week 6 release blockers (state check, 2026-07-28)

`pyproject.toml`: `version = "0.1.0"`, dependencies pinned to exact versions (Day 26). **Missing:**
`LICENSE` (blocks PyPI, Day 40), `CITATION.cff` (pairs with the Zenodo DOI, Day 41), `CHANGELOG.md`.
All three are built in this task (§1.4 of the Weeks 5-6 plan) rather than deferred to Day 40, per an
`llm-council` advisor's point that they are ten-minute template fills today and a Day 41 fire drill
if left until then.
