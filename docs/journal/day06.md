# Day 6 — Preregistration and adversarial council review

## What preregistration protects against, in plain language

Nobody sets out to fool themselves. But if the parameter ranges, the metrics, and the statistical
rules are only nailed down after looking at some early results, it becomes very easy to
retroactively decide "actually, that range makes more sense" in whichever direction makes the
numbers tell a cleaner story — not through dishonesty, just because a satisfying result is a real
pull and there's no external reviewer here to catch the drift. Writing everything down first, then
holding to it (or visibly changing it and saying why), is the cheapest substitute available for
having someone else checking.

## What got built

`docs/PREREGISTRATION.md`, committing the research questions, parameter space, metrics, and
statistical protocol from Day 5's approved design — then, per this day's explicit instruction, run
through the llm-council skill as a hostile peer reviewer would, not rubber-stamped.

## The council did not go easy on this

Five advisors attacked the document from five angles; all five independently converged on the same
core diagnosis even while disagreeing on which fix mattered most: **several things in this document
were "committed" in name only** — postponed decisions wearing a lock icon. The peer-review layer
(five more passes, cross-evaluating the five attacks) then converged further: 4 of 5 reviewers
ranked the Executor's response strongest (it alone turned diagnosis into a dated, actionable fix),
and all 5 flagged the Expansionist's response as the weakest — reframing genuine problems as hidden
strengths without engaging the actual objections raised against them.

## What actually changed, and why each change is a real fix, not a wording patch

1. **RQ2's breakdown thresholds on two axes, demoted to ordinal-only.** The council's strongest
   point: interpolating a precise breakdown threshold off a grid that's admittedly a guess isn't
   imprecise, it's a number about something that may not exist as stated. Fixed by reporting those
   two axes' findings as relative rankings only, never as calibrated thresholds — the amplitude-ratio
   and arc-coverage axes, which ARE grounded in real numbers, keep full quantitative treatment.
2. **Köning/Wimmer/Witkovský's "required but unread" problem, actually fixed, not just
   re-flagged.** Rather than leaving this as a named risk for Day 19 to inherit, went and found real
   information today: the CRAN `OEFPIL` package (open access) explicitly generalizes this exact
   method, and its manual describes the real algorithm — an errors-in-variables model fit by
   iterated Taylor linearization, genuinely different in kind from every other method's single-shot
   linear-algebra solve. This is a meaningfully better starting point than "title and abstract only,"
   and a concrete, named fallback (simpler covariance-weighted total-least-squares) is on record in
   case the full iterative version proves too hard within the remaining schedule.
3. **RQ3's power-law ambiguity, given an actual default and a stated fallback**, rather than left
   open with "we'll figure it out on Day 13." Default: treat it as an emergent property of the
   classic distortions to characterize (fit a power-law curve to existing sweep results), not a new
   mechanism to invent. Fallback stated in case that produces nothing clean. Either way, RQ3 now has
   a concrete, falsifiable target — an explicit operating envelope, not just "did it hold up, yes or
   no" — salvaging the one part of the Expansionist's critique that was actually right.
4. **Cost and robustness, defined as real formulas** — wall-clock time and iteration count for cost;
   failure rate as its own explicit number, kept separate from error-when-successful, for robustness.
5. **The Bonferroni correction, fully specified** — family size, scope, and the resulting alpha
   written down, rather than a method named without its parameters.

## What I did NOT pretend to do today

The council's single highest-leverage suggestion — run a real pilot with all 7 methods to
empirically ground the guessed axes before finalizing anything — genuinely can't happen on Day 6,
because none of the 7 methods exist as code yet. Claiming to have done this would have been exactly
the kind of thing this whole exercise exists to prevent. Instead, it's committed as a scheduled
action for Day 15 (once the first methods exist), logged here and in `PREREGISTRATION.md` itself,
with an explicit trigger for revising the document again if the pilot finds the grids implausible.
