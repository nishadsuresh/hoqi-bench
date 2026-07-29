# Day 33 — RQ4: Poisson vs. Gaussian ranking comparison

The one remaining methodological decision the pre-flight audit flagged as genuinely open (not a
defect): what does "equivalent noise level" mean for comparing method rankings across two
physically different noise models? Routed through `llm-council` per §0.4 before any analysis code
existed (`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 2).

## The council

5 advisors proposed matched-sigma, matched-SNR, matched-Fisher-information/CRB, and a no-matching
within-axis-only alternative. Three independent peer-review passes converged unanimously on two
points: report a sensitivity matrix across all matching definitions rather than defending one, and
— the more interesting catch — two advisors' rejection of Fisher information (arguing it requires
committing to a specific estimator) was a real technical error, independently caught by all three
reviewers. Cramér-Rao Fisher information is a property of the measurement model itself, computable
in closed form from a resolved condition's own parameters, never of any correction algorithm. Peer
review also caught something none of the 5 initial advisors raised: nobody proposed testing whether
an observed ranking flip is statistically distinguishable from ordinary seed-to-seed noise before
calling it real.

Adopted: primary analysis reports each axis's own internal ranking (zero cross-axis assumptions);
secondary analysis builds a sensitivity matrix across three matching rules and only calls a
difference real if it survives a bootstrap significance check.

## Building the Fisher-information module

`src/hoqi_bench/fisher_information.py` differentiates the exact composed forward model this
project's own transforms produce (verified against `transforms.py`'s own docstring rather than
re-derived): `I(phi) = mean_intensity + A*cos(phi)`, `Q(phi) = mean_intensity +
A*amplitude_ratio*sin(phi+quadrature_error_rad)`, giving closed-form Fisher information for both
noise models (Gaussian: constant variance; Poisson: variance = intensity/photon_scale, genuinely
phi-dependent, confirmed directly rather than assumed). One overclaim caught before it shipped:
the first draft's docstring asserted both channels stay positive "across the FULL amplitude_ratio
and quadrature_error_rad grids this module is ever called against" — checked directly and found
false at `amplitude_ratio=1.5` (Q's minimum goes negative). Fixed to state precisely what's actually
verified: positivity holds at RQ4's shared baseline (`amplitude_ratio=1.1`), which is the only
condition this module is ever called with, since neither noise axis sweeps that parameter.

6 tests, including two oracle-independent reconstructions of the derivative sum from first
principles (not imported from the module under test) and a monotonicity check.

## A real bug in my own significance check, caught before results were trusted

First implementation always tested `gaussian_ranking[0]` (Heydemann — the tautologically-favored
method per `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md`'s Category 1 prediction, essentially always
ranked first) for significance, regardless of which methods actually swapped position. Checked the
actual divergence points before trusting a first, encouraging-looking result (100% of flagged
differences "significant"): every single divergence was at position 1, 2, or 4 — **never position
0**. The check was validating a method that never moved.

Fixed with `_first_diverging_pair`: identifies the specific pair of methods whose relative order
actually changed, and requires BOTH conditions' bootstrap CIs to show a significant, consistently-
ordered difference (Gaussian CI entirely on one side, Poisson CI entirely on the other) before
calling the swap real. Re-running with the fix changed the headline result completely: **100% →
0% of flagged ranking differences survive proper significance testing**, across all three matching
rules. Inspected one swap in detail to confirm this isn't the fix being *too* conservative:
Fitzgibbon and Halir & Flusser have near-identical per-seed RMSE values under both conditions
(matching Day 17/18's own finding that these two methods are numerically near-equivalent in
well-conditioned regimes) — the "swap" between them really is noise, and the corrected check
correctly says so.

## The result

**Within-axis**: 12 of 17 grid points show a ranking that differs from their own axis's first
(baseline) point — expected, and uninteresting on its own (harder conditions reorder methods with
different noise sensitivities within one noise model, which nothing about RQ4 disputes).

**Cross-axis (the actual RQ4 question)**: 4–7 of 9 matched pairs show an apparent ranking
difference depending on the matching rule, but **zero survive the bootstrap significance check
under any of the three matching definitions**. The honest finding: at this campaign's swept range,
no method-ranking difference between Poisson and Gaussian noise is distinguishable from ordinary
seed-to-seed sampling noise. This is one of the three honest outcomes the protocol's own
falsification criterion named as legitimate in advance — not a null result manufactured after the
fact.

## Verification

241 passed, 2 xfailed (net +10 real tests: 6 in `test_fisher_information.py`, 4 in
`test_rq4_analysis.py`). `ruff check`, `ruff format --check`, and `mypy --strict` all clean on every
file touched today and the full repo. One transient `SystemError: attempting to create PyCFunction
with class but no METH_METHOD flag` observed on one full-suite run — the exact crash signature this
project's own Day 20 journal already documented as a known WSL/BLAS-threading flake, not
reproducible on immediate retry with identical code, isolated test file passing clean both times.

## What's next

Task 6 (Day 34): RQ6's supplementary N×noise design chart — the other unanswerable-as-written RQ
(D6), needing new supplementary campaign data this time, not just new analysis over existing data.
Per §0.6, protocol committed before any code.
