# Day 20 — Köning/Wimmer/Witkovský, robustness matrix, runtime probe (Week 3 closes)

## Köning: the hardest method, and what "algorithm family" actually means in code

Every prior method minimizes an *algebraic* residual — treating the fitted curve as exact
and every deviation as error in one implicit equation. Köning's paper does something
structurally different: it treats *both* channels, `I` and `Q`, as carrying measurement
error simultaneously — an errors-in-variables (EIV) model — and refines the fit iteratively
rather than solving it in one shot.

The concrete technique implemented here is **iterated Sampson-distance reweighting**: at
each step, weight every point by `1 / |∇F|` — the gradient of the implicit conic equation,
evaluated at the *current* parameter estimate — which approximates true geometric
(orthogonal) distance far better than a raw algebraic residual does. Because the weights
depend on the current estimate, the fit can't be solved in one step; each iteration
re-weights, re-solves, and checks whether the parameters actually moved. That
current-estimate-dependence is what makes this genuinely iterative rather than "an algebraic
fit plus a loop," and what makes the errors-in-variables framing real rather than
decorative. Verified numerically before writing a line of the real implementation: recovers
a known synthetic ellipse to a few parts in ten-thousand, converging in 4 iterations.

**Explicit scope, stated in the code itself, not just here**: the original 2014 paper is
still unread (paywalled). This is an implementation of the *algorithm family* the OEFPIL
package manual describes, not a reproduction of the paper's own tuning choices — the plan's
own explicit allowance, taken up honestly rather than quietly overclaimed.

**Covariance, scoped honestly too.** `FitResult.covariance` exists because Day 15 designed
the whole interface around this method's needs. At convergence, the weighted normal
equations give a standard covariance estimate for the *fitted conic coefficients* —
verified finite, symmetric, and positive semi-definite before trusting it. This is real and
useful, but it's covariance of the raw algebraic parameters, not yet propagated into
phase-space uncertainty — a genuinely partial answer to "the statistical uncertainty of the
interferometric phase" the paper's own title promises, and said so directly rather than
implying more precision than what's actually there.

## The robustness matrix: zero crashes, first try

Ran all 7 methods against 5 adversarial input categories — near-zero phase excursion, a
genuine circle, 10-sample records, 5x the campaign's worst noise, and all-identical points —
35 cells total. **Every single cell came back graceful**: either a clean result, or a
`failed=True` with a specific reason code. Zero crashes on the first real run. This isn't
luck — it's each method's own failure-mode guard, built and independently verified across
Days 17–20 against its *own* adversarial conditions, holding up against a *different* battery
it was never specifically tuned against. That's exactly what "faithfully implemented, not
overfit to the test suite" is supposed to buy.

One hygiene note along the way: the matrix run surfaced two numpy `RuntimeWarning`s
(`invalid value encountered in sqrt`, `divide by zero`) from already-handled degenerate
cases in the shared post-fit conversion. Both were expected outcomes (caught downstream by
existing `isfinite` checks) — silenced deliberately at the source with a documented
`np.errstate` context, rather than left as unexplained noise in test output.

## The runtime probe — and a real crash it found

Projected the full campaign from a representative sample first: ~17 seconds, dramatically
under the plan's 12-hour stop-and-ask threshold. Rather than trust a linear extrapolation —
Köning's iteration count could plausibly vary a lot by condition — ran the *actual* full
125,650-run campaign directly, since it was cheap enough to just do.

**First attempt crashed.** Partway through, with a low-level
`SystemError: attempting to create PyCFunction with class but no METH_METHOD flag` — a
numpy/BLAS internal error, not anything in this project's own logic. The cause: that run was
a standalone script invoked directly, which never imports `conftest.py`, so P4's BLAS
thread-count pin was never applied — tens of thousands of rapid `np.linalg` calls under
32-way thread contention (this venv's real default, per P4's own earlier investigation)
apparently pushed something past a stability edge. Re-ran the identical script with
`OMP_NUM_THREADS=1`/`OPENBLAS_NUM_THREADS=1`/`MKL_NUM_THREADS=1` set explicitly: **all
125,650 runs completed cleanly in 14.32 seconds.**

This changes what P4's fix actually is. It was built and justified as a determinism
safeguard (audit item B5). It turns out to also be **a crash-prevention requirement** for
Day 24's real sweep runner — every worker process must inherit this pin, not as a nice-to-
have, but because the alternative has now been directly observed to crash under sustained
load. `conftest.py`'s own docstring updated with the full account, and a permanent stress
test added (~1,750 back-to-back calls across all 7 methods, run under pytest's own pinned
process) so this specific regression is guarded against on every future commit — without
adding 14 seconds to the fast test suite by re-running the entire campaign every time.

**Also found, as a real byproduct of running the whole thing for real**: overall failure
rate across the full campaign is **5.81%** (7,303 of 125,650 runs), of which 1,999 are
Köning's own non-convergence. This is concrete, non-hypothetical confirmation that
`docs/WEEK3-4_PLAN.md` Part 0.4's differential-dropout concern is real, not speculative —
Day 22's aggregation logic needs the convergence-rate-alongside-error rule it already
commits to, and now has a real number to sanity-check against once it's built.

## What got built

- **`src/hoqi_bench/methods/koning_wimmer_witkovsky.py`** — Method 7, the last of the 7.
- **`scripts/robustness_matrix.py`** + **`tests/test_robustness_matrix.py`** — the matrix
  itself, and a permanent CI check that it stays crash-free.
- **`tests/test_full_campaign_smoke.py`** — the sustained-load regression guard for the
  crash found above.
- **`conftest.py`** — updated with the crash account, upgrading P4's own justification.
- **`src/hoqi_bench/methods/_ellipse.py`** — two `RuntimeWarning`s silenced deliberately at
  an already-handled degenerate path.

## Week 3, closed

All 7 methods implemented: raw atan2, Kasa, Heydemann, Halir & Flusser, Fitzgibbon, Taubin,
Köning/Wimmer/Witkovský. 123/123 tests passing, ruff clean, mypy --strict clean (54 files).
Every method day surfaced at least one real, traced, honestly-recorded finding — a test bug
caught by an ungrounded tolerance (Days 15, 17), a corrected acceptance criterion (Day 16), a
dangerous silent numpy behavior (Day 18), a falsified contract prediction correctly narrowed
rather than hidden (Day 20's Taubin), and now a real crash found and fixed (Day 20's runtime
probe). Day 21 next: the cross-validation gate — the closest thing this project gets to peer
review, with an explicit, pre-committed failure branch per `docs/WEEK3-4_PLAN.md`, so a
failing gate can't quietly become a passing one under schedule pressure.
