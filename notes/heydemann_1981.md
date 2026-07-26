# Heydemann 1981 — "Determination and correction of quadrature fringe measurement errors in interferometers"

**Access:** PAYWALLED. Full text not accessed. This note is built from (a) the general,
well-established description of "the Heydemann correction" as it's summarized and cited across
the other papers in this reading list (Lehmann 2025 cites and applies it directly; the
`quadrature-interferometer-sim` project's own README and this project's forward-model plan both
describe the same three-parameter correction), and (b) title/venue/year metadata confirmed via
secondary bibliographic sources (Optica abstract page, ADS). **Nothing below should be treated as
a direct quote or a verified equation number from the actual 1981 text** — equation-level citation
in the code (per `docs/DOCUMENTATION_STANDARD.md` rule 4) will need either institutional access to
the actual paper or continued reliance on how later papers (Lehmann 2025 in particular) describe
it, clearly marked as such rather than presented as if Heydemann's own equation numbers were read.

## Citation
Heydemann, P. L. M. (1981). *Determination and correction of quadrature fringe measurement errors
in interferometers.* Applied Optics, 20(19), 3382-3384. See `refs/references.bib`
(`Heydemann1981`).

## Core claim (as commonly described, not independently re-derived from the source text)
Real two-photodetector quadrature interferometers exhibit three characteristic, static error
sources relative to the ideal model: unequal gain between the two channels (amplitude imbalance),
a phase offset between the channels that isn't exactly 90 degrees (quadrature phase error), and a
DC bias/offset on each channel. Together these distort the ideal circular (I, Q) Lissajous
trajectory into a tilted, off-center ellipse. The paper is credited as the origin of correcting for
this by fitting that ellipse's parameters and using them to transform the distorted trajectory back
onto a unit circle before recovering phase via `atan2`.

## Equations I need
This is exactly what Day 2's task is for: derive the correction from first principles (starting
from the distorted quadrature signal model) rather than copying equations from a source this
project cannot currently access. Day 2's derivation stands in for direct equation citation here —
the derivation itself, verified symbolically, is the actual provenance this project can honestly
claim, cross-checked against how the correction is *described* (not equation-numbered) in
accessible secondary sources.

## What it does NOT address
- As commonly described (not verified from source): the classic Heydemann correction assumes the
  three error parameters are static/time-invariant during the measurement — this is exactly the
  assumption Lehmann et al. 2025 test the limits of (drift, hysteresis).
- Does not address shot noise or any stochastic noise model — it's a deterministic geometric
  correction for a systematic distortion, orthogonal to RQ4's noise-model question.
- Does not (as far as can be told without the source) address ellipse-fitting *algorithm* choice —
  it defines the physical error model and correction concept; Kasa/Halir & Flusser/Fitzgibbon/Taubin
  are all about *how* to numerically fit the ellipse, a question this 1981 paper likely predates in
  its modern form.

## Open questions
- Real access to this paper (library/institutional access) would materially improve Day 2's
  derivation-vs-original-source cross-check — currently that cross-check can only be done against
  how *other, accessible* papers describe Heydemann's result, which is a weaker form of
  verification than reading the source directly. Flagging this as a standing limitation rather than
  pretending the cross-check is as strong as it would be with direct access.
- The exact original notation/parameterization Heydemann used (is it amplitude ratio + phase
  offset + two DC terms, exactly four parameters, or does the original paper use a different
  decomposition?) is inferred from how later work describes it, not confirmed directly.
