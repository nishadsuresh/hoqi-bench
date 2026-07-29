# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

Weeks 1-6 of the 42-day build. Not yet released to PyPI (Day 40) or archived with a Zenodo DOI
(Day 41) as of this entry.

### Added

- Seven phase-recovery methods: raw atan2, Kasa, Heydemann, Halir & Flusser, Fitzgibbon, Taubin,
  Köning/Wimmer/Witkovský, behind a common `fit_by_name` interface.
- A composable forward model (`amplitude_ratio`, `quadrature_error_rad`, `dc_offset`, `arc_fraction`,
  Gaussian and Poisson noise, hysteresis, power-law residual scaling).
- A preregistered, OSF-timestamped (v2, https://osf.io/qyw6t) 359-condition / 125,650-fit main
  campaign, with a paired-seed, resumable, deterministic sweep runner.
- A statistics layer: bootstrap percentile CIs, three-outcome breakdown-threshold detection,
  Bonferroni-corrected paired significance tests.
- Cyclic-error harmonic analysis via least-squares projection (not FFT, which corrupts 99 of 359
  conditions where `arc_fraction < 1.0`).
- RQ1/RQ2 analysis (`docs/RQ1_RQ2_ANALYSIS.md`), reviewed for overclaiming via `llm-council`.
- CI: lint + strict type-check + test matrix (Python 3.10/3.11) and a 3-OS x 2-Python
  reproducibility matrix (numeric-tolerance, not byte-exact -- see `docs/PREREGISTRATION.md`
  deviation D4).
- `tests/test_campaign_integrity.py`: permanent CI guards against the Week 5 pre-flight audit's
  defect class (a preregistered axis/metric/RQ that looks covered but isn't).

### Fixed

- Day 21: `arc.build_arc_ramp`'s `endpoint=True` sampling convention duplicated one phase sample
  per full-circle record, biasing Heydemann's moment estimator by ~1/N rad (deviation D1).
- Day 26: dropped an exact-hash reproducibility claim after it was shown false even within a single
  platform across separate CI runs; the claim is now numeric-tolerance (`rtol=1e-9`, `atol=1e-15`)
  on all three OSes (deviation D4).

### Known limitations (Week 5 pre-flight audit, 2026-07-28)

Four defects found in the completed main campaign, all recorded as dated preregistration
deviations rather than silently patched -- see `docs/WEEK5_PREFLIGHT_AUDIT.md` for full detail:

- **D5** — the preregistered `hysteresis_magnitude` axis measures direction-independent radial
  inflation, not path-dependent hysteresis (every campaign waveform is monotonic). RQ3's hysteresis
  half is unanswered by the preregistered campaign.
- **D6** — RQ6 (an N-vs-noise design chart) is unanswerable from the preregistered grid: the
  `samples_per_fit` axis was swept entirely at zero noise.
- **Cost metric** — `runtime_s` was preregistered but never populated by the campaign runner
  (implementation gap, not a deviation; see `docs/WEEK3_METHOD_CONTRACT.md`'s Day 29 defect report).
- **D7** — RQ5's grid never reached the "many-fringe" regime its own research question names;
  answerable only over the sub-fringe range.

Supplementary experiments addressing D5 and D6, and a fix for the cost metric, are planned for Week
5 (`docs/WEEK5-6_EXECUTION_PLAN.md`) and will be reported separately from the preregistered results,
never blended into them.

## [0.1.0] - Unreleased

Initial version under active development. No tagged release yet.
