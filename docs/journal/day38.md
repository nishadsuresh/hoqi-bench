# Day 38 — the contribution claim, updated to match what actually happened

`notes/contribution_claim.md`'s own opening line commits every future document to matching this
framing — "if a later day's writing drifts from it, that's a bug to fix, not a new framing to adopt
silently." Today is that check, for the claim itself.

## What changed

Claim (b) — "extension to nonlinearity classes the classic fitting literature predates" — was
written before Day 15, when no method existed and no result was possible. Rewritten to state
plainly what Week 5 actually found:

- **Power-law**: a real, if largely null, result. Only 7 of 28 fits clear the pre-committed honesty
  floor; where a clean relationship exists, its exponent is near 1, not Lehmann's reported ~3. A
  genuine finding, not a failure to reproduce — but not the confirmation the original claim's
  framing implied might happen.
- **Direction-dependent hysteresis**: **the preregistered campaign never actually tested this
  mechanism at all** — every campaign waveform is monotonic, so the direction-reversal branch of
  the hysteresis transform is dead code for the entire 125,650-fit campaign (deviation D5). Real
  direction-dependence was found, but only via a supplementary experiment built after the gap was
  discovered, carrying the evidentiary weight of one post-hoc run, not a preregistered result.

Added a "Net effect on this claim" paragraph stating this combination directly: the project's
extension to Lehmann's nonlinearity classes is real but weaker than the pre-Day-15 framing, and both
halves — the power-law null result and the hysteresis preregistration gap — belong in the same
sentence of any external write-up, not silently dropped or allowed to imply more than they support.

## Explicitly avoided: describing the gap-finding as an achievement

Per the plan's own instruction, informed by the peer-review consensus against the Expansionist
framing three weeks ago (Weeks 1-2 audit): the "honest boundary" section states directly that
catching the D5 gap accurately **is** the deliverable, and should not be dressed up as a triumph of
the audit process in its own right. Claim (a) — reproducibility infrastructure — is described as
strengthened by having caught this before publication, but that is a statement about (a)'s own
integrity, not a reframing of (b)'s real shortfall as a hidden win.

## Consistency check

`README.md`'s abstract (written yesterday, Day 37) already states claim (b) at exactly this
strength — "a partial extension... the preregistered campaign turned out to test only one of these
two mechanisms as originally intended" — confirmed by direct re-read before writing today's more
detailed revision, not assumed consistent.

## Verification

No code touched today. 249 passed, 2 xfailed (dev venv, unchanged from Day 37).

## What's next

Task 12 (Day 39): the packaging dry-run — build the sdist/wheel, confirm `LICENSE`/`CITATION.cff`/
`CHANGELOG.md` are present (verified once already, Day 29), `twine check`, and a TestPyPI round-trip
install into a fresh venv.
