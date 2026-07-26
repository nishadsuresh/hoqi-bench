# Köning, Wimmer & Witkovský 2014 — "Ellipse fitting by nonlinear constraints to demodulate quadrature homodyne interferometer signals and to determine the statistical uncertainty of the interferometric phase"

**Access:** SECONDARY / title-and-metadata level only. Full text not accessed (IOPscience
paywalled). Bibliographic details (title, journal, volume/issue/article-number, DOI) were
confirmed directly against the primary IOPscience page.

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

## Open questions
- This paper's actual method (what "nonlinear constraints" means concretely, as opposed to Halir &
  Flusser / Fitzgibbon's linear reformulation) is not understood beyond the title — if this method
  is implemented as "Method 7" (mentioned as a possible Day 20 addition, "bias-corrected
  ellipse-specific fit"), real access to the paper would be needed first; right now there isn't
  enough here to implement it correctly, only enough to know it exists and is on-topic.
- The statistical-uncertainty-quantification angle this paper takes could be directly relevant to
  Day 25's confidence-interval work — worth a real read before that day if time allows, since it
  may be the single most relevant piece of prior art in this whole reading list for that specific
  task, given it's explicitly about uncertainty on interferometric phase from ellipse fitting.
