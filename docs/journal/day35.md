# Day 35 — RQ5, the RQ3-RQ6 synthesis, and a caught overclaim

## RQ5: sub-fringe analysis over the full range, not just the extreme point

`scripts/rq5_analysis.py` reads only existing preregistered data (`arc_fraction` axis + `arc_x_noise`
interaction grid) — no new campaign. Cross-checked every `arc_fraction=0.02` number against
`docs/RQ1_RQ2_ANALYSIS.md`'s RQ1b table programmatically before writing anything: exact match.

Two findings distinct from RQ1b's single-point headline, visible only by looking at the whole range:

- **Heydemann's `unusable_rate` is exactly 1.0 at every sub-fringe `arc_fraction` value and exactly
  0.0 at `arc_fraction=1.0`** — verified across every noise level in the interaction grid, not just
  the noiseless baseline. Not a gradual degradation like every other method shows; a clean binary
  threshold.
- **Halir & Flusser's `unusable_rate` is non-monotonic**: 0.54 at 0.02, rising to 1.00 at 0.05,
  falling back to 0.00 by 0.10. A reader anchored on the single extreme point RQ1b reports would
  miss that reliability gets briefly worse before it gets better.

## The RQ3-RQ6 synthesis document, and a real overclaim caught before it shipped

`docs/RQ3_RQ6_ANALYSIS.md` synthesizes Tasks 2 (RQ3 power-law), 4 (RQ3 hysteresis), 5 (RQ4), 6
(RQ6), and today's RQ5 work. Run through an adversarial review hunting specifically for
overclaiming, per §0.4 item 2 — the same discipline Day 28 applied to the RQ1/RQ2 draft.

**The review caught a fabricated convergence claim.** The first draft asserted "three independent
analyses converge" on `samples_per_fit` being a weak lever, citing RQ3 part 1 and RQ4's within-axis
analysis alongside RQ6. Checked directly: **RQ3 part 1's power-law axes are `amplitude_ratio`,
`quadrature_error_rad`, `dc_offset`, and `hysteresis_magnitude` — `samples_per_fit` was never among
them**, and RQ4's within-axis analysis covers only `photon_scale`/`noise_std`. Neither citation
supports the claim being made. The real second data point was the pre-flight audit's own P2
finding (the zero-noise flatness result from Day 29), misfiled under the wrong analysis's name.
Corrected to state the real two-way convergence at the strength it actually has, with the citation
error itself recorded in the document rather than silently fixed.

Two more real issues from the same review, fixed:

- The document's "Established" summary section stated preregistered and supplementary findings
  with identical, undifferentiated confidence — violating the document's own framing rules 5/6.
  Split into separate paragraphs by evidentiary source.
- RQ3 part 1's `quadrature_error_rad` exponent didn't state which methods produced the 7 clean
  fits. Checked: raw_atan2, Kasa, and Taubin — the three methods with **no structural correction**
  for that distortion, not the tautologically-favored general-conic fitters. This resolved the
  review's concern (that the exponent might be a construction-check artifact) with a factual
  clarification, not a retraction — the finding survives, now stated precisely.

A minor fourth point (Heydemann's mechanism explanation bordering on asserted-as-settled) was
already adequately hedged with "consistent with" language; tightened slightly for consistency with
the corrected framing elsewhere in the document.

## Task 8b: clean-clone reproduction check

Per the plan, this must pass before Week 6 begins. Report follows in a separate section below, run
against the pushed state of this commit.

## Verification

248 passed, 2 xfailed. `ruff check`, `ruff format --check`, `mypy --strict` all clean. One more
transient native-library crash on a full-suite run (same category as Days 32-34, not reproducible
on immediate retry).
