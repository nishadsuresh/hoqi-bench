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
Halir & Flusser, Fitzgibbon, Taubin, and Köning/Wimmer/Witkovský's errors-in-variables fit —
all seven were built, per `src/hoqi_bench/methods/__init__.py`'s `METHOD_REGISTRY`; the "if
time allows" conditional here was stale, corrected Week 6 doc audit, 2026-07-29) is taken from
existing, cited literature, faithfully implemented (including known fragilities, per Day 3's
findings) — not modified or "improved" as part of this project's contribution.

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

**(b) Extension to nonlinearity classes the classic fitting literature predates — weaker than
originally framed, updated here to match what actually happened (Day 38, 2026-07-29), not the
Week 1 version of this claim.** Lehmann et al. 2025's power-law residual scaling and
direction-dependent hysteresis findings post-date every classic ellipse-fitting method compared
here by years to decades — none of those methods were designed with these nonlinearity classes in
mind, and (per the related-work search) no existing comparison tests whether they hold up against
them. `hoqi-bench`'s RQ3 asks this directly. What actually happened, run against real results:

- **Power-law**: characterized on this project's own campaign data (`docs/RQ3_RQ6_ANALYSIS.md`).
  Only 7 of 28 (axis, method) fits clear a pre-committed honesty floor, and where a clean
  relationship does exist, its exponent lands near 1 — **not** Lehmann's reported ~3. This is a
  genuine, reportable result (not every clean relationship needs to match a prior paper's number to
  be worth reporting), but it is a null-to-mixed result, not a confirmation.
- **Direction-dependent hysteresis**: **the preregistered campaign never actually tested this
  mechanism.** Every campaign waveform is a monotonic ramp, so `transforms.hysteresis`'s
  direction-reversal branch is dead code for the entire 125,650-fit main campaign
  (`docs/PREREGISTRATION.md` deviation D5) — the preregistered `hysteresis_magnitude` axis measures
  a real but different effect (direction-independent radial inflation). This was found by a Week 5
  pre-flight audit, not by design. A **supplementary** experiment, built and run after the fact
  under a protocol committed before any of its code existed (`docs/SUPPLEMENTARY_PROTOCOLS.md`
  Protocol 1), did find real direction-dependence in several methods — but that result carries the
  evidentiary weight of one post-hoc supplementary run, not a preregistered campaign result.

**Net effect on this claim**: (b) is real but weaker than the version of this document written
before Day 15. The project extends to the power-law question with a genuine (if largely null)
preregistered answer, and to the hysteresis question only via a supplementary experiment the
preregistered campaign itself failed to actually run. Both facts belong in the same sentence in any
external write-up — neither should be quietly dropped nor allowed to imply more than it supports.

## The honest boundary between (a) and (b)

(a) is the safer, unambiguous claim — reproducibility infrastructure is valuable regardless of
whether any individual finding inside it turns out to be surprising, and it is strengthened, not
weakened, by the fact that this project's own preregistration discipline caught the (b) gap above
before publication rather than after. (b) is where a genuinely new empirical result could emerge —
and did, partially: a real (if unexpected-shape) power-law null result, and a real supplementary
finding on hysteresis direction, sitting alongside a real gap in what the preregistered campaign
actually managed to test. Neither should be overstated relative to the other, and the (b) shortfall
should not be dressed up as a triumph of the audit process that caught it — catching it accurately
is the deliverable, not a headline achievement in its own right.

## Standing limitation (repeated here deliberately, not just in the Limitations section)

This is a simulation study. No real HoQI hardware, no real bench data, no external peer review
before release. The related-work search itself surfaced that even Lehmann et al. 2025 — the
real-hardware anchor this project extends from — does not appear to have released code or data
(not fully confirmed; see `notes/related_work_table.md`'s caveats), meaning this project's
simulation-based extension cannot currently be cross-validated against that paper's own raw data
even if it wanted to be. **Confirmed in the abstract as written (`README.md`, Day 37/38, 2026-07-29)
— present in the abstract's own text, not buried in a limitations section a reader might skip.**
