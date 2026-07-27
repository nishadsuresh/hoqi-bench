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

**Status:** Week 2 of 6 complete (Days 0-14 of a 42-day build plan). Documentation standard,
literature review, experimental design, and preregistration all done and adversarially reviewed;
the full composable forward model (all 7 distortion classes from the classic Heydemann parameters
through direction-dependent hysteresis) implemented and validated (47/47 tests passing). Method
implementations (Kasa, Heydemann, Halir & Flusser, Fitzgibbon, Taubin, Köning/Wimmer/Witkovský)
begin Week 3.

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
  config.py            # TOML sweep-config schema, validation, total_runs()
  forward_model.py     # ideal (distortion-free) interferometer, ported and verified
  pipeline.py           # composable transform architecture (apply_pipeline, Transform type)
  transforms.py         # amplitude imbalance, quadrature phase error, DC offset, hysteresis
  noise.py               # Gaussian and Poisson (signal-dependent) detector noise
  power_law.py           # power-law exponent characterization for RQ3
  _types.py               # shared type aliases
tests/                 # pytest suite (47 tests)
scripts/               # standalone exploratory/verification scripts
configs/               # sweep configuration TOML files
docs/
  DOCUMENTATION_STANDARD.md            # the 7 rules every module follows
  PREREGISTRATION.md                   # committed research questions, parameters, protocol
  experimental_design.md               # the approved, expanded sweep design
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
statistical protocol — is in `docs/PREREGISTRATION.md`, which itself documents a full adversarial
review pass (5 independent critiques, cross-peer-reviewed, synthesized) run against it before any
data collection, per the project's own preregistration discipline.

## Honest limitations (see `docs/PREREGISTRATION.md` and `docs/journal/` for full detail)

- **Simulation only.** No real HoQI hardware, no real bench data, no external peer review before
  release.
- **Two parameter ranges are engineering judgment, not literature-derived** (quadrature phase error,
  DC offset) — explicitly flagged as such throughout, not disguised as paper-grounded numbers.
- **One required method (Köning/Wimmer/Witkovský) is implemented from the general algorithm family
  it belongs to** (errors-in-variables estimation via iterated Taylor linearization, per the CRAN
  `OEFPIL` package this method generalizes into), not from the original 2014 paper's own text, which
  remains paywalled and unread.

## References

See `refs/references.bib` for the full, verified bibliography and `notes/` for per-paper reading
notes (each marked by actual access level — primary full-text read vs. secondary/abstract-level).
