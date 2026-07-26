# Day 1 — Documentation standard + literature infrastructure

## What got built

Two foundational pieces, both meant to be referenced constantly for the rest of this project
rather than written once and forgotten:

1. **`docs/DOCUMENTATION_STANDARD.md`** — the seven rules every module in this codebase follows
   (module docstrings, section banners, purpose-not-syntax comments, equation provenance,
   design-decision notes, failure-mode notes, daily journals), plus a fully worked before/after
   example on Kasa's circle fit showing exactly what "meets the standard" looks like versus code
   that runs correctly but doesn't.
2. **Literature infrastructure**: `refs/references.bib` (verified BibTeX for all 7 papers in the
   reading list) and one `notes/*.md` file per paper, each following the same template — citation,
   core claim, the exact equations this project needs from it, what it does *not* address, and
   open questions.

## What "verified" actually meant here

Two of the seven papers (Lehmann 2025 and Halir & Flusser 1998) are open access, and I read the
actual full text of both rather than working from a summary — the Lehmann PDF was already fetched
earlier this project's history and the Halir & Flusser PDF was fetched fresh today. The other five
(Heydemann 1981, Fitzgibbon 1999, Kåsa 1976, Taubin 1991, and the paper listed as "Kok et al. 2014")
are paywalled. For those, a research pass cross-checked bibliographic details (author names,
volume/issue/pages, DOIs) against multiple independent sources rather than trusting the reading
list's details at face value — and this caught something real.

## A real error caught in the reading list itself

**The paper listed as "Kok et al. 2014" is misattributed.** Checking the actual paper at the given
DOI (10.1088/0957-0233/25/11/115001, Measurement Science and Technology 25:115001) shows the real
authors are **Köning, Wimmer, and Witkovský**, not "Kok, Challis" or anything close to it — every
other detail in the reading list entry (journal, volume, issue, article number, year, DOI) was
correct, only the author names were wrong. This is now corrected throughout the project
(`refs/references.bib`, `notes/koning_2014.md`) with the mistake documented rather than silently
fixed, since a reading list is exactly the kind of thing worth double-checking rather than copying
forward, and I'd rather you know this changed than find a citation that doesn't match what you're
reading.

## A second thing worth flagging now, not on Day 13

Reading Lehmann et al. 2025 in full surfaced a genuine ambiguity in how the build plan describes
one of its own upcoming tasks. Day 13 calls for implementing "the power-law nonlinearity class from
Lehmann et al. 2025" as a third forward-model distortion mechanism, alongside amplitude imbalance
and quadrature phase error. Having now read the actual paper: **the "power-law" content in Lehmann
2025 is an empirically observed scaling relationship in their residual-noise data (residual
nonlinearity vs. motion range, roughly cubic) — not a distinct injectable distortion mechanism with
its own forward-model equation**, the way amplitude imbalance and quadrature phase error each have
one. `notes/lehmann_2025.md` lays out two genuinely different things Day 13 could mean and why they
lead to different implementations. I'm flagging this today, seven days early, rather than waiting
for Day 13 to raise it, since it's the kind of thing you might want to think about while reading the
paper yourself this week rather than getting surprised by it later.

## Why a reading list needs this kind of check at all

It would have been easy to just copy the reading list's bibliographic details into BibTeX and move
on — nothing about a wrong author name breaks any code. But this project's whole contribution
claim rests on being trustworthy reproducibility infrastructure, and a references file with a
silently wrong author attribution undermines exactly that kind of trust, in a small but very
avoidable way. The cost of checking was one research pass; the cost of not checking would have been
a citation error sitting in a "citable" package all the way through to the Zenodo release six weeks
from now.
