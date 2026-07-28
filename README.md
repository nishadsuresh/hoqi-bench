# hoqi-bench

**Nishad Suresh**

## Abstract

This project is an open, reproducible benchmark for phase-recovery and nonlinearity-correction
methods in homodyne quadrature interferometry (HoQI). Comparisons of ellipse-fitting methods for
interferometry already exist in the literature (see `notes/related_work_table.md`), and Heydemann's
correction dates to 1981 — this project does not claim to be the first comparison of these methods.
The actual contribution is twofold: (a) reproducibility infrastructure — an open, installable
benchmark implementing seven major methods (raw atan2, Kasa, Heydemann, Halir & Flusser, Fitzgibbon,
Taubin, and Köning/Wimmer/Witkovský's errors-in-variables fit) under one roof on a common,
controlled, preregistered parameter space, which does not currently exist; and (b) extension to the
newer nonlinearity classes (power-law residual scaling, direction-dependent hysteresis) described by
Lehmann et al. 2025, which the classic static-fitting literature predates. This is a simulation
study — no real HoQI hardware, no external peer review before release.

**Status:** Weeks 1-3 of 6 complete (Days 0-21 of a 42-day build plan). The full composable
forward model (all 7 distortion classes, from the classic Heydemann parameters through
direction-dependent hysteresis), the config-to-run resolver, seed-pairing discipline, all **seven
phase-recovery methods**, and Day 21's cross-validation gate are implemented and validated
(136 tests passing, `ruff` and `mypy --strict` clean, CI green on Python 3.10 and 3.11). The
preregistration is externally timestamped on OSF (https://osf.io/qyw6t, 2026-07-27). Week 4 --
metrics, the sweep harness, and the 125,650-run main campaign -- is next; no campaign data exists
yet.

Two adversarial reviews and one gate have shaped the work so far, and each is documented with what
it actually found rather than as a process box ticked:

- **Weeks 1-2 audit** (`docs/WEEK1-2_AUDIT.md`) found 11 code-verified defects behind an
  initially-green test suite -- most seriously, the hysteresis transform derived direction-of-travel
  from the noisy measured signal rather than ground truth, and the preregistered parameter space
  omitted axes (`arc_fraction`, `hysteresis_magnitude`, `photon_scale`, `samples_per_fit`) that
  RQ3/RQ4/RQ6 needed to be answerable at all. All 11 fixed; the preregistration was superseded and
  re-registered as v2 while still pre-data.
- **A 5-advisor adversarial review of the Weeks 3-4 plan** (`docs/WEEK3-4_PLAN.md` Part 0) named a
  circularity threat the draft had missed: the forward model IS algebraically Heydemann's own
  distortion model, so Heydemann's dominance on the classic axes is guaranteed by construction, not
  a finding. `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` was written before any method existed to fix
  which results are tautological in advance of seeing them.
- **Day 21's cross-validation gate** (`docs/journal/day21.md`) did not pass on its first run. It
  traced a sampling-convention defect in the forward model that gave one method a `1/N` error floor
  on the *noiseless* condition -- which would have published a clean, entirely artifactual
  "error falls as 1/N" curve onto a preregistered research question -- plus a gate criterion that
  stated one of the project's own prior findings backwards, a journal finding that no longer
  reproduces, and a preregistered predictions document that contradicted its own implementation.
  All four are fixed or retracted, with dated deviations.

**Open items:** none blocking. Week 3's review (`docs/WEEK3_REVIEW.md`) records one finding that
Week 4 must act on rather than resolve: the preregistered per-method failure rate measures whether a
method *detects* its own failure, not whether it failed, so a gross-error rate must be reported
alongside it (`docs/WEEK3_METHOD_CONTRACT.md` §2.1).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -v                              # full test suite
ruff check src/ tests/                 # lint
mypy                                   # strict type checking
python scripts/verify_heydemann_derivation.py    # symbolic derivation check
python scripts/explore_ellipse_constraints.py    # Fitzgibbon vs Halir & Flusser study
```

## Project structure

```
src/hoqi_bench/        # the installable package
  config.py            # TOML sweep-config schema, validation, total_runs(), REQUIRED_MODEL_PARAMS
  forward_model.py     # ideal (distortion-free) interferometer, ported and verified
  pipeline.py           # composable transform architecture (apply_pipeline, Transform type)
  transforms.py         # amplitude imbalance, quadrature phase error, DC offset, hysteresis
  noise.py               # Gaussian and Poisson (signal-dependent) detector noise
  power_law.py           # power-law exponent characterization for RQ3
  arc.py                 # arc_fraction displacement-ramp generator
  resolve.py              # config -> per-condition run manifest, fraction-to-absolute conversion
  seeds.py                # derive_seed(): structurally-paired seed derivation across methods
  simulate.py             # simulate_condition(): the single canonical condition -> (I, Q) path
  metrics.py              # wrapped_phase_error(): circular-statistics phase-error metric
  _types.py               # shared type aliases
  methods/                # the seven phase-recovery methods, behind one common interface
    base.py               #   FitResult, PhaseRecoveryMethod, failed_result, timed_fit
    __init__.py           #   METHOD_REGISTRY (name -> fit) and fit_by_name
    _ellipse.py           #   shared POST-fit machinery only (conic -> phase); never a fit itself
    raw_atan2.py          #   Method 1 -- the deliberately naive baseline
    kasa.py               #   Method 2 -- Kasa (1976) algebraic circle fit
    heydemann.py          #   Method 3 -- Heydemann (1981), via second-order moments
    halir_flusser.py      #   Method 4 -- Halir & Flusser (1998) block-decomposed ellipse fit
    fitzgibbon.py         #   Method 5 -- Fitzgibbon (1999), fragility deliberately preserved
    taubin.py             #   Method 6 -- Taubin (1991) bias-corrected circle fit
    koning_wimmer_witkovsky.py  # Method 7 -- errors-in-variables, iterated Sampson reweighting
tests/                 # pytest suite (136 tests)
scripts/               # standalone exploratory/verification scripts
configs/               # sweep configuration TOML files
docs/
  DOCUMENTATION_STANDARD.md            # the 7 rules every module follows
  PREREGISTRATION.md                   # v2: committed research questions, parameters, protocol
  PREREGISTRATION_v1_superseded.md     # v1, superseded same-day -- kept verbatim, with postmortem
  WEEK1-2_AUDIT.md                     # the Weeks 1-2 adversarial audit that drove the v2 revision
  WEEK3_METHOD_CONTRACT.md             # pre-Week-3 contract: circular stats, fit-failure, Day 21 gate
  WEEK3-4_PLAN.md                      # Weeks 3-4 plan, adversarially reviewed pre-implementation
  WEEK3_REVIEW.md                      # the Week 3 review: what Day 21's gate and a full re-read found
  STRUCTURAL_ADVANTAGE_PREDICTIONS.md  # which results are tautological, fixed before any method existed
  experimental_design.md               # the approved, expanded sweep design (+ v2 addendum)
  derivations/heydemann.md             # from-scratch, symbolically-verified derivation
  forward_model_validation_summary.md  # Week 2 close-out: every distortion class, test, property
  journal/                             # dayNN.md, one per day of the build plan
notes/                 # per-paper reading notes, related-work table, contribution claim
refs/references.bib     # verified bibliography
```

## Methodology

Every module follows `docs/DOCUMENTATION_STANDARD.md` (module docstrings, equation provenance,
design-decision and failure-mode notes) and the TDD / numeric-verification discipline documented in
`04-resources/numeric-verification-methodology.md` of the author's broader research notes: numeric
checks over visual, unit tests in isolation before integration, and re-running the exact
previously-failing case plus everything already passing after any fix.

The full research plan — preregistered research questions, parameter space, metrics, and
statistical protocol — is in `docs/PREREGISTRATION.md` (v2), which documents two rounds of
adversarial review: the original 5-advisor llm-council review before any data collection (preserved
in `docs/PREREGISTRATION_v1_superseded.md`), and a second Weeks 1-2 audit + llm-council review
(`docs/WEEK1-2_AUDIT.md`) that found the first version committed to research questions its own
config file couldn't execute, and led to the v2 revision -- both done, per this project's own
preregistration discipline, before Week 3 began and before any campaign data existed.

## Honest limitations (see `docs/PREREGISTRATION.md`, `docs/WEEK1-2_AUDIT.md`, and `docs/journal/` for full detail)

- **Simulation only.** No real HoQI hardware, no real bench data, no external peer review before
  release.
- **Three parameter ranges are engineering judgment, not literature-derived** (quadrature phase
  error, DC offset, and, new in v2, hysteresis magnitude/photon_scale/samples_per_fit's specific
  grid points) — explicitly flagged as such throughout, not disguised as paper-grounded numbers.
- **One required method (Köning/Wimmer/Witkovský) is implemented from the general algorithm family
  it belongs to** (errors-in-variables estimation via iterated Taylor linearization, per the CRAN
  `OEFPIL` package this method generalizes into), not from the original 2014 paper's own text, which
  remains paywalled and unread.
- **Cross-validation against external implementations covers only two of the seven methods.**
  `lsq-ellipse` and `ellipsinator` cover Halir & Flusser and Fitzgibbon -- the two most algebraically
  similar of the set. Kasa, Heydemann, Taubin and Köning are checked only against this project's own
  analytic oracle (exact recovery of a known generating ellipse, `tests/test_cross_validation_gate.py`),
  which is a genuine independent reference but not an independent *implementation*.
- **Seven implementations by one author are not seven independent samples.** Agreement between the
  methods is weak evidence of correctness however many of them agree, since correlated authorship
  error survives duplication perfectly. This is why the validation weight sits on external and
  analytic oracles rather than on method agreement -- stated here rather than left for a reader to
  notice (`docs/WEEK3-4_PLAN.md` §0.2).
- **Per-method failure rates are not directly comparable across methods.** The `failed` flag records
  whether a method detects its own failure; only some of the seven carry a self-consistency check.
  Reported with a gross-error rate alongside it for exactly this reason
  (`docs/WEEK3_METHOD_CONTRACT.md` §2.1).

## References

See `refs/references.bib` for the full, verified bibliography and `notes/` for per-paper reading
notes (each marked by actual access level — primary full-text read vs. secondary/abstract-level).
