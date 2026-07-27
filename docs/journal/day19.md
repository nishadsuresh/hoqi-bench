# Day 19 — Fitzgibbon (Method 5) + external cross-validation

## The research-ethics point: why faithfully reproducing weakness matters

It would have been easy to make Fitzgibbon "better" — add a fallback to the block-decomposed
solve when the direct one fails, relax the ambiguity check, quietly pick the first candidate
when several satisfy the constraint. Every one of those would misrepresent *two* papers at
once: Fitzgibbon's own contribution (the first non-iterative, ellipse-guaranteed direct fit)
depends on this implementation actually having the properties that paper claims, fragility
included; Halir & Flusser's contribution (fixing exactly this fragility) is only meaningful
as a comparison if there's something real to compare it against. A benchmark that quietly
patches the thing it's supposed to be measuring isn't measuring anything. This is the same
principle Day 16 and Day 18 already established — port faithfully, characterize honestly —
applied to the one method where "faithfully" specifically means "don't fix it."

## What Day 3 already told us, and what I got right by checking first

Before writing a single test assertion, checked Day 3's own documented per-regime numbers
(`docs/journal/day03.md`) rather than guessing. They show something genuinely counterintuitive:
Fitzgibbon has a **perfect record** — 0% failure — across *all five* of Day 3's conditioning
regimes, including the most extreme one (15° of arc on a 160:1-eccentricity ellipse), where
Halir & Flusser (Day 18) fails 60% of the time. This isn't a contradiction of anything —
`docs/WEEK3_METHOD_CONTRACT.md`'s Day 21 gate criteria already anticipated the two methods
*diverging* in ill-conditioned regimes, not Halir & Flusser uniformly winning. Building the
test suite directly against these known numbers meant all three of today's tests passed on
the first run — a contrast with every previous method day, where a hand-guessed tolerance
had to be corrected against reality at least once.

## Tier 2 external cross-validation, moved up from Day 21

Per the plan, pulled this forward deliberately — a disagreement found today has days of
debugging room rather than hours before Day 21's blocking gate. Installed `lsq-ellipse` and
`ellipsinator` (both real, independently-authored PyPI packages, added as a `validation`
extra — never a runtime dependency) and cross-checked both Halir & Flusser and Fitzgibbon
against them on well-conditioned synthetic data.

Halir & Flusser agrees with both external packages to within `1e-6` — near machine precision,
as expected for a numerically stable, well-conditioned solve. Fitzgibbon needed a different,
still-tight but honestly wider tolerance (`1e-3`, not `1e-6`): measured a small, consistent
`1e-5`–`2e-5` disagreement with `ellipsinator`'s own Fitzgibbon implementation across 10
seeds. Not a bug — Fitzgibbon's unreduced 6×6 system with a singular constraint matrix is
*by design* the less numerically stable path (the entire reason Halir & Flusser's paper
exists), so two independent eigenvalue solvers landing a few parts in a hundred-thousand
apart is exactly what "less stable" predicts, not a red flag.

**Known coverage gap, stated plainly**: these two packages only cover Halir & Flusser and
Fitzgibbon — the two most algebraically similar of the seven methods. Kasa, Heydemann,
Taubin, and Köning stay externally uncrossed here and rely on Day 21's Tier 1 analytic
oracle instead. This test now runs in CI on every future commit — a permanent, machine-
checkable regression guard, not a one-time check.

## What got built

- **`src/hoqi_bench/methods/fitzgibbon.py`** — Method 5, built from this project's own more
  careful Day 3 exploration code (matching Day 18's precedent), not a naive reimplementation.
- **`tests/test_fitzgibbon.py`** — 3 tests: Day 3's exact 5-regime failure-rate reproduction,
  close agreement with Halir & Flusser on well-conditioned data, and documented degradation
  at tight angular clustering.
- **`tests/test_external_cross_validation.py`** — 4 tests, the Tier 2 cross-check described
  above, plus a `validation` extra in `pyproject.toml` and an updated CI workflow to install
  it on every run.

## Status

111/111 tests passing (was 104 at Day 18's close; +7 today — 3 from Fitzgibbon, 4 from the
external cross-validation suite), ruff clean, mypy --strict clean (46 files). Day 20 next:
Taubin, Köning, the full
7-method robustness matrix, and the runtime probe — moved up from Day 26 specifically because
Köning is the only iterative method among the seven and the existing runtime projection was
never checked against that.
