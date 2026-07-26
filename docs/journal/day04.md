# Day 4 — Related work and gap validation

## What "a benchmark contribution" is, and why reproducibility counts as real research

It's tempting to think research only "counts" if it discovers something nobody knew before. But a
huge amount of real, valuable scientific work is making existing knowledge *checkable* — building
the thing that lets someone else verify a claim, compare two methods fairly, or reuse a result
without re-deriving it from scratch. If five different papers each propose "an improved ellipse fit"
and each only compares itself against one prior method, on data nobody else can access, then the
field has five papers and no way to actually know which method is best, or under what conditions
each one breaks. A benchmark that puts all of them on the same, documented, reproducible footing is
a real contribution to that field even if it doesn't discover a sixth, better method — it's the
difference between "five people each say their own approach is good" and "here's a shared, checkable
answer to which approach is good, and when."

## What got done today

A genuine literature and software search, not a token check: general web search across academic
databases and search engines, direct PyPI search, and — specifically because general web search
can't browse GitHub's own code index — a direct GitHub code and repository search via `gh api
search/code` and `gh api search/repositories`. Every query is logged verbatim in
`notes/related_work_table.md` so this search is itself reproducible, not just asserted.

## What the search found — engaged with honestly, not dismissed

**The real prior art**: Collett & Tee's 2014 JOSA A paper ("Ellipse fitting for interferometry. Part
1: static methods") and its follow-up Collett & Watkins (2015, Part 3, dynamic method) genuinely
compare multiple ellipse-fitting approaches specifically for interferometry, over a decade before
this project. This is not brushed aside — `notes/related_work_table.md` and
`notes/contribution_claim.md` both name it directly and explain precisely what's different: this
project widens the specific method set (bringing in the Halir-Flusser/Fitzgibbon/Taubin trio from
the general computer-vision literature, plus Köning/Wimmer/Witkovský's interferometry-specific
nonlinear-constraint fit, none of which the 2014-2015 papers compare together), releases it as
actual open, installable code (neither 2014-2015 paper has any code release, confirmed via search
rather than assumed), and extends to nonlinearity classes (Lehmann et al. 2025's power-law residual
scaling and hysteresis) that didn't exist in the literature until eleven years after Collett & Tee.

**No full pre-emption found.** No paper runs the specific method set this project implements against
each other in one place. No open-source Python package or Zenodo dataset does this either — direct
GitHub searches for `"Heydemann correction" language:Python` and for repositories matching `homodyne
quadrature interferometer ellipse` both came back with zero results. The closest software found
(EllipseFit4HC, a MATLAB-only implementation of one of the seven methods; OEFPIL, a general-purpose
R package) don't overlap in language, scope, or method count.

## What would have been the honest thing to do if the search HAD found a real collision

If a paper or repository had turned up doing essentially what this project sets out to do, the plan
was to say so plainly and immediately rather than bury it — this is exactly the instruction this
day's task came with, and it's worth restating here even though it didn't end up being necessary:
finding out a project duplicates existing work is much cheaper on Day 4 than on Day 42.

## Real limitations of today's search, stated rather than hidden

Two of the closest papers (Collett & Tee, Collett & Watkins) are paywalled — this search worked from
abstracts and secondary summaries, not the full text, so the characterization of exactly which
methods they compare is at abstract-level confidence, not verified by reading the paper directly.
Lehmann et al. 2025's own code/data availability wasn't fully confirmed absent (checked the arXiv
HTML rendering, not PDF supplementary material or a possible later journal version). Both flagged
explicitly in `notes/related_work_table.md` rather than smoothed into an unqualified "no code
exists" claim.
