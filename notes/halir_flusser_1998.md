# Halir & Flusser 1998 — "Numerically stable direct least squares fitting of ellipses"

**Access:** PRIMARY. Full PDF fetched directly (autotrace.sourceforge.net/WSCG98.pdf) and read in
full (8 pages). Page numbers in the citation (125-132) are from secondary sources, not visible in
the fetched text itself — see `refs/references.bib` note.

## Citation
Halíř, R. & Flusser, J. (1998). *Numerically stable direct least squares fitting of ellipses.*
Proceedings of WSCG'98, Plzeň, Czech Republic. See `refs/references.bib` (`Halir1998`).

## Core claim
Fitzgibbon et al.'s (1999, submitted/circulated earlier as a 1996 conference paper — see that
paper's own notes file) direct ellipse-specific least-squares fit is provably correct in theory but
numerically fragile in practice, because its 6x6 generalized eigenvalue problem's constraint matrix
`C` is singular, which forces picking out the one eigenvector with a negative eigenvalue by scanning
signs — a step that becomes ambiguous or wrong under floating-point roundoff on scattered/noisy
data. Halir & Flusser fix this via a **block decomposition** of the 6x6 system into two 3x3 blocks
(quadratic terms `[x^2, xy, y^2]` vs. linear terms `[x, y, 1]`), reducing the problem to a much
smaller, well-conditioned 3x3 generalized eigenvalue problem with no sign-scanning ambiguity.

## Equations I need (Day 3 and Day 18-19)
- Eq. 1: general conic `F(x,y) = ax^2 + bxy + cy^2 + dx + ey + f = 0`.
- Eq. 2: ellipse-specific constraint `b^2 - 4ac < 0`.
- Eq. 6: the scaled equality-constraint reformulation `4ac - b^2 = 1` (exploits the fact that `a`
  and any scalar multiple `alpha*a` represent the same conic).
- Eq. 7-9: the constrained minimization `min ||Da||^2 s.t. a^T C a = 1`, the N x 6 design matrix
  `D` (rows `[x_i^2, x_i*y_i, y_i^2, x_i, y_i, 1]`), and the 6x6 constraint matrix `C` (all zero
  except `C[0,2] = C[2,0] = 2`, `C[1,1] = -1`).
- Eq. 10: the generalized-eigenvalue optimality condition `S*a = lambda*C*a`, `a^T*C*a = 1`, where
  `S = D^T*D` is the 6x6 scatter matrix — this is Fitzgibbon's original formulation, described in
  the paper's own background section before the fix is introduced.
- The block-decomposition itself (their improvement): splits `a` into quadratic-part `a1 = [a,b,c]`
  and linear-part `a2 = [d,e,f]`, and `S`/`C` accordingly into 3x3 sub-blocks, reducing the
  generalized eigenproblem to size 3 instead of 6 — exact sub-block algebra needs a direct re-read
  when implementing Day 18, not just this summary.

## What it does NOT address
- Explicitly states its own limitation in the conclusion: because it minimizes *algebraic* distance
  (not true geometric/orthogonal distance), fitted ellipses are systematically biased toward being
  *smaller* than the true ellipse, and "this bias depends on the parameters of the fitted ellipse
  and cannot be simply corrected." States plainly that for applications needing high accuracy, this
  method is better used as a fast initial estimate for a subsequent iterative geometric-distance
  refinement, not as the final answer. Relevant to Day 18's docstring (failure-mode note) and to
  interpreting Day 21's method-agreement check.
- Does not address quadrature-interferometry or Heydemann's correction at all — this is a general
  computer-vision/pattern-recognition ellipse-fitting paper; Days 2 and 17 connect it to the
  interferometry-specific application.
- Does not address hysteresis, noise-dependent fitting behavior, or non-static distortion — it's a
  single-snapshot, noiseless-in-theory geometric fitting method.

## Open questions
- The exact numerical values of the small worked examples/failure cases in the paper's own
  experiments section were not extracted in this pass — worth a targeted re-read on Day 3 if the
  synthetic conditioning-spectrum study needs a specific known failure case to reproduce, rather
  than only a newly-generated one.
- Page range (125-132) is secondary-sourced, not seen directly in the fetched PDF text — low
  stakes (doesn't affect implementation), flagged for completeness per the citation standard.
