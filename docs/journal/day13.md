# Day 13 — Power-law nonlinearity

## What "power-law nonlinearity" means here, and why it differs in kind from the classic distortions

Every distortion built so far (amplitude imbalance, quadrature phase error, DC offset, both noise
models) is a *mechanism* — a specific, well-defined thing physically happening to the signal, with
its own equation, that gets injected into the forward model and can be dialed up or down. Lehmann et
al. 2025's "power-law" content is a different kind of claim entirely: it's an *observation* about
what residual error looks like after correction, not a description of a new thing going wrong in the
detector. Their Section III.C reports that once their real hardware's ellipse correction is applied,
whatever nonlinearity is still left over shrinks and grows with the range of motion in a way that
traces out roughly a cubic curve — a *description of an outcome*, not a *specification of a cause*.

This is exactly the ambiguity flagged all the way back on Day 1 (`notes/lehmann_2025.md`) and named
explicitly as something to raise with Nishad on this day rather than resolve silently — which is
what happened before any code was written today. Confirmed: this project treats power-law as
something to *characterize* in this project's own sweep results (fit a curve to error-vs-magnitude
data from the mechanisms that already exist, see if the exponent lands near Lehmann's reported ~3),
not as a new mechanism to invent and inject. If that characterization produces no clean relationship
at all in this project's own data, the recorded fallback (Day 6's preregistration) is to build it as
an injected mechanism instead, the way hysteresis will be tomorrow.

## What got built

- **`src/hoqi_bench/power_law.py`**, `fit_power_law_exponent` — log-log linear regression
  (`error = coefficient * magnitude^exponent`), returning the exponent, coefficient, and R² of the
  fit. R² is returned deliberately, not discarded — a low R² is the actual, specified trigger for
  falling back to the injected-mechanism approach, not something to notice only by eyeballing a plot
  later.
- **Five tests**, since Days 15-20's real phase-recovery methods don't exist yet to generate real
  error-vs-magnitude data: synthetic data built with a known exponent (3.0, matching Lehmann's
  reported value directly, plus a separate check with a different coefficient to make sure the fit
  isn't accidentally tied to one specific number), first exactly (no noise) then with realistic
  multiplicative noise, confirming the fit recovers the true exponent within a reasonable tolerance
  either way. A rejection test for the zero/negative-value edge case a log-log fit can't handle. And
  — the one that matters most for this project's own honesty — a test that a genuinely *flat*
  relationship (no real magnitude-dependence at all) is correctly reported as a low-R², near-zero
  exponent fit, not a falsely confident "yes, power of 3" result. That's the actual mechanism this
  project's fallback plan depends on triggering correctly when the real data comes in on Day 30.

## What's still ahead

The real question — does this project's own sweep data actually show a power-law relationship, and
does its exponent land near 3 — can't be answered until Days 15-20 build real phase-recovery methods
and Day 27 runs the actual main campaign. Today's scope, confirmed with Nishad before writing any
code, was building and validating the analysis tool that question will be answered with, not
answering the question itself prematurely on synthetic stand-in data.
