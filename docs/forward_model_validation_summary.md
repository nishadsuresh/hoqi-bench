# Forward Model Validation Summary

Produced at the close of Week 2 (Day 14), per that day's task. Every distortion class implemented
so far, its test status, and the specific independently-derived analytic property each was checked
against — not just "tests pass," but *what property* each passing test actually establishes.

| Distortion class | Module | Test status | Verified analytic property |
|---|---|---|---|
| Ideal (distortion-free) signal | `forward_model.py` | 3/3 passing | Exact fringe spacing = λ/2 (0.000000% error, bit-identical to `quadrature-interferometer-sim`); ideal (I,Q) traces an exact circle of radius `contrast`; zero displacement gives constant, well-defined phase |
| Pipeline composition | `pipeline.py` | 3/3 passing | Empty pipeline is bit-identical to the ideal signal (not just numerically close); pipeline introduces no randomness of its own; transforms compose in documented sequential order |
| Amplitude imbalance | `transforms.py` | 2/2 passing | Produces a known axis ratio (= `amplitude_ratio`) with zero tilt, verified via independent covariance-matrix/PCA measurement, not the transform's own formula |
| Quadrature phase error | `transforms.py` | 3/3 passing | Produces a known, fixed 45-degree tilt (independent of the specific error magnitude) and a known axis ratio `sqrt((1+|sin(eps)|)/(1-|sin(eps)|))`, both derived via sympy before being written into any test, verified across 5 distinct magnitudes |
| DC offset | `transforms.py` + `test_forward_geometry.py` | (covered by the combined keystone test below) | Purely additive; commutes algebraically with the other two classic distortions |
| **Combined (all 3 classic distortions together)** | `test_forward_geometry.py` | 3/3 passing | **The keystone test**: center and full covariance-matrix shape match closed-form predictions derived independently of the transform code, across 4 distinct non-trivial parameter combinations — confirms the verified 2-transform composition order (Day 8) genuinely generalizes to 3 transforms, which was not guaranteed in advance |
| Gaussian detector noise | `noise.py` | 5/5 passing | Empirical variance matches specified sigma within the calculated statistical tolerance (`sigma/sqrt(2N)`); I/Q noise channels are independent (correlation near zero, sample-size-derived tolerance); deterministic under a fixed seed; two different seeds give different output |
| Poisson shot noise | `noise.py` | 4/4 passing | Variance is proportional to intensity (the defining physical property) across 5 distinct intensity levels; distribution shape converges toward Gaussian (skewness → 0) as photon count grows, per the Central Limit Theorem's concrete quantitative prediction |
| Power-law characterization | `power_law.py` | 5/5 passing | Correctly recovers a known injected exponent (both exactly and under realistic noise) from synthetic data; correctly identifies a genuinely flat (non-power-law) relationship via low R² rather than reporting a falsely confident exponent — the specific mechanism this project's Day-30 fallback plan depends on |
| Direction-dependent hysteresis | `transforms.py` | 6/6 passing | Zero magnitude gives zero enclosed loop area (confirms the measurement method itself is sound); nonzero magnitude produces a real, substantial loop area; loop area scales exactly linearly with magnitude (verified empirically before being asserted, ratio constant to within 0.1% across 5 magnitudes); up-pass and down-pass mean radii differ by exactly `2 * hysteresis_magnitude`, the direct definition of the direction-dependent effect; **(2026-07-26 audit fix, finding F1)** direction-of-travel now derives from the generator's ground-truth `true_displacement`, not the noisy measured signal — loop area is unaffected by noise that would previously have corrupted direction toward a coin flip (measured: <10% area change under noise_std=0.05, vs. the ~57%-accuracy-only-50%-chance direction agreement the old noisy-signal-derived approach had at that noise level) |

**Total: 47/47 tests passing, `ruff check` clean, `mypy --strict` clean**, across the full Week 2
forward model (`forward_model.py`, `pipeline.py`, `transforms.py`, `noise.py`, `power_law.py`).

## What this table does NOT claim

This is a validation of the forward model's internal consistency and its faithfulness to derived/
cited equations — it is not a claim that any of these distortion magnitudes are calibrated to real
hardware (two parameter ranges are explicitly engineering judgment, per `docs/PREREGISTRATION.md`),
and it is not yet a validation of any phase-*recovery* method (Days 15-20 build those; this is only
the forward, signal-generation half of the pipeline).
