# Day 42 — retrospective, and where this project actually stands

Written honestly at the close of the research/engineering work, before the two remaining
credential-gated steps (Days 40-41) happen — this entry does not pretend those are done. What
follows is what this project, as it stands, actually answers, actually does not, and what its own
process caught versus what it took a dedicated audit to find.

## What this benchmark actually answers

- **RQ1/RQ2**: on the classic Heydemann distortion axes, results are a construction check, not a
  finding — algebraically guaranteed by which methods share the forward model's own functional
  form. The real finding is a complete reliability inversion at extreme low arc coverage: the four
  methods that dominate every classic-distortion axis become totally unusable, and the two
  circle-only methods remain accurate.
- **RQ3, power-law half**: a genuine, largely null result. This project's own sweep data does not
  reproduce Lehmann et al. 2025's power-of-3 exponent on any tested axis.
- **RQ3, hysteresis half**: **not answered by the preregistered campaign.** Answered instead by a
  supplementary experiment, with that experiment's own reduced evidentiary weight — real
  direction-dependence found in several methods.
- **RQ4**: no Poisson-vs-Gaussian ranking difference proved statistically real, under any of three
  independently-reasoned matching definitions.
- **RQ5**: sub-fringe regime only. Heydemann requires a full revolution as a hard, binary threshold.
- **RQ6**: **not answerable from the preregistered grid.** Answered instead by a supplementary
  interaction grid — `samples_per_fit` has far less influence than method choice or noise level.

## What this benchmark does not answer, and why that is stated plainly rather than minimized

Two of six preregistered research questions could not be answered from the campaign this project
actually preregistered and ran. That is not a footnote. It is found, on this project's own record,
by a dedicated audit run five weeks in — not by an outside reader, not by the two prior adversarial
`llm-council` reviews, not by Day 21's cross-validation gate, and not by the Week 3 review. Four
separate review processes, each real and each having caught real problems of its own, all missed
this specific defect class. The fifth process — a pre-flight audit built specifically to ask "does
the grid actually have the statistical leverage the research question needs," rather than "does the
code do what it says" — is what found it.

## What the six-week process caught, and what it took until Day 29 to find

**Caught early, by the mechanisms already in place:**
- Day 21's cross-validation gate failed on its first run and caught a forward-model sampling defect
  before it could publish an artifactual finding.
- Two `llm-council` reviews of planning documents, pre-data, restructured real parts of the
  experimental design before any campaign ran.
- The Week 3 review found the preregistered failure-rate metric measured self-detection, not
  failure — inverting the true reliability ranking, caught before Week 4's campaign would have
  reported it backwards.

**Not caught until Day 29's dedicated pre-flight audit, despite surviving every mechanism above:**
- RQ3's hysteresis axis never activating direction-dependence (a monotonic-waveform bug present
  since Week 2).
- RQ6's design chart being arithmetically unanswerable (present since the v2 preregistration
  revision that introduced the axis).
- The cost metric being 100% unmeasured (present since Week 4's runner was first built).
- RQ5's scope silently narrowing from "many-fringe" to "one fringe" in prose.

**The honest lesson, stated once rather than left implicit**: every prior review process checked
"is the code correct" or "is the plan well-reasoned." None of them checked "does the preregistered
grid actually have the statistical leverage to answer the question it was built for." That is a
different question, and answering it requires a different kind of audit — one built to compare
research questions against grid coverage directly, not to review code or reasoning in isolation.
This is now a permanent, automated check (`tests/test_campaign_integrity.py`), not a one-time catch.

**And even Week 5's own remediation process was not immune** — Day 36's documentation audit caught
two real overclaims in that same week's own analysis writing, missed by the `llm-council` review
that had already run on that exact document three days earlier. The pattern held at every level of
this project: no single review process, however good, is sufficient on its own. What worked was
running several different kinds of check against each other and trusting the discrepancies they
surfaced, not any one check's clean result in isolation.

## Where things stand

Weeks 1-5 (Days 0-36) closed. Week 6's documentation, packaging, and verification work (Days 37-39)
is done and clean. Days 40-41 — the PyPI upload and the Zenodo DOI — require Nishi's credentials
directly and have not happened as of this entry. Zenodo's own gate (OSF amendment, doc audit,
clean-clone reproduction, packaging dry-run) is fully satisfied except the OSF amendment itself,
which also needs Nishi's account access. Nothing about the project's substantive research content
is blocked; only the final act of publishing it to two external indices is.
