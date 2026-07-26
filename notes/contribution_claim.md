# Contribution Claim

This states precisely what `hoqi-bench` claims and does not claim, based on the related-work
search in `notes/related_work_table.md`. Every future document in this project (README, paper
sections, journal entries) should match this framing — if a later day's writing drifts from it,
that's a bug to fix, not a new framing to adopt silently.

## What this project is NOT claiming

**Not the first comparison of ellipse-fitting methods in homodyne interferometry.** That prior work
exists, and the closest of it is engaged with directly, not waved off: Collett & Tee (2014, JOSA A,
"Ellipse fitting for interferometry. Part 1: static methods") and its follow-up Collett & Watkins
(2015, Part 3, dynamic method) compare multiple ellipse-fitting variants specifically in an
interferometry context, predating this project by over a decade.

**Not the first application of Heydemann's correction, or of ellipse fitting generally, to
quadrature interferometry.** Heydemann (1981) is the origin; Köning, Wimmer & Witkovský (2014),
Požar & Možina (2011), and a steady stream of 2017-2025 papers each propose incremental
improvements. None of this is novel to claim.

**Not a novel ellipse-fitting algorithm.** Every method implemented here (Kasa, Heydemann,
Halir & Flusser, Fitzgibbon, Taubin, and — if time allows — Köning/Wimmer/Witkovský's
nonlinear-constraint fit) is taken from existing, cited literature, faithfully implemented
(including known fragilities, per Day 3's findings) — not modified or "improved" as part of this
project's contribution.

## What this project IS claiming

**(a) Reproducibility infrastructure that does not currently exist.** The related-work search found
no open-source Python package, no public benchmark repository, and no Zenodo-archived dataset that
implements this specific method set (Kasa through Köning/Wimmer/Witkovský) under one common,
installable, tested roof with a controlled, documented parameter space — confirmed via direct
GitHub code search (`"Heydemann correction" language:Python"`: 0 results;
`homodyne quadrature interferometer ellipse` repository search: 0 results), not assumed from
absence of evidence alone. The closest software artifacts found (EllipseFit4HC, MATLAB only;
OEFPIL, R, general-purpose) are single-method-family and not Python. This project's actual
deliverable — a `pip`-installable, typed, tested, CI-backed package plus a versioned, DOI-archived
benchmark dataset plus one-command reproduction — is the kind of artifact this specific literature
does not currently have, regardless of whether any single method in it is new.

**(b) Extension to nonlinearity classes the classic fitting literature predates.** Lehmann et al.
2025's power-law residual scaling and direction-dependent hysteresis findings post-date every
classic ellipse-fitting method compared here by years to decades — none of those methods were
designed with these nonlinearity classes in mind, and (per the related-work search) no existing
comparison tests whether they hold up against them. `hoqi-bench`'s RQ3 asks this directly and
answers it with real numbers (Days 30-31), whatever the answer turns out to be.

## The honest boundary between (a) and (b)

(a) is the safer, unambiguous claim — reproducibility infrastructure is valuable regardless of
whether any individual finding inside it turns out to be surprising. (b) is where a genuinely new
empirical result could emerge (or might not — a null result, "the classic methods hold up fine," is
equally valid and equally worth reporting per this project's own preregistration discipline, Day 6).
Neither should be overstated relative to the other in the eventual paper's abstract/introduction.

## Standing limitation (repeated here deliberately, not just in the Limitations section)

This is a simulation study. No real HoQI hardware, no real bench data, no external peer review
before release. The related-work search itself surfaced that even Lehmann et al. 2025 — the
real-hardware anchor this project extends from — does not appear to have released code or data
(not fully confirmed; see `notes/related_work_table.md`'s caveats), meaning this project's
simulation-based extension cannot currently be cross-validated against that paper's own raw data
even if it wanted to be. This should appear in the abstract itself when written (Day 38), not be
buried in a limitations section a reader might skip.
