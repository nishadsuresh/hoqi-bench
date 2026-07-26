# Köning, Wimmer & Witkovský 2014 — "Ellipse fitting by nonlinear constraints to demodulate quadrature homodyne interferometer signals and to determine the statistical uncertainty of the interferometric phase"

**Access:** SECONDARY, upgraded 2026-07-26. The original 2014 paper itself is still not accessed
(IOPscience paywalled) — bibliographic details were confirmed directly against the primary
IOPscience page. However, the actual algorithm FAMILY this paper introduced is now understood via
a real primary source: the CRAN `OEFPIL` R package manual (open access, fetched and read in full),
which explicitly generalizes this method. See the "Update 2026-07-26" section below.

## Important correction to the reading list
The build plan's reading list names this reference as **"Kok et al. 2014"**. That author
attribution is **wrong** — a direct check of the actual paper at the given DOI
(10.1088/0957-0233/25/11/115001) shows the real authors are **Köning, Wimmer, and Witkovský**, not
"Kok, Challis" or any similar name. The journal, volume, issue, article number, year, and DOI given
in the reading list were all otherwise correct — only the author names were mismatched, likely a
mixup with a different, unrelated researcher (there is a well-known quantum-optics physicist named
Pieter Kok, but no connection to this paper or topic was found). Using the verified correct
citation throughout this project; see `refs/references.bib` (`Koning2014`).

## Citation (corrected)
Köning, R., Wimmer, G., & Witkovský, V. (2014). *Ellipse fitting by nonlinear constraints to
demodulate quadrature homodyne interferometer signals and to determine the statistical uncertainty
of the interferometric phase.* Measurement Science and Technology, 25(11), 115001.

## Core claim (from title and abstract-level understanding only)
Directly relevant to this benchmark's own topic (quadrature homodyne interferometer demodulation
via ellipse fitting) — the most on-topic of the classic ellipse-fitting references, since it's
specifically about interferometry rather than general computer-vision ellipse fitting. Its stated
focus, per the title, is twofold: an ellipse-fitting approach using nonlinear constraints (as
opposed to Halir & Flusser / Fitzgibbon's linear-algebra reformulations), and — notably — explicit
statistical uncertainty quantification on the recovered interferometric phase, which none of the
other classic fitting papers in this reading list appear to address.

## What it does NOT address (inferred from title/scope, not verified)
- Cannot confirm from title alone whether it addresses the Lehmann-class nonlinearities
  (power-law residual, hysteresis) at all — likely predates that specific framing (2014 vs. 2025),
  so probably not, but this is inference, not a confirmed fact from the text.

## Update 2026-07-26: the algorithm family is now understood, via a real primary source

Following Day 6's adversarial council review (which flagged "required but unread" as a real
preregistration risk), found and read directly the manual for **OEFPIL** (CRAN R package, open
access, PDF fetched and read in full), which explicitly generalizes this 2014 paper's method.
**Access level upgraded from title/abstract-only to a real understanding of the algorithm family**,
though still not the original paper's own ellipse-specific worked equations.

What "nonlinear constraints" means, concretely: an **errors-in-variables (EIV) model** — unlike
Halir & Flusser / Fitzgibbon / Kasa / Taubin, which all treat the fit as ordinary least squares on
one implicit algebraic residual, this method treats **both I and Q as having measurement error**
(not just distance-to-curve in an unweighted algebraic sense), and estimates the ellipse parameters
by **iterated linearization via Taylor expansion** of the nonlinear implicit constraint around a
current parameter estimate, refining via a covariance-weighted (Locally Best Linear Unbiased
Estimation) update each iteration until convergence — a Gauss-Newton-style EIV estimator, built on
Kubáček (2000)'s general framework, not a single-shot linear-algebra solve the way the other six
methods are.

This is enough to implement a faithful, real version of the algorithm FAMILY (iteratively-linearized
covariance-weighted EIV ellipse fit) even without the original 2014 paper's specific tuning
choices. The original paper's exact worked ellipse constraint equation and interferometry-specific
covariance model would still improve fidelity if obtained, but this is no longer a blocking unknown
for Day 19-20 — see `docs/PREREGISTRATION.md`'s updated fallback plan.

## Open questions
- The original paper's specific covariance model (how I/Q measurement uncertainty is characterized
  for a real HoQI detector, as opposed to a generic EIV setup) is still not confirmed — a reasonable
  default (isotropic Gaussian noise, matching this project's own noise model from Day 11) will be
  used unless/until better information is found.
- The statistical-uncertainty-quantification angle this paper takes could be directly relevant to
  Day 25's confidence-interval work — worth a real read before that day if full paper access is ever
  obtained, since it may be the single most relevant piece of prior art in this whole reading list
  for that specific task, given it's explicitly about uncertainty on interferometric phase from
  ellipse fitting.
