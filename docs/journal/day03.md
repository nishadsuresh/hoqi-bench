# Day 3 — Ellipse-fitting constraint comparison

## What "numerically unstable" actually means here

An algorithm can be *algebraically* correct — every step follows validly from the last, and if you
did the arithmetic with infinite precision (exact fractions, no rounding) it would always give the
right answer — and still produce garbage on a real computer. The reason is that every floating-point
number only carries about 16 significant decimal digits, and some algebraic operations (inverting a
matrix, solving an eigenvalue problem) can *amplify* the tiny rounding error already present in the
input data by an enormous factor, especially when the matrix involved is close to singular (its
"condition number" — how much it can stretch small input errors — is very large). "Numerically
unstable" means exactly this: correct algebra, wrong answer, because the specific arithmetic path
chosen to implement that algebra happens to blow up small floating-point noise into a large error.
That's the whole reason a second, differently-organized way of solving the *same* algebraic problem
(Halir & Flusser's reformulation) can behave completely differently from the *original* way
(Fitzgibbon's), even though both are mathematically valid.

## A bug caught in my own first attempt (important — read before the results below)

The first version of `fit_ellipse_fitzgibbon()` selected the correct eigenvector out of Fitzgibbon's
6 candidates using a rule remembered from public reference implementations: "pick the one with the
negative eigenvalue." Running it produced a suspicious result — **every single test case, including
the easy, well-conditioned one, came back "ambiguous: 2 negative eigenvalues found."** That's not a
subtle numerical-precision issue; it's a sign the selection rule itself was wrong.

Investigating directly (computing `a^T C a` — the literal quantity the constraint requires to equal
1 — for every candidate eigenvector) showed the actual correct eigenvector has a **positive**
eigenvalue in this script's sign convention for the constraint matrix `C`, and neither of the two
"negative eigenvalue" candidates satisfies the constraint at all (their `a^T C a` is negative, which
can never be rescaled to `+1` by any real scale factor — they're hyperbola solutions, not ellipses).
The "pick the negative eigenvalue" folklore rule is real, but it's tied to a *specific* sign
convention for `C` that public implementations often use — the opposite of the one used here,
which follows Halir & Flusser's own paper (`eq. 9`) literally. Using a convention-dependent rule
without re-deriving it for this script's actual convention was the bug, not Fitzgibbon's method
itself. The fix: select by the actual constraint, `a^T C a > 0`, which is convention-independent by
definition. This is exactly the kind of thing the numeric-verification discipline this project
follows is *for* — the first result "looked like" a dramatic demonstration of the paper's point, and
it would have been a very easy, very wrong thing to write up uncritically.

## What actually happens once the selection rule is fixed

Across 30 random noise seeds per regime:

| regime | cond(D) | Fitzgibbon fail% | Fitzgibbon error | H&F fail% | H&F error |
|---|---|---|---|---|---|
| well_conditioned | 2.2e3 | 0% | 0.0012 | 0% | 0.0012 |
| high_eccentricity | 1.8e4 | 0% | 0.0014 | 0% | 0.0014 |
| partial_arc_30deg | 5.1e5 | 0% | 0.5081 | 0% | 0.5081 |
| tight_clustering_3deg | 1.3e6 | 0% | 0.4730 | 0% | 0.4730 |
| near_degenerate_15deg | 1.1e8 | **0%** | 0.1677 | **60%** | 0.3116 |

At moderate conditioning (the first four regimes), the two methods are statistically
indistinguishable at double precision — modern LAPACK-based eigensolvers largely absorb the
fragility Halir & Flusser describe, at these problem sizes, once the selection bug above is fixed.
This is itself worth stating plainly rather than manufacturing artificial drama: the 1998 paper's
own benchmarking note ("MATLAB v5.0 on one SPARC Ultra-1") suggests the instability they observed
may have been considerably easier to trigger on 1998-era numerics than on a 2026 double-precision
stack.

**Two things needed real extremity to surface, and one of them was genuinely surprising.**

## Finding 1 — the paper's actual point, cleanly reproduced

Using float32-precision input data (deliberately degrading precision, since that's closer to what
Halir & Flusser's own hardware would have experienced) at a moderately extreme 15-degree arc with
high eccentricity: **Fitzgibbon's direct 6x6 approach genuinely fails — two eigenvectors both
satisfy the constraint, with no principled way to choose between them (a real ambiguity, not a
selection-rule bug this time) — while Halir & Flusser's reduced 3x3 approach succeeds cleanly.**
This is the failure mode the paper describes: the singular 6x6 constraint matrix `C` is the root
cause, and reducing to a well-conditioned 3x3 problem genuinely avoids it. Reproduced directly, not
just cited.

## Finding 2 — an honest, unplanned result that complicates the story

At double precision, in the most extreme regime tested (a very thin ellipse sampled over only 15
degrees of arc), **Halir & Flusser's method failed 60% of the time — far more often than
Fitzgibbon's corrected direct approach, which never failed.** This runs directly counter to the
premise that the "stable" reformulation should always be the safer choice, so it was investigated
rather than reported as a strange footnote.

The cause: Halir & Flusser's block-decomposition eliminates the linear coefficients `[d,e,f]` via
`a2 = -S3^-1 * S2^T * a1`, where `S3` is built from the design matrix's linear columns `[x, y, 1]`.
In this near-degenerate regime, `cond(S3) ≈ 1.2e8` — meaning inverting `S3` amplifies whatever
floating-point noise is already present by roughly that factor. Direct inspection of a failing case
confirmed this concretely: the resulting reduced 3x3 matrix produced two complex-conjugate
eigenvalues (not real at all) and one real eigenvector that fails the ellipse-specific condition —
not a code bug, a real consequence of `S3`'s poor conditioning corrupting the elimination step
itself.

**In other words: Halir & Flusser's reformulation trades one specific numerical fragility (the
singular 6x6 constraint matrix `C`, which it genuinely fixes) for a different one their own paper
doesn't analyze (the conditioning of `S3`, the matrix their own elimination step needs to invert).**
In the regime where `S3`'s conditioning is the dominant problem rather than `C`'s singularity, the
"stable" method is not actually the safer choice. This is a real, if narrow, limitation worth
carrying forward into Day 18/19's implementation notes and into how the eventual paper frames the
comparison — not something to quietly drop because it complicates a cleaner story.

## What this means for Day 18/19

Both methods need documented failure-mode notes reflecting what was actually found, not the
textbook expectation: Fitzgibbon's method fails via genuine eigenvector ambiguity when `C`'s
singularity dominates (confirmed at reduced precision); Halir & Flusser's method fails via `S3`
ill-conditioning when the data's linear part is close to rank-deficient (confirmed at double
precision, in the most extreme regime tested here) — a failure mode the original 1998 paper doesn't
discuss. Neither method should be documented as unconditionally safer than the other; which one is
more fragile depends on which specific numerical mechanism the data happens to stress.

---

## Addendum, 2026-07-27 (Day 21) — Finding 1 above does not reproduce

Day 21's cross-validation gate re-ran both findings above against the real method
implementations (`src/hoqi_bench/methods/fitzgibbon.py`, `halir_flusser.py`) rather than this
script's own copies. **Finding 2 is robustly confirmed. Finding 1 is not, and is retracted as
stated.**

What was checked, and what came back:

| check | Day 3 claimed | measured 2026-07-27 |
|---|---|---|
| `near_degenerate_15deg`, float64 | FB 0% / H&F 60% | FB 0% / H&F 60% — **confirmed** |
| Day 3's own `demonstrate_clean_divergence` case (float32, `semi_minor=0.001`, seed 0) | FB "ambiguous", H&F "ok" | **both `ok`** |
| same regime, 200 seeds, float32 | (not measured) | FB-only fails 8%, H&F-only fails 37% |
| same regime, 200 seeds, float64 | (not measured) | FB-only fails 7%, H&F-only fails 42% |

Two things follow. First, **reducing precision to float32 does essentially nothing here** — the
failure rates barely move, and the ordering never inverts. The mechanism Finding 1 attributes the
divergence to (single-precision hardware of the kind Halir & Flusser's own 1998 benchmarking used)
is not what is driving it. Second, Finding 1 was **a single-seed observation reported as a general
result**: running the same script today prints `ok` for both methods on the very case the finding
was drawn from.

This is not a regression. `git log -p --follow scripts/explore_ellipse_constraints.py` shows the
script's numerics unchanged since its Day 3 commit — every later commit is a cosmetic refactor
(dataclass conversion, line wrapping). Whatever produced the original "ambiguous" output was either
a pre-selection-rule-fix run or a parameterisation that was never committed.

**What survives, and is what Day 19/21 actually rely on:** Fitzgibbon's singular-`C` ambiguity is
real and is reachable at double precision — 12% of 200 seeds at `semi_minor=0.001`, all of them the
AMBIGUOUS mode, confirming the fragility `fitzgibbon.py` deliberately preserves is genuinely
present and unpatched. What is *not* supportable is the claim that Halir & Flusser succeeds where
Fitzgibbon fails: in every regime measured, H&F fails 3-5x more often. The closing line of this
entry — "neither method should be documented as unconditionally safer than the other" — turns out
to have been the durable part.

Recorded as an addendum rather than an edit, per this project's never-delete convention.
`docs/WEEK3_METHOD_CONTRACT.md` §3.2 carries the corresponding correction to the gate criterion,
which had inherited Finding 1's direction.
