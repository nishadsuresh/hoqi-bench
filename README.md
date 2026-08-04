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
controlled, preregistered parameter space, which does not currently exist; and (b) a partial
extension to the newer nonlinearity classes (power-law residual scaling, direction-dependent
hysteresis) described by Lehmann et al. 2025 — the preregistered campaign turned out to test only
one of these two mechanisms as originally intended, see "What this benchmark does NOT answer,"
below. This is a simulation study — no real HoQI hardware, no external peer review before release.

**Status (2026-07-29): Weeks 1-5 of 6 complete (Days 0-36 of a 42-day build plan).** The full
composable forward model, all **seven phase-recovery methods**, the 125,650-fit main campaign, and
every preregistered research question (RQ1-RQ6) have been run and analyzed —
`docs/RQ1_RQ2_ANALYSIS.md` and `docs/RQ3_RQ6_ANALYSIS.md`, both marked DRAFT pending the author's
own review. 251 tests passing (249 pass outright, 2 `xfail` documenting known, dated,
intentionally-unfixed preregistration limitations — see below), `ruff` and `mypy --strict` clean,
CI green on a 3-OS × 2-Python reproducibility matrix. The preregistration is externally timestamped
on OSF (https://osf.io/qyw6t, 2026-07-27; a pending amendment covers deviations D5-D7, added
2026-07-29). Week 6 (packaging, PyPI, Zenodo DOI) is in progress.

## Development & AI Assistance

This is a self-directed project. I chose the topic, defined the research
question and scope, made the design decisions, and evaluated the results.
AI assistance (Anthropic's Claude) was used to structure the implementation
and write the code. I directed the work and assessed the output; I did not
write the implementation line by line.

This disclosure was added on 2026-08-03 to accurately describe how the
project was built.


## What this benchmark does NOT answer

**Stated here, prominently, not as a footnote** — a project whose stated contribution is
reproducibility infrastructure should say plainly where its own preregistered campaign fell short,
where it did:

- **The preregistered campaign does not test direction-dependent hysteresis**, despite
  `hysteresis_magnitude` being a preregistered axis. Every campaign waveform is a monotonic ramp, so
  the direction-of-travel mechanism the axis is named for is never exercised — the preregistered
  data measures a real but different effect (direction-*independent* radial inflation). A
  supplementary experiment with an actual bidirectional waveform, run after the fact under a
  protocol committed before any of its code existed, found real direction-dependence in several
  methods — reported as supplementary evidence, not preregistered, in `docs/RQ3_RQ6_ANALYSIS.md`.
- **RQ6 (an N-vs-noise design chart) is not answerable from the preregistered grid** — the
  `samples_per_fit` and `noise_std` axes were swept independently, never together. Answered instead
  by a supplementary interaction grid, reported separately.
- **RQ5 covers only the sub-fringe regime** (a 0.72° arc up to exactly one full fringe cycle) —
  `arc_fraction`'s preregistered range never reaches the "many-fringe" regime its own research
  question names.
- **No Poisson-vs-Gaussian ranking difference was found to be statistically real.** Apparent
  differences between the two noise models did not survive a proper significance check against
  seed-to-seed sampling noise, under any of three independently-reasoned equivalence definitions.

Every one of these is recorded as a dated, reasoned deviation in `docs/PREREGISTRATION.md`
(D5, D6, D7) — found by a dedicated pre-flight audit (`docs/WEEK5_PREFLIGHT_AUDIT.md`) before Week 5
began, not discovered by an outside reader after the fact.

## Key results, at a glance (full detail and caveats in the RQ analysis docs)

- **RQ1/RQ2**: on the classic Heydemann distortion axes, the general-conic fitters win by algebraic
  construction, not merit (`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`) — reported as a construction
  check. The genuine finding: at extreme low arc coverage (`arc_fraction=0.02`), reliability
  **inverts completely** — the four methods that dominate every classic-distortion axis become
  unusable, and the two circle-only methods (Kasa, Taubin) remain accurate.
- **RQ3**: this project's own sweep data does not reproduce Lehmann et al. 2025's power-law
  exponent (~3) on any axis tested; where a clean power-law relationship exists at all, it lands
  near exponent 1. Direction-dependent hysteresis is real (supplementary result, see above).
- **RQ4**: no statistically significant Poisson-vs-Gaussian ranking difference found.
- **RQ5**: Heydemann requires a full revolution as a hard, all-or-nothing threshold (100% unusable
  at every sub-fringe point, 0% at exactly one full cycle) — not a gradual degradation the way
  every other method shows.
- **RQ6**: `samples_per_fit` has far less influence over whether a method meets the preregistered
  accuracy tolerance than which method is used or how much noise is present.

## Setup

```bash
uv venv .venv --python 3.10
uv pip install -e ".[dev,validation]" --python .venv/bin/python

.venv/bin/pytest -q                                # full test suite
.venv/bin/ruff check src/ tests/ scripts/           # lint
.venv/bin/mypy                                      # strict type checking
.venv/bin/python scripts/verify_heydemann_derivation.py    # symbolic derivation check
.venv/bin/python scripts/explore_ellipse_constraints.py    # Fitzgibbon vs Halir & Flusser study
```

`uv` (https://docs.astral.sh/uv/) is used here rather than the stdlib `venv` module because plain
`python -m venv` fails on at least one of this project's own development machines
(`python3.10-venv` not installed system-wide) — `uv venv` has no such dependency and is verified
working end-to-end (Day 35's clean-clone reproduction check, `docs/journal/day35.md`). If `python -m
venv .venv && source .venv/bin/activate && pip install -e ".[dev,validation]"` already works in your
environment, that is equally correct and produces an identical installation — `uv` is a
reproducibility fallback here, not a hard dependency of the package itself.

`.[validation]` is optional (`lsq-ellipse`, `ellipsinator` — external cross-validation for two of
the seven methods, `tests/test_external_cross_validation.py`); omit it and that one test file's
tests are skipped rather than failing.

## Project structure

```
src/hoqi_bench/                # the installable package
  config.py                    # TOML sweep-config schema, validation, total_runs(), REQUIRED_MODEL_PARAMS
  resolve.py                   # config -> per-condition run manifest, fraction-to-absolute conversion
  seeds.py                     # derive_seed(): structurally-paired seed derivation across methods
  forward_model.py             # ideal (distortion-free) interferometer, ported and verified
  pipeline.py                  # composable transform architecture (apply_pipeline, Transform type)
  transforms.py                # amplitude imbalance, quadrature phase error, DC offset, hysteresis
  noise.py                     # Gaussian and Poisson (signal-dependent) detector noise
  arc.py                       # arc_fraction displacement-ramp generator (monotonic)
  waveforms.py                 # bidirectional (triangle-wave) generator, Week 5's supplementary RQ3 fix
  simulate.py                  # simulate_condition(): the single canonical condition -> (I, Q) path
  power_law.py                 # power-law exponent characterization for RQ3
  fisher_information.py        # closed-form Fisher information / CRB, for RQ4's noise-matching
  metrics.py                   # wrapped_phase_error(): circular-statistics phase-error metric
  harmonics.py                 # cyclic-error harmonic amplitudes (least-squares, not FFT)
  aggregate.py                 # per-(method,condition) summaries, fit-failure contract, rankability
  reference_scale.py           # physical reference bands, PREREGISTERED_TOLERANCE_M
  statistics.py                # bootstrap CIs, three-outcome breakdown thresholds, paired significance
  runner.py                    # incremental/resumable/deterministic/parallel sweep runner
  _types.py                    # shared type aliases
  methods/                     # the seven phase-recovery methods, behind one common interface
    base.py                    #   FitResult, PhaseRecoveryMethod, failed_result, timed_fit
    __init__.py                #   METHOD_REGISTRY, fit_by_name, timed_fit_by_name
    _ellipse.py                #   shared POST-fit machinery only (conic -> phase); never a fit itself
    raw_atan2.py                #   Method 1 -- the deliberately naive baseline
    kasa.py                     #   Method 2 -- Kasa (1976) algebraic circle fit
    heydemann.py                #   Method 3 -- Heydemann (1981), via second-order moments
    halir_flusser.py            #   Method 4 -- Halir & Flusser (1998) block-decomposed ellipse fit
    fitzgibbon.py                #   Method 5 -- Fitzgibbon (1999), fragility deliberately preserved
    taubin.py                    #   Method 6 -- Taubin (1991) bias-corrected circle fit
    koning_wimmer_witkovsky.py   # Method 7 -- errors-in-variables, iterated Sampson reweighting
tests/                 # pytest suite (251 tests)
scripts/               # campaign runner, per-RQ analysis scripts, standalone verification scripts
configs/
  main_campaign.toml               # the preregistered 359-condition / 125,650-fit campaign
  smoke.toml                       # tiny config for CI/dev iteration
  supplementary_hysteresis.toml    # Week 5: bidirectional-waveform RQ3 supplementary grid
  supplementary_n_x_noise.toml     # Week 5: samples_per_fit x noise_std RQ6 supplementary grid
docs/
  DOCUMENTATION_STANDARD.md            # the 7 rules every module follows
  PREREGISTRATION.md                   # v2 + deviations D1-D7: committed questions, parameters, protocol
  PREREGISTRATION_v1_superseded.md     # v1, superseded same-day -- kept verbatim, with postmortem
  SUPPLEMENTARY_PROTOCOLS.md           # Week 5 supplementary-experiment protocols, committed pre-code
  WEEK1-2_AUDIT.md, WEEK3_REVIEW.md, WEEK5_PREFLIGHT_AUDIT.md, WEEK6_DOC_AUDIT.md
                                        # adversarial/self audits, each with what it actually found
  WEEK3_METHOD_CONTRACT.md             # circular stats, fit-failure contract, Day 21 gate criteria
  WEEK3-4_PLAN.md, WEEK4_EXECUTION_PLAN.md, WEEK5-6_EXECUTION_PLAN.md
                                        # the plan documents each week executed against
  STRUCTURAL_ADVANTAGE_PREDICTIONS.md  # which results are tautological, fixed before any method existed
  RQ1_RQ2_ANALYSIS.md, RQ3_RQ6_ANALYSIS.md  # DRAFT interpretations of the full campaign, per RQ
  experimental_design.md               # the approved, expanded sweep design (+ v2 addendum)
  derivations/heydemann.md             # from-scratch, symbolically-verified derivation
  forward_model_validation_summary.md  # Week 2 close-out: every distortion class, test, property
  journal/                             # dayNN.md, one per day of the build plan
notes/                 # per-paper reading notes, related-work table, contribution claim
refs/references.bib     # verified bibliography
results/                # committed: aggregated summaries, per-RQ analysis CSVs (raw per-seed
                         # Parquet output is gitignored -- fully regenerable from the committed
                         # config, pinned dependencies, and this package's source)
```

## Methodology

Every module follows `docs/DOCUMENTATION_STANDARD.md` (module docstrings, equation provenance,
design-decision and failure-mode notes) and a numeric-verification discipline: numeric checks over
visual, unit tests in isolation before integration, and re-running the exact previously-failing case
plus everything already passing after any fix.

The full research plan — preregistered research questions, parameter space, metrics, and
statistical protocol — is in `docs/PREREGISTRATION.md` (v2 + deviations D1-D7), which documents
three rounds of adversarial review before and during the campaign: the original 5-advisor
`llm-council` review before any data collection (preserved in
`docs/PREREGISTRATION_v1_superseded.md`); a Weeks 1-2 audit + second council review
(`docs/WEEK1-2_AUDIT.md`) that found the first version committed to research questions its own
config file couldn't execute, driving the v2 revision, done pre-data; and a Week 5 pre-flight audit
(`docs/WEEK5_PREFLIGHT_AUDIT.md`) that found four further defects in the *completed* main campaign
after Week 4 closed, each resolved by a dated deviation and, where possible, a protocol-committed
supplementary experiment rather than silently re-running the preregistered grid.

## Honest limitations (see `docs/PREREGISTRATION.md`, audit docs, and `docs/journal/` for full detail)

- **Simulation only.** No real HoQI hardware, no real bench data, no external peer review before
  release.
- **Four preregistered research questions required a supplementary fix after the main campaign
  completed** — see "What this benchmark does NOT answer," above, and deviations D5-D7.
- **Three parameter ranges are engineering judgment, not literature-derived** (quadrature phase
  error, DC offset, and hysteresis magnitude/photon_scale/samples_per_fit's specific grid points) —
  explicitly flagged as such throughout, not disguised as paper-grounded numbers.
- **One required method (Köning/Wimmer/Witkovský) is implemented from the general algorithm family
  it belongs to** (errors-in-variables estimation via iterated Taylor linearization, per the CRAN
  `OEFPIL` package this method generalizes into), not from the original 2014 paper's own text, which
  remains paywalled and unread.
- **Cross-validation against external implementations covers only two of the seven methods.**
  `lsq-ellipse` and `ellipsinator` cover Halir & Flusser and Fitzgibbon -- the two most algebraically
  similar of the set. Kasa, Heydemann, Taubin and Köning are checked only against this project's own
  analytic oracle (exact recovery of a known generating ellipse), which is a genuine independent
  reference but not an independent *implementation*.
- **Seven implementations by one author are not seven independent samples.** Agreement between the
  methods is weak evidence of correctness however many of them agree, since correlated authorship
  error survives duplication perfectly. Validation weight sits on external and analytic oracles
  rather than on method agreement.
- **Per-method failure rates are not directly comparable across methods.** The `failed` flag records
  whether a method detects its own failure, not whether it failed; reported with a gross-error rate
  alongside it for exactly this reason (`docs/WEEK3_METHOD_CONTRACT.md` §2.1) — the preregistered
  failure-rate metric, read alone, was found to invert the true reliability ranking (Week 3 review).
- **No platform holds a byte-exact reproducibility guarantee, including against itself.** Verified
  directly (Day 26): the same machine, same OS label, produced three different hashes across
  separate CI runs. The reproducibility claim is numeric-tolerance (`rtol=1e-9`, `atol=1e-15`),
  checked on Linux, macOS, and Windows — not byte-exact anywhere.

## References

See `refs/references.bib` for the full, verified bibliography and `notes/` for per-paper reading
notes (each marked by actual access level — primary full-text read vs. secondary/abstract-level).
