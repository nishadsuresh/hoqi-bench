# Fitzgibbon, Pilu & Fisher 1999 — "Direct least square fitting of ellipses"

**Access:** SECONDARY (but a strong secondary source). The original paper itself was not directly
fetched (IEEE Xplore paywalled). However, Halir & Flusser 1998 — fetched and read directly in full
(see `notes/halir_flusser_1998.md`) — describes Fitzgibbon's method in detail as background before
presenting their fix, including reproducing its core equations (their eq. 1-10 are Fitzgibbon's
original formulation). So the *method* itself is understood through a primary source's faithful
description of it, even though Fitzgibbon's own paper (with its own original numbering, worked
examples, and failure-case data) was not read directly.

## Citation
Fitzgibbon, A. W., Pilu, M., & Fisher, R. B. (1999). *Direct least square fitting of ellipses.*
IEEE Transactions on Pattern Analysis and Machine Intelligence, 21(5), 476-480. See
`refs/references.bib` (`Fitzgibbon1999`).

## Core claim
First non-iterative, ellipse-specific direct least-squares fit: reformulates general conic fitting
(which can return any conic — ellipse, parabola, hyperbola) as a quadratically constrained
least-squares problem (`min ||Da||^2` subject to `a^T C a = 1`) that is guaranteed to return an
ellipse specifically, solved via a single generalized eigenvalue decomposition rather than
iteration. See `notes/halir_flusser_1998.md` for the actual equations (1-10), since those were
read from a primary source reproducing them faithfully.

## What it does NOT address (per Halir & Flusser's characterization of it)
- Numerical stability: the 6x6 constraint matrix `C` is singular, forcing a search for the one
  eigenvector with negative eigenvalue among the generalized eigenvalue solutions — under
  floating-point roundoff on scattered or noisy data, this selection step can become ambiguous or
  pick the wrong eigenvector, producing "unoptimal or even completely wrong results" (Halir &
  Flusser's own characterization). This is the specific fragility Day 3 and Day 19 need to
  reproduce and document, not paper over.
- Like Halir & Flusser, uses algebraic (not geometric) distance — same small-ellipse bias applies.

## Open questions
- Fitzgibbon's own paper reportedly includes specific numerical examples/benchmarks (referenced
  indirectly via Halir & Flusser's comparison section) that were not extracted in this pass. If
  Day 19's "preserve the fragility deliberately" task needs a specific documented failure case
  from Fitzgibbon's own paper (rather than one newly generated in `hoqi-bench`), direct access to
  the original 1999 paper would be needed — currently out of reach (IEEE Xplore paywall). The
  fallback is generating equivalent failure cases synthetically (already the plan for Day 3), which
  is a reasonable substitute but not literally "reproducing Fitzgibbon's documented case."
