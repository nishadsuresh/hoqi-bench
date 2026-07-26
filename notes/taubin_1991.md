# Taubin 1991 — "Estimation of planar curves, surfaces, and nonplanar space curves defined by implicit equations with applications to edge and range image segmentation"

**Access:** SECONDARY / general knowledge only. Full text not accessed (IEEE Xplore paywalled; the
verification pass found the correct full title, volume/issue/pages via dblp and the author's own
hosted PDF listing, but did not read the paper's content itself). This paper backs the *stretch*
method (Day 20, "Method 6"), so depth of understanding here is deliberately lighter than the
core-path papers above — flagged honestly rather than padded out.

## Citation
Taubin, G. (1991). *Estimation of planar curves, surfaces, and nonplanar space curves defined by
implicit equations with applications to edge and range image segmentation.* IEEE Transactions on
Pattern Analysis and Machine Intelligence, 13(11), 1115-1138. Note: this is the full, correct
title — noticeably longer and more general (covers curves *and* surfaces, not just circles/ellipses)
than the short form ("bias-reduced algebraic fit") used to describe it in this project's build
plan. See `refs/references.bib` (`Taubin1991`).

## Core claim (as generally known, not verified from source)
Proposes a bias-corrected algebraic fitting approach, generally described in the circle/ellipse
fitting literature as reducing the systematic small-shape bias that plain algebraic fits (like
Kasa's) exhibit, via an approximate normalization of the fitting objective based on the gradient of
the implicit curve equation (an approximation to true geometric/Sampson distance) rather than
unweighted algebraic distance.

## What it does NOT address
- Cannot state with confidence, without having read the source, exactly how much bias reduction is
  achieved relative to Kasa specifically, or under what conditions (noise level, arc coverage) the
  approximation breaks down — this would need to come from the paper directly or from a secondary
  source that discusses it quantitatively, neither of which was found in this pass.

## Open questions
- Since this is a Day 20 *stretch* method ("if time allows"), the honest state of this note
  reflects that: enough is known to implement a reasonable version of "Taubin's method" as
  generally described in the fitting literature, but not enough to make specific quantitative
  claims about its expected behavior relative to the other methods ahead of actually running it.
  Any comparative claim about Taubin specifically in the eventual paper should be checked against
  what `hoqi-bench`'s own Day 20/21 results actually show, not against an assumed prior expectation
  from this thin note.
- If this method is in fact implemented (not cut per the "if behind schedule" priority order,
  where stretch methods are the second thing cut), getting real access to the source paper before
  Day 20 would materially improve the implementation's fidelity to Taubin's actual formulation
  rather than a generic "Taubin-style" approximation.
