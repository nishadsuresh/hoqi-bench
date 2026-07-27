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

**Status:** Weeks 1-2 of 6 complete (Days 0-14 of a 42-day build plan), plus a same-day adversarial
audit and remediation before Week 3 begins (`docs/WEEK1-2_AUDIT.md`). The audit found 11 code-verified
defects behind an initially-green test suite -- most seriously, the hysteresis transform derived
direction-of-travel from the noisy measured signal rather than ground truth, and the preregistered
parameter space omitted axes (`arc_fraction`, `hysteresis_magnitude`, `photon_scale`,
`samples_per_fit`) that RQ3/RQ4/RQ6 needed to be answerable at all. All 11 are fixed; the
preregistration was superseded and re-registered as v2 (`docs/PREREGISTRATION.md`,
`docs/PREREGISTRATION_v1_superseded.md`) while the project was still pre-data, per a second
adversarial llm-council review's recommendation. The full composable forward model (all 7
distortion classes from the classic Heydemann parameters through direction-dependent hysteresis),
the config-to-run resolver, seed-pairing discipline, and the Week 3 method contract are implemented
and validated (75/75 tests passing). Method implementations (Kasa, Heydemann, Halir & Flusser,
Fitzgibbon, Taubin, Köning/Wimmer/Witkovský) begin Week 3, against `docs/WEEK3_METHOD_CONTRACT.md`'s
pre-written pass criteria.

**Open items, not yet resolved**: 10+ commits are not yet pushed to GitHub (a `workflow` OAuth scope
issue); the preregistration needs an external OSF/Zenodo timestamp before Week 4's campaign launches,
since a document in a repository the author controls is a note to self until an external party
holds a timestamp on it.

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
  metrics.py              # wrapped_phase_error(): circular-statistics phase-error metric
  _types.py               # shared type aliases
tests/                 # pytest suite (75 tests)
scripts/               # standalone exploratory/verification scripts
configs/               # sweep configuration TOML files
docs/
  DOCUMENTATION_STANDARD.md            # the 7 rules every module follows
  PREREGISTRATION.md                   # v2: committed research questions, parameters, protocol
  PREREGISTRATION_v1_superseded.md     # v1, superseded same-day -- kept verbatim, with postmortem
  WEEK1-2_AUDIT.md                     # the Weeks 1-2 adversarial audit that drove the v2 revision
  WEEK3_METHOD_CONTRACT.md             # pre-Week-3 contract: circular stats, fit-failure, Day 21 gate
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
- **The preregistration has no external timestamp yet.** A document in a repository the author
  controls, with a rewritable history, is not independently verifiable as pre-dating the campaign --
  an OSF preregistration or Zenodo DOI is needed before Week 4, and is not yet in place.
- **10+ commits are not yet pushed to GitHub** (a `workflow` OAuth scope issue) -- there is currently
  no external record of most of this work, the preregistration included.

## References

See `refs/references.bib` for the full, verified bibliography and `notes/` for per-paper reading
notes (each marked by actual access level — primary full-text read vs. secondary/abstract-level).
