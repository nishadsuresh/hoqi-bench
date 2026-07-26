# Related Work

Search conducted 2026-07-26. Full query list at the bottom of this file — every claim below traces
back to one of those queries, run via general web search (Google Scholar/arXiv/journal abstract
pages), direct PyPI search, and direct GitHub code + repository search via the `gh` CLI (`gh api
search/code`, `gh api search/repositories`). This search log is itself the defense of the
contribution claim in `notes/contribution_claim.md` — if this project's novelty framing is ever
challenged, this is the reproducible record of what was actually checked, not an assertion made
from memory.

## Comparison table

| Paper / artifact | Year | Methods compared | Test conditions | Noise model | Code available? | Data available? |
|---|---|---|---|---|---|---|
| Collett & Tee, "Ellipse fitting for interferometry. Part 1: static methods" (JOSA A) | 2014 | Multiple static algebraic/geometric ellipse fits with different normalizations (not the same named set as this project — predates Halir-Flusser/Fitzgibbon/Taubin being compared together in interferometry) | Simulated + real interferometer data, per abstract-level access (paywalled, not read in full — see note below) | Not confirmed (paywalled) | No | No |
| Collett & Watkins, "Ellipse fitting for interferometry. Part 3: dynamic method" (JOSA A) | 2015 | A new time-series-aware dynamic fit vs. the Part 1 static methods | Noisy, high-eccentricity data (per abstract) | Not confirmed (paywalled) | No | No |
| Köning, Wimmer & Witkovský, "Ellipse fitting by nonlinear constraints..." (Meas. Sci. Technol.) — the corrected reference from Day 1 | 2014 | Nonlinear-constraint (errors-in-variables) fit vs. standard Heydemann least-squares — a pairwise comparison, not a broad method-set benchmark | Not confirmed in depth (paywalled) | Not confirmed | MATLAB only, "EllipseFit4HC" (MathWorks File Exchange) — no GitHub/Python port found | Not confirmed |
| Požar & Možina, "Enhanced ellipse fitting in a two-detector homodyne quadrature laser interferometer" (Meas. Sci. Technol.) | 2011 | One new linear ellipse-specific fit + bias correction vs. prior Heydemann-style approaches | Not confirmed in depth (paywalled) | Not confirmed | No | No |
| Assorted 2017-2025 single-method papers (Fu et al. 2023 *Opt. Lett.*; IEEE 2023 reference-interferometer paper; *Appl. Opt.* 2025 dimensionality-reduced fit) | 2017-2025 | Each proposes ONE new/improved fit vs. one or two baselines (usually Heydemann) — not a shared multi-method benchmark | Varies per paper | Varies per paper | Not checked per-paper (all narrow, single-comparison papers; low prior likelihood of a benchmark artifact) | Not checked |
| Lehmann et al. 2025 (arXiv:2511.04386) — this project's anchor paper | 2025 | Real-hardware measurement + ellipse correction; compares primarily against no-correction, not against a broad method set | Real HoQI + mechanical resonator, one hour of dynamic motion | Real hardware noise, not simulated | No code/data-availability statement found in the arXiv HTML rendering (PDF supplementary materials not separately checked — flagged as uncertain, not confirmed absent) | Same caveat as above |
| `bdhammel/least-squares-ellipse-fitting` (`lsq-ellipse` on PyPI) | ongoing | Halir-Flusser-style direct fit only | General computer vision, not interferometry-specific | N/A | Yes (Python, PyPI) | N/A |
| `ellipsinator` (PyPI, McKibben) | ongoing | Halir-Flusser, Fitzgibbon, and a "guaranteed ellipse estimate" method | Built for phase-cycled bSSFP MRI parameter mapping, not interferometry | MRI-domain noise, not interferometer-specific | Yes (Python, PyPI) | Not applicable (library, not a benchmark dataset) |
| OEFPIL (CRAN R package) | ongoing | Generalizes the Köning/Wimmer/Witkovský nonlinear-constraint EIV method into a reusable estimator | General-purpose (e.g. nanoindentation examples), not a HoQI benchmark | Not interferometer-specific | Yes (R, CRAN) | Example datasets only, not a HoQI benchmark dataset |
| Direct GitHub code search: `"Heydemann correction" language:Python` | searched 2026-07-26 | — | — | — | 0 results | — |
| Direct GitHub repo search: `homodyne quadrature interferometer ellipse` | searched 2026-07-26 | — | — | — | 0 results | — |
| Direct GitHub code search: `"quadrature interferometer" ellipse fit` | searched 2026-07-26 | 3 results, none relevant (a Julia interferometer package with no multi-method benchmark; an unrelated LaTeX paper-dataset scrape; an unrelated LLM training-data text file) | — | — | — | — |
| PyPI direct search: `heydemann`, `quadrature interferometer`, `hoqi` | searched 2026-07-26 | — | — | — | 0 relevant results | — |

## Honest assessment: the closest prior art, engaged with directly

**Collett & Tee (2014, Part 1) + Collett & Watkins (2015, Part 3)** is real, citable, non-trivial
prior work comparing multiple ellipse-fitting variants specifically in the interferometry context —
this is NOT waved off as irrelevant. It predates the specific named trio of Halir-Flusser/
Fitzgibbon/Taubin fits (from the general computer-vision ellipse-fitting literature) being compared
together in an interferometry benchmark, has no released code or dataset (confirmed absent via
search, not assumed), and obviously predates and does not test Lehmann et al. 2025's nonlinearity
classes (power-law residual scaling, hysteresis) since those were only characterized in 2025.
`hoqi-bench`'s contribution is precisely the gap between this 2014-2015 series and what exists now:
a wider, named method set, released as open reproducible code, extended to the newer nonlinearity
classes neither this series nor Lehmann et al. themselves benchmark against each other.

**Nothing found fully pre-empts this project.** No paper runs Kasa, Heydemann-least-squares,
Halir & Flusser, Fitzgibbon, Taubin, and the Köning/Wimmer/Witkovský nonlinear-constraint fit
against each other in one controlled comparison. No open-source Python package or Zenodo dataset
does this either — the closest software artifacts (EllipseFit4HC, OEFPIL) are single-method-family,
non-Python, and don't cover the Lehmann-class nonlinearities.

## Real limitations of this search (stated plainly, not hidden)

- **Collett & Tee/Watkins' actual PDFs were not read** — both are paywalled on Optica, and this
  search relied on abstracts and secondary summaries. The characterization of "what exactly they
  compare" above is at abstract-level confidence, not full-text-verified. If institutional access
  becomes available, re-reading these directly before the paper's final Related Work section would
  strengthen this claim materially.
- **Lehmann et al. 2025's "no code released" finding is not fully confirmed** — based on the arXiv
  HTML rendering only, not a direct check of PDF supplementary materials or a published-journal
  version's data-availability statement.
- **General web search cannot fully replace a proper systematic literature review** — a real
  academic novelty search would also check backward/forward citations of the papers above, which
  wasn't done here given the scope of a one-day task. This is flagged, not glossed over, as a
  limitation of a single day's search rather than a definitive, exhaustive clearance.

## Exact search queries (reproducibility log)

Via general web search (arXiv/Scholar/journal abstracts):
1. `Ellipse fitting for interferometry Part 1 static methods paper`
2. `Lehmann 2025 arXiv 2511.04386 quadrature interferometer nonlinearity`
3. `Ellipse fitting for interferometry Part 3 dynamic method Heydemann Kasa comparison JOSA A`
4. `Koning Wimmer Witkovsky ellipse fitting nonlinear constraints homodyne interferometer`
5. `"Heydemann correction" python github`
6. `quadrature interferometer ellipse fitting benchmark github python HoQI`
7. `"Enhanced ellipse fitting" two-detector homodyne quadrature laser interferometer Eom Kim`
8. `Fitzgibbon Halir Flusser Taubin ellipse fit comparison interferometer nonlinearity correction`
9. `site:github.com EllipseFit4HC OR "Heydemann" OR "quadrature homodyne interferometer" python`
10. `"comparison of ellipse fitting" phase demodulation interferometer 2022 OR 2023 OR 2024`
11. `pypi.org "heydemann" OR "quadrature interferometer" OR "hoqi"`
12. `github.com "hoqi-bench" OR "HoQI bench" ellipse fitting`
13. `zenodo ellipse fitting benchmark homodyne interferometer nonlinearity dataset`
14. `Lehmann homodyne quadrature interferometer HoQI gravitational wave seismic isolation github code repository Birmingham`
15. `"quadrature interferometer" python pip install ellipse fit github repository`
16. `ellipsinator github mckib2 ellipse fitting MRI methods list`
17. `R package OEFPIL CRAN Witkovsky ellipse fit interferometer function`
18. Direct PyPI search: `heydemann`, `quadrature interferometer`, `ellipse fitting`

Via direct GitHub API search (`gh api search/code`, `gh api search/repositories`), run separately as
a belt-and-suspenders check since general web search cannot browse GitHub's own code index:
19. `search/code: "Heydemann correction" language:Python` → 0 results
20. `search/repositories: homodyne quadrature interferometer ellipse` → 0 results
21. `search/code: "quadrature interferometer" ellipse fit` → 3 results, all confirmed irrelevant (checked directly, see table)
22. `search/repositories: hoqi-bench` → 1 result (this project's own repo only)
