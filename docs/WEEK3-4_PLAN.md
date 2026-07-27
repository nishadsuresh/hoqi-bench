# Weeks 3-4 Execution Plan (Days 15-28)

Written 2026-07-27, after Weeks 1-2 closed out (81 tests, ruff + mypy --strict clean,
preregistration v2 timestamped at https://osf.io/qyw6t, all commits pushed, CI green on
Python 3.10 + 3.11). Planned with Opus; intended to be **executed by a different, cheaper
model without re-deriving the reasoning** -- so every day below states its objective, the
exact files it touches, checkable acceptance criteria, and explicit stop-and-ask triggers.

This plan supersedes the day-by-day prompts for Days 15-28 in the original 42-day build
plan (`HOQI-BENCH-PLAN.md`, vault). Where it deviates, the deviation is stated with its
reason, per the same discipline `docs/PREREGISTRATION.md` and
`docs/WEEK3_METHOD_CONTRACT.md` already hold themselves to.

---

## Part 0 -- What a 5-advisor adversarial review changed about this plan

An `llm-council` adversarial review (2026-07-27, 5 independent advisors) was run against
the draft of this plan. It overturned three of the draft's positions and named two failure
modes the draft had not. Recorded here because the changes are the substance of the plan,
not commentary on it.

### 0.1 The circularity threat (the most serious finding, previously unnamed)

**The forward model is algebraically Heydemann's own model.** `docs/experimental_design.md`
Section 1 defines:

```
I(phi) = I0 + A * cos(phi)
Q(phi) = Q0 + A * g * sin(phi + eps)
```

That is *exactly* the distortion model the Heydemann correction is derived to invert. So on
the classic-distortion axes (`amplitude_ratio`, `quadrature_error_rad`, `dc_offset`),
Heydemann is guaranteed to win **by construction**, not by merit. Reporting that as a
finding would be reporting a tautology.

This does not invalidate the benchmark, but it sharply constrains what may be claimed:

- On classic axes, the interesting quantity is **not** "does Heydemann win" (it must) but
  *how far the other methods fall behind, and where they cross tolerance* (RQ2), plus cost
  and failure rate.
- The genuinely non-tautological results live on the axes where **no method has a
  structural home-field advantage**: `hysteresis_magnitude`, power-law (RQ3), Poisson noise
  (RQ4), `arc_fraction` (RQ5), and `samples_per_fit` (RQ6).

**Action (Day 15, before any method exists):** write
`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` stating, per axis, which method the forward
model structurally favors and why -- *before* seeing results. Any later result matching a
predicted structural advantage is reported as a tautology check, not a finding. This is a
preregistration-grade commitment and must be timestamped in git before Day 22.

### 0.2 Internal agreement is near-worthless as evidence (overturns the draft's Q2 reasoning)

The draft argued for independent implementations *because* Day 21's cross-validation gate
derives evidential value from independence. Two advisors independently demolished this:
seven implementations written by one person, in one week, with one AI assistant, from one
shared mental model of conic fitting **are not independent samples**. Correlated authorship
error survives duplication perfectly. Agreement among them is weak evidence regardless of
whether they share a core.

**Consequence:** still implement independently -- but for a *different, honest* reason:
each method must faithfully follow its own paper's numerical path (Halir & Flusser's entire
contribution *is* a different numerical path from Fitzgibbon's; collapsing them into a
shared core would misrepresent both). The validation weight is carried by **external
oracles**, not internal agreement. The writeup must say so plainly rather than presenting
seven-way agreement as strong self-validation.

### 0.3 The exact-solution analytic oracle (the draft under-weighted this)

The draft treated external-package cross-validation as the foundation of Day 21. It is not
the strongest instrument available -- the forward model with **known ground truth** is.

On noiseless, exactly-generated ellipse data, every conic-fitting method must recover the
generating conic's parameters **to machine precision**. That is an analytic oracle: it does
not re-assert any method's own formula (directly answering audit item **B2**), it covers
**all 7 methods** (external packages only cover Halir & Flusser and Fitzgibbon), and it is
free.

**This becomes Tier 1 of validation.** External packages become Tier 2, internal
predictions Tier 3.

### 0.4 Differential dropout / survivorship bias (flagged independently by two advisors)

`docs/WEEK3_METHOD_CONTRACT.md` §2 mandates NaN + reason code + `failed=True` on failure,
but **never specifies how aggregation treats those rows**. Köning (iterative EIV) will fail
to converge preferentially in ill-conditioned regimes -- precisely the regimes that
discriminate between methods. A per-condition mean over surviving runs then compares
*different populations* across methods, silently flattering whichever method dropped out of
the hardest cases.

**Action (Day 22, binding):** every aggregate reports convergence rate alongside error, and
no method is ranked on any condition where any method's failure rate exceeds a threshold
fixed *before* Day 24. Recorded as a deviation/extension to the contract.

### 0.5 Corrections to the draft's own claimed facts

- The draft asserted Köning was unvalidatable because the 2014 paper is paywalled. **Wrong,
  and the information was already in `notes/related_work_table.md`:** Witkovský's own
  MATLAB implementation `EllipseFit4HC` is public on the MathWorks File Exchange, and
  Octave (free, `apt` candidate 6.4.0-2) runs it. Verified: no Python `oefpil` exists on
  PyPI, and R is not installed -- so Octave + `EllipseFit4HC` is the realistic route.
- One advisor claimed arXiv:2501.08961 is an open worked-example paper for OEFPIL usable as
  a validation oracle. **Verified false.** It is by the right authors (Witkovský, Wimmer et
  al.) but is a scanning-thermal-microscope calibration application paper, not an
  ellipse-fitting worked example with numerical validation values.

### 0.6 Other adopted changes

| Change | Source | Reason |
|---|---|---|
| Cross-validation moves to **Day 19**, not Day 21 | Executor | If agreement fails you need days to debug, not hours before a gate |
| Smoke campaign moves to **Day 24**, not Day 26 | Executor | Same reason -- find pipeline breaks with days of headroom |
| Runtime probe moves to **Day 20**, not Day 26 | This plan | Köning is the only iterative method; the "125,650 fits in seconds" projection was measured on non-iterative fits only and may be badly wrong |
| Day 21 gets an explicit **failure branch** | Contrarian | "A gate with no failure branch, seven days before launch, is a gate that gets rationalized into passing" |
| Define a **physical reference scale** before Day 24 | Outsider | Without "is 0.3 mrad a lot, compared to what requirement?", 125,650 runs produce a ranking nobody can act on |
| Multi-OS CI matrix + pinned BLAS threading | Expansionist | Turns audit item B5 (reproducibility unevidenced -- *the stated contribution*) from weakest claim to strongest, for ~1 day |
| Author emails + ILL requests on Day 15, **off critical path** | Executor + Outsider | Free, 20 minutes, never a blocker; fold in whatever arrives |

---

## Part 1 -- Alter now, before Day 15

These are pre-Week-3 corrections. Each is small, and each prevents a larger Week 3/4
problem.

### P1. Promote the condition-to-signal function into `src/` **(highest value)**

Currently there is no named unit that goes from a resolved condition to `(I, Q, x_true)`.
It exists only as ad-hoc glue in a throwaway integration script. Every method test *and*
the Day 24 sweep runner need it; without it, each will re-derive the pipeline order
independently and they will drift.

- **New file:** `src/hoqi_bench/simulate.py`
- **Function:** `simulate_condition(resolved: dict, seed: int) -> SimulatedSignal`
  returning `(i, q, x_true, true_phase)`.
- Applies the documented pipeline order exactly once, in one place:
  `quadrature_phase_error -> amplitude_imbalance -> dc_offset -> noise -> hysteresis`.
- **Acceptance:** an existing-behaviour test asserting that
  `simulate_condition` reproduces, bit-identically, the arrays the current
  ad-hoc composition produces for at least 3 named conditions.

### P2. Resolve the two-noise-path ambiguity (audit item **B6**)

Audit B6: two parallel noise paths, one misleadingly named, risking **silent double
application** in Week 4. Fix before the runner exists, not after.

- Read `src/hoqi_bench/noise.py` and `forward_model.py`; identify both paths.
- Keep exactly one path reachable from `simulate_condition`; delete or clearly rename the
  other with a docstring stating which is canonical.
- **Acceptance:** a test asserting noise is applied exactly once -- e.g. measured output
  variance matches the single-application prediction and not 2x it.

### P3. Write `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` (per §0.1)

Per-axis, which method the forward model structurally favors, and why. Must be committed
before Day 22. Non-negotiable: this is what separates "Heydemann won" from "Heydemann was
always going to win."

### P4. Pin BLAS threading now

Add to the package's test configuration and (later) the runner: `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`. Determinism under parallelism (Day 24) is
far easier to *preserve* than to retrofit.

### P5. Send the off-critical-path access requests

Email the corresponding authors of Collett & Tee 2014, Collett & Watkins 2015, and Köning
et al. 2014 requesting preprints; file a school-librarian ILL request. 20 minutes.
**Never a blocker** -- anything that arrives before Week 6 improves the Related Work
section; nothing depends on it.

---

## Part 2 -- Week 3: the method zoo (Days 15-21)

### Standing rules for every method day

Binding on Days 15-20 without restatement:

1. **No shared code below `fit()`.** Sharing *above* it (ellipse params -> phase,
   result construction, validation helpers) is expected and fine. This is the operative
   form of §0.2.
2. Every method returns the **result dataclass** from Day 15 -- never a bare array.
3. Every method satisfies `docs/WEEK3_METHOD_CONTRACT.md` §2: on failure, all numeric
   fields NaN, `failed=True`, and a **specific** reason code (`"singular_scatter_matrix"`,
   `"non_convergent"`, `"rejected_ellipse_solution"` -- never a generic `"failed"`).
4. Every method is added to the **Tier 1 exact-oracle test** (§0.3) the same day it lands.
   A method is not "done" until it recovers the generating conic to machine precision on
   noiseless data.
5. Follow `docs/DOCUMENTATION_STANDARD.md`; write `docs/journal/dayNN.md`.
6. **Never silently patch a method's known weakness.** Fitzgibbon's fragility is
   scientifically load-bearing (Day 19). Preserve it and document that it is deliberate.

### Day 15 -- Interface, baseline, and the tautology preregistration

**Objective.** The common interface, the raw-atan2 baseline, and the structural-advantage
predictions.

**Do not spend the day on interface architecture.** All five advisors converged: this is a
dataclass, not a design problem. Design it against Köning's needs (the hardest method) so
Days 16-18's tests are not invalidated by a Day 20 refactor -- but that is a ten-minute
decision, not a day's work.

- **New:** `src/hoqi_bench/methods/__init__.py`, `base.py`, `raw_atan2.py`
- `base.py` defines:
  ```
  @dataclass(frozen=True)
  class FitResult:
      recovered_phase: FloatArray
      failed: bool = False
      reason: str | None = None
      params: dict[str, float] | None = None   # fitted ellipse/conic params
      converged: bool | None = None            # None for non-iterative methods
      n_iter: int | None = None
      covariance: FloatArray | None = None     # Koning only, initially
      runtime_s: float | None = None
  ```
  plus a `PhaseRecoveryMethod` Protocol with `name: str` and
  `fit(i, q, **kwargs) -> FitResult`.
- Implement Method 1: raw `atan2`, no correction. The floor every other method must beat.
- Write `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` (P3).

**Acceptance:** atan2 near-exact on clean data; measurably degrades under injected
distortion; `FitResult` accommodates a hypothetical iterative method without modification.

**Journal:** why a benchmark needs a deliberately naive baseline; what atan2 actually does.

### Day 16 -- Kasa circle fit, and a corrected acceptance criterion

**Objective.** Port Kasa from `quadrature-interferometer-sim` behind the interface.

**The original plan's acceptance criterion is wrong and must not be used as written.** It
demands reproducing "0.0395% displacement RMS error and 0.0019% vibration-frequency error."
Verified: `0.0019%` comes from `detect_vibration_freq` (an FFT on recovered displacement,
`tests/test_phase3.py`) and `0.0395%` from the Phase-2 *end-to-end pipeline*. Neither is a
Kasa output. hoqi-bench's method interface is `(I,Q) -> phase`; it has no FFT vibration
stage. **The criterion tests something this day does not build.**

**Replacement, which is strictly stronger:**

- **(a) Port fidelity (binding).** The ported circle fit must produce **bit-identical**
  center estimates to `fit_circle_center` in
  `/mnt/c/Users/nisha/Desktop/ee-portfolio/quadrature-interferometer-sim/src/analysis.py`
  on identical input. Bit-identity on the actual unit is a far tighter check than a
  percentage match on a downstream composite.
- **(b) End-to-end regression (secondary, non-blocking).** Separately reproduce the
  original project's 0.0395% figure via its own test path, as evidence the published number
  is reproducible. If it does not reproduce, **report it** -- do not fix either project to
  make them agree without flagging it.

Method 2 in hoqi-bench = fit circle center -> subtract center -> `atan2`.

**Journal:** what the circle fit assumes, and precisely why that assumption fails once
Week 2's ellipse distortions are present -- this sets up the whole research question.

### Day 17 -- Heydemann correction

Implement faithfully from `docs/derivations/heydemann.md` (symbolically verified Day 2 via
`scripts/verify_heydemann_derivation.py`). Do **not** substitute an easier ellipse fit.

Inject known amplitude imbalance, quadrature phase error, and DC offsets; verify recovery
to a stated tolerance. Add a degeneracy test (tiny phase excursion, near-circular data, few
samples) verifying **graceful failure with a reason code**, not a throw or silent garbage.

**Mandatory note in the module docstring and journal:** per §0.1, this method inverts
exactly the forward model's own distortion parameterization, so its dominance on classic
axes is structural, not evidential. State it here so it cannot be quietly forgotten at
writeup time.

### Day 18 -- Halir & Flusser

Implement the numerically stable **block-decomposition** formulation -- the entire point of
the paper. Do not implement the naive version.

Validate against synthetic ellipses with known analytic parameters: recovered center,
semi-axes, and tilt must match injected values to near machine precision on well-conditioned
data (this is the Tier 1 oracle). Then re-run Day 3's degenerate cases and confirm this
implementation survives conditioning that broke the naive formulation.

**Journal:** explain the block decomposition intuitively -- what problem it solves, why
splitting the matrix helps numerically.

### Day 19 -- Fitzgibbon **+ external cross-validation (moved up from Day 21)**

**(1)** Implement Fitzgibbon et al. (1999) faithfully, *including its known numerical
fragility*. Preserving that fragility is the point: the Fitzgibbon vs Halir & Flusser
comparison is scientifically meaningful precisely because of it. Module docstring must state
the preservation is deliberate.

**(2) Tier 2 external cross-validation — pulled forward from Day 21 deliberately**, so that
a disagreement has days of debugging headroom rather than hours before a blocking gate.

- `pip install lsq-ellipse==2.2.1 ellipsinator==0.3.0` (both verified available on PyPI).
- Add these as an **optional dev/validation extra**, never a runtime dependency of the
  package.
- Cross-check Halir & Flusser against `lsq-ellipse`, and both Halir & Flusser and Fitzgibbon
  against `ellipsinator`, on identical synthetic data. Expect agreement to ~1e-10 in
  well-conditioned regimes.
- **Known coverage hole, to state plainly rather than paper over:** these packages cover only
  Halir & Flusser and Fitzgibbon -- the two most algebraically similar of the seven. Kasa,
  Heydemann, Taubin, and Köning remain externally uncrossed and rely on the Tier 1 analytic
  oracle. Say this in the writeup.

### Day 20 -- Taubin, Köning, robustness matrix, **and the runtime probe**

**(1) Taubin (Method 6).** Kasa's algebraic circle fit plus a bias correction.

**(2) Köning/Wimmer/Witkovský (Method 7)** -- the highest-risk implementation. Implement the
algorithm *family* as understood from the OEFPIL manual (`notes/koning_2014.md`): an
errors-in-variables fit treating **both** I and Q as noisy, estimated by **iterated Taylor
linearization** with a covariance-weighted (BLUE) update each iteration until convergence --
Gauss-Newton-style, not a single-shot linear solve.

Must be labeled in its docstring as **an implementation of the algorithm family, not a
faithful reproduction of the 2014 paper's specific tuning choices**, since that paper remains
unread (paywalled).

*Optional, off critical path:* `sudo apt install octave`, download `EllipseFit4HC` from the
MathWorks File Exchange (Witkovský's own implementation), and cross-check. If Octave fights
back for more than ~an hour, **abandon it** and keep the labeled-approximation framing -- a
brand-new toolchain on the critical path on Day 20 is how weeks die.

**(3) Robustness matrix.** Every method against adversarial inputs: near-zero phase
excursion, near-perfect circle, very short records (10-50 samples), extreme noise,
all-identical points. Produce a `method x failure-mode x graceful/degraded/crash` matrix.
Every crash must become a graceful failure with a reason code -- a method that throws
mid-sweep would corrupt the Week 4 campaign. **Report the matrix; do not silently "fix" a
method by altering its algorithm.**

**(4) Runtime probe (moved up from Day 26).** Time all 7 methods on a representative
condition. Köning is the only iterative method and plausibly dominates total cost; the
existing "125,650 fits in ~seconds" projection was measured on non-iterative fits only.
Project full-campaign wall-clock now, while there is still time to act on it.

**Stop-and-ask trigger:** if projected campaign runtime exceeds ~12 hours, stop and present
grid-reduction options to Nishi. Per the original plan, he would rather cut resolution than
method count.

### Day 21 -- Cross-validation gate ⚠️ NEVER SKIP

Two tasks, plus -- new -- a defined failure branch.

**(1) Tier 1, the analytic oracle (the foundation, per §0.3).** On noiseless, exactly
generated data, all 7 methods must recover the generating conic / phase to machine
precision, and agree with each other. Any disagreement means one is wrong -- root-cause it.
**Do not average the discrepancy away.**

**(2) Tier 3, the internal falsifiable predictions** already fixed in
`docs/WEEK3_METHOD_CONTRACT.md` §3.2-3.3, tested explicitly, both halves:
- Fitzgibbon ↔ Halir & Flusser **agree** in well-conditioned regimes (a bug if they do not)
  and **diverge** in ill-conditioned ones (a bug if Fitzgibbon does *not* show elevated
  failure/error there, since that would mean Day 3's finding does not generalize).
- Taubin ↔ Kasa agree at low noise and diverge as noise rises, with Taubin's bias correction
  measurably reducing bias.

**(3) The failure branch (new -- per §0.6).** If the gate fails, the following is
pre-committed, so that a failing gate cannot be rationalized into passing under schedule
pressure:

- **Day 21 failing does not permit proceeding to Day 22.** Week 4 slips.
- Root-cause with a written hypothesis before any code change.
- Classify the cause explicitly as (i) implementation error, (ii) a difference in test
  conditions, or (iii) a genuine discrepancy worth reporting. Only (i) is fixed silently;
  (ii) and (iii) are **written up as findings**.
- If unresolved after 2 days, escalate to Nishi with the three candidate causes and a
  recommendation. Do not quietly widen the tolerance until it passes -- widening the
  tolerance **is** the failure mode this gate exists to prevent.

**Note on scope, recorded as a deviation.** The original plan's Day 21 second task --
"reproduce a qualitative result from the published comparison literature" -- is **not
executable as written**: every comparison paper is paywalled and was read only at abstract
level, and conditions cannot be replicated from an abstract. It is replaced by the
three-tier structure above (analytic oracle → external packages → internal falsifiable
predictions). This is recorded as a dated deviation in
`docs/WEEK3_METHOD_CONTRACT.md`. If a preprint arrives from Part 1's P5 requests, the
original check is added retroactively as a bonus.

---

## Part 3 -- Week 4: harness, metrics, campaign (Days 22-28)

### Day 22 -- Core metrics **+ the survivorship-bias fix**

Displacement RMSE, peak absolute error, per-fit runtime. Each needs a test against a
**hand-computed** reference whose arithmetic is shown in the test's comments.

Any error computed on recovered **phase** must use `hoqi_bench.metrics.wrapped_phase_error`
(contract §1) -- do not re-derive the wrapping.

Aggregation layer collapsing 50 seeds into mean/median/std/percentiles, tested on a known
distribution.

**Binding addition, per §0.4 -- this is the day the survivorship-bias fix lands:**
- Every aggregate reports **convergence rate alongside error**, never error alone.
- A method is **not ranked** on any condition where any method's failure rate exceeds a
  threshold fixed today, before results exist.
- Record as an extension to `docs/WEEK3_METHOD_CONTRACT.md` §2.

**Also today, per §0.6 (Outsider):** define the **physical reference scale**. State what
displacement error actually matters for a real HoQI application, with a citation to Lehmann
et al. 2025's reported performance where possible. Without this, the campaign yields a
ranking with no actionable meaning.

### Day 23 -- Cyclic-error harmonics

Recover first- and second-order periodic error amplitudes in the recovered-phase residual --
the standard figure of merit in interferometry nonlinearity work, and what makes results
comparable to published literature.

Validate by injecting a **known** cyclic error of known amplitude at a known harmonic.
Test several amplitudes, both harmonics, plus a **null case** (no cyclic error must yield
~zero, not a spurious peak). Consult arXiv:2207.03488 for conventions.

### Day 24 -- Sweep runner **+ smoke campaign (moved up from Day 26)**

Requirements: takes the grid from the config (never hardcoded); runs every
`(method x condition x seed)`; writes Parquet **incrementally** so a crash loses nothing;
fully **resumable**; **deterministic**; parallelized.

**Determinism under parallelism -- the highest-risk engineering item in Week 4.** Concrete
approach, not aspiration:
- Pin `OMP_NUM_THREADS=1` / `OPENBLAS_NUM_THREADS=1` / `MKL_NUM_THREADS=1` **inside each
  worker process** (P4 sets this up).
- Parallelize at the **condition** level so workers never share mutable state.
- Derive every seed via the existing `hoqi_bench.seeds.derive_seed(...)`, which already
  gives paired seeds across methods -- do **not** invent a second seeding path.
- Result ordering must be normalized before writing, so worker completion order cannot
  affect output bytes.

**Two mandatory tests** (a silently non-reproducible sweep invalidates the entire study):
- **Determinism:** run twice, compare byte-for-byte.
- **Resumability:** kill mid-run, restart, verify the final output matches an uninterrupted
  run exactly.

**Smoke campaign today, not Day 26:** tiny grid (2 methods x 3 conditions x 5 seeds)
end-to-end, `config -> sweep -> metrics -> aggregated statistics`, verifying data flows and
exact reproducibility from a fixed seed. Finding a pipeline break here leaves days of
headroom.

### Day 25 -- Statistics layer

Implement **exactly** per `docs/PREREGISTRATION.md`: bootstrap CIs (percentile method),
breakdown-threshold detection (interpolated between grid points, not reported at grid
resolution), and pairwise comparison with the preregistered Bonferroni family of **21
pairwise comparisons per condition** (not a global 337-condition correction).

Test breakdown detection against synthetic error curves with **known** crossing points.

**Hard rule:** do **not** add any statistical test that was not preregistered. If something
appears missing, **flag it for Nishi's decision** rather than adding it.

### Day 26 -- Reproducibility hardening (repurposed)

The smoke test and runtime probe have moved earlier, so this day is repurposed to attack
audit item **B5** -- reproducibility is *the stated contribution* and is currently
unevidenced. Per §0.6 this is the highest-leverage day in Week 4.

- **Multi-OS CI matrix:** extend `.github/workflows/ci.yml` to Linux + macOS + Windows.
- **Fresh-clone job (audit item C6):** clone from scratch, install, run the smoke campaign,
  assert results match committed expected hashes.
- **Cross-platform determinism:** assert the smoke campaign produces identical result hashes
  across all three OSes. If it does not, that is itself a finding worth documenting -- and
  far better found now than in Week 6.
- Pin dependency versions and record the resolved environment.

**Stop-and-ask trigger:** if cross-OS hashes differ and the cause is BLAS-level, present the
options to Nishi (pin a BLAS, relax to tolerance-based comparison, or document the platform
dependence as a finding) rather than silently choosing.

### Day 27 -- Launch main campaign

**Pre-flight, all blocking:**
1. Verify the configured grid matches `docs/PREREGISTRATION.md` **exactly**
   (`tests/test_docs_consistency.py` already does part of this). Report any discrepancy and
   **do not proceed if they differ.**
2. Verify `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` (P3) is committed and timestamped
   *before* any result exists.
3. Verify Day 24's determinism and resumability tests still pass.

Then launch, with progress logging and incremental writes. While it runs, build a quick-look
script plotting partial results so anything obviously broken surfaces early.

### Day 28 -- RQ1 + RQ2 analysis

RQ1: comparative ranking across every classic non-ideality on displacement RMSE, cyclic-error
harmonics, runtime, and failure rate, with CIs. RQ2: breakdown thresholds per method per
condition.

**Framing constraints, binding:**
- **Report the §0.1 tautology explicitly.** Heydemann's dominance on classic axes is
  structural. Compare against `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` and say which
  results were predicted by construction versus genuinely informative.
- Report **failure rate beside every error number** (§0.4).
- Be explicit about which differences are statistically distinguishable and which fall
  within overlapping CIs -- **this distinction is where benchmark papers most often
  overclaim.**
- Interpretation labeled **DRAFT INTERPRETATION** for Nishi to revise, not rubber-stamp.
- Flag anything surprising separately so Nishi can judge finding vs. bug.

---

## Part 4 -- Decision points that need Nishi (not the executing model)

| When | Decision |
|---|---|
| Day 20 | If projected runtime > ~12 hours: which grid reductions (he prefers cutting resolution over method count) |
| Day 20 | Whether to spend time installing Octave for the Köning cross-check, or accept the labeled-approximation framing |
| Day 21 | If the gate fails and is unresolved after 2 days: which of the three candidate causes to pursue |
| Day 25 | Any statistical test that appears needed but was not preregistered |
| Day 26 | If cross-OS result hashes differ at BLAS level: pin, relax, or document as a finding |
| Day 28 | Review and revise every DRAFT INTERPRETATION |

## Part 5 -- Notes for the executing model

- **Read `docs/WEEK3_METHOD_CONTRACT.md` before writing any method.** It is binding and
  pre-dates every result.
- The standing rules in Part 2 apply to every method day without restatement.
- When a day's acceptance criterion cannot be met, **stop and report** -- do not widen a
  tolerance, skip an assertion, or fix a comparison target to make a check pass. Weeks 1-2's
  audit found 11 defects behind a green suite precisely because green is not the goal.
- Commit per day with the day's journal entry. Keep ruff + mypy --strict clean.
- Any deviation from this plan gets recorded here, dated, with its reason.
