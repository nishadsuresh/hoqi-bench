# Day 18 — Halir & Flusser (Method 4)

## The block decomposition, intuitively

Fitzgibbon's original direct ellipse fit poses the problem as one 6×6 generalized eigenvalue
system. The catch: the constraint matrix `C` in that system is *singular* — most of its
entries are exactly zero, with just three nonzero values scattered in it. A singular matrix
in a generalized eigenproblem means some directions are undefined, which is exactly what
forces the fragile "scan the eigenvectors and pick the one with a positive sign" step Day 3
found breaks under floating-point roundoff.

Halir & Flusser's fix: split the six unknowns into two groups — the three *quadratic*
coefficients (`a`, `b`, `c`, which determine the ellipse's shape and tilt) and the three
*linear* ones (`d`, `e`, `f`, which determine its position). It turns out the linear group
can always be eliminated algebraically in terms of the quadratic group (solving a small,
well-behaved 3×3 system), collapsing the whole problem down to a 3×3 eigenproblem on the
shape coefficients alone — and at that smaller size, the equivalent constraint matrix is
*invertible*, so there's no singular direction left to create ambiguity. Same underlying
math, reorganized so the fragile step never has to happen.

## A design decision: which of this project's own two implementations to build from

Two versions of this algorithm already exist in this codebase's orbit: a compact one in the
sibling `quadrature-interferometer-sim` project, and a more careful one this project's own
Day 3 built specifically to explore where Fitzgibbon breaks
(`scripts/explore_ellipse_constraints.py`). They're mathematically identical — verified
algebraically, not assumed — but the Day 3 version has real failure handling the sibling
project's doesn't: an explicit catch around the one matrix inversion that can go singular,
and an explicit check that a candidate eigenvector's `4ac-b²` value is both real-positive
*and* has negligible imaginary part.

That second check matters more than it sounds like it should. Verified directly: numpy
compares a complex array to a real number using *only the real part*, silently, at every
warning level — `np.array([1+2j]) > 0` succeeds and returns `True`, no error, no warning.
The sibling project's bare `cond > 0` would silently accept an eigenvector with real
eigenvalues on paper but complex components in practice — a genuinely dangerous trap on
exactly the degenerate inputs this method is supposed to be tested against. Since Day 18's
task is specifically to confirm this implementation survives Day 3's own degenerate regimes,
building from Day 3's own more careful code was the right call, not an arbitrary preference.

## A test that assumed the wrong thing — and reproduced a known result instead

The first version of the "survives Day 3's regimes" test asserted zero failures everywhere,
reasoning that fixing the sign-scanning ambiguity is the whole point of the paper. It failed
at 18 of 30 seeds (60%) on the most extreme regime (15° of arc on a 160:1-eccentricity
ellipse). That looked like a bug — until checking what Day 3's *original* study actually
found there: the same 60% Halir & Flusser failure rate, exactly. Fitzgibbon was actually
*better* at that one extreme regime (0% failure). The block decomposition fixes the specific
bug that made Fitzgibbon look artificially worse everywhere — it doesn't make ellipse
fitting itself robust at 15° of near-degenerate arc under any formulation. Reproducing 60%
here is confirmation of an already-published result, not a new defect — fixed by correcting
the test's assumption and grounding its expectation in the actual documented numbers, not by
touching the implementation.

## Shared post-fit machinery, and why it doesn't compromise Day 21

Refactored a small shared module, `methods/_ellipse.py`: `conic_to_heydemann_params`
(converting a fitted ellipse into this project's `(dc_i, dc_q, g, eps)` parameterization) and
`apply_heydemann_correction` (the closed-form transform back to a circle). Day 17's Heydemann
now calls the shared correction function too, rather than duplicating it. This is legitimate
sharing, not a violation of Day 15's independence rule: what Day 21 benchmarks is the
numerical *path* from raw data to a fitted ellipse — genuinely different between Heydemann's
moments, Halir & Flusser's eigenproblem, and whatever Fitzgibbon/Taubin/Köning do next. What
happens *after* a fit is validated — turning parameters into a phase value — is mechanical
and appears nowhere in any of these papers' own content; sharing it is no different from
every method sharing `numpy`.

## What got built

- **`src/hoqi_bench/methods/_ellipse.py`** — shared post-fit conic→phase machinery.
- **`src/hoqi_bench/methods/halir_flusser.py`** — Method 4.
- **`src/hoqi_bench/methods/heydemann.py`** — refactored to use the shared correction helper
  (behavior-preserving; all 4 of its existing tests still pass unchanged).
- **`tests/test_halir_flusser.py`** — 3 tests: near-machine-precision recovery on
  well-conditioned synthetic data, Day 3's full 5-regime conditioning spectrum reproduced
  with grounded (not assumed) per-regime failure rates, and an end-to-end check through the
  real distorted-signal pipeline.

## Status

104/104 tests passing (was 101; +3), ruff clean, mypy --strict clean (43 files). Day 19 next:
Fitzgibbon — implemented faithfully *including* its known fragility, which this day's own
Day 3 numbers now make concrete rather than theoretical.
