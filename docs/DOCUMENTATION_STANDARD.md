# Documentation Standard

Every module in `hoqi-bench` follows this standard. It's referenced by every daily prompt in this
project's build plan, so it needs to be unambiguous rather than aspirational — this document
defines exactly what "done" looks like for documentation, not just a list of good intentions.

## The seven rules

### 1. Module docstring

Every `.py` file's top docstring answers three questions, in this order:
- **What it does** — one or two sentences, concrete, no marketing language.
- **Why it exists** — what problem it solves or what it replaces. If it's a specific paper's
  method, say so here.
- **Where it sits in the pipeline** — what calls it, what it calls, what stage of the benchmark
  (forward model / method / metric / harness / etc.) it belongs to.

### 2. Section banners

Inside a file, label major logical blocks with a banner comment:

```python
# ---- 1. Build the design matrix ----
```

Banners are numbered when order matters (most of the time, in this project) and are short enough
to scan in one line. They exist so a reader can jump to "the part that does X" without reading the
whole file top to bottom.

### 3. Purpose comments, not syntax comments

A comment explains **why**, never **what** — the code already says what, in a language a reader of
this codebase is assumed to know. `x = x + 1  # increment x` is banned. `# Kasa's linear
reformulation needs the offset term isolated on the RHS before the lstsq call` is the right level.
If deleting a comment wouldn't confuse a future reader, delete it.

### 4. Equation provenance

Every implemented equation cites its source: paper (short form, matching `refs/references.bib`'s
cite keys) and the specific equation number, inline next to the code that implements it. Not "per
the literature" — the actual equation number, so a reader can flip to the exact page and check.

### 5. Design-decision notes

Where a real alternative existed and a specific one was chosen, say why, next to the choice — not
in a separate design doc that drifts out of sync. "Uses the Kasa formulation, not Taubin's
bias-corrected variant, because X" belongs at the point of decision, not just in a journal entry
that nobody reads while modifying the code later.

### 6. Failure-mode notes

For anything with a known way to break (numerical instability at a certain conditioning, an
assumption that doesn't hold outside a certain regime), the docstring or a comment states the
failure mode and what the symptom looks like when it happens — not just that it "may not always
work."

### 7. Daily journal

`docs/journal/dayNN.md` — plain language, assumes the reader has not seen the code that day, and
has not necessarily read yesterday's entry either. Explains what was built, why, what was verified
(with the actual numbers/output, not "it works"), and anything left uncertain or deferred.

## Worked example: before and after

This is `Kasa's algebraic circle fit`, shown as it would look *without* the standard, then *with*
it, on the same function, so the standard is unambiguous rather than a list of adjectives.

### Before (fails the standard)

```python
import numpy as np

def fit_circle(x, y):
    # fit a circle
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x**2 + y**2
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx = c[0] / 2
    cy = c[1] / 2
    return cx, cy
```

This runs and is arguably even correct, but it fails every rule above: no module docstring, no
explanation of *why* this particular linear reformulation is being used instead of a nonlinear
least-squares fit, no equation citation, no note that this specific formulation becomes numerically
unstable on data that doesn't span much of the circle's arc, and a comment (`# fit a circle`) that
restates the function name instead of adding anything.

### After (follows the standard)

```python
"""
Kasa (1976) algebraic circle fit.

Recovers the center of a circle from a noisy point cloud (I, Q) that is assumed to lie
approximately on a circle -- used in this project as the classical baseline every
ellipse-fitting method (Halir & Flusser, Fitzgibbon, Taubin) is compared against, since
it is exactly what breaks once the signal is no longer circular (see Day 16 vs Day 9).

Pipeline position: called by the phase-recovery harness as Method 2 (kasa_circle_fit),
behind the common interface defined in Day 15's Protocol.
"""

from __future__ import annotations

import numpy as np


def fit_circle(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Returns the (center_x, center_y) of the best-fit circle through (x, y).

    Equation provenance: Kasa 1976, eq. 2-4 [kasa1976] -- the circle equation
    (x-a)^2 + (y-b)^2 = r^2 is expanded to x^2+y^2 = 2ax + 2by + (r^2-a^2-b^2), which is
    LINEAR in the unknowns [2a, 2b, (r^2-a^2-b^2)] and solvable by ordinary least squares,
    avoiding the nonlinear optimization a direct geometric fit would need.

    Design decision: Kasa's algebraic form is used here deliberately, not Taubin's (1991)
    bias-corrected variant, because this method's entire purpose in the benchmark is to be
    the naive baseline that later methods improve on -- using an already-improved variant
    here would understate the gap the benchmark exists to measure.

    Failure mode: this formulation is known to be numerically unstable when the input
    points span only a small arc of the circle (a near-degenerate case) -- the design
    matrix becomes ill-conditioned and the recovered center can be far from correct even
    though np.linalg.lstsq returns without error. Symptom: a large residual OR a
    plausible-looking but wrong center with no exception raised. See Day 3 for a direct
    numerical demonstration of this failure mode.
    """
    # ---- 1. Build the linear design matrix ----
    # Columns [x, y, 1] correspond to unknowns [2a, 2b, (r^2 - a^2 - b^2)].
    design = np.column_stack([x, y, np.ones_like(x)])
    target = x**2 + y**2

    # ---- 2. Solve the linear least-squares system ----
    coeffs, *_ = np.linalg.lstsq(design, target, rcond=None)

    # ---- 3. Recover the center from the solved coefficients ----
    center_x = coeffs[0] / 2
    center_y = coeffs[1] / 2
    return float(center_x), float(center_y)
```

Nothing about the *logic* changed between the two versions — the difference is entirely that a
reader who has never seen this file now knows what it does, why this specific formulation was
picked over real alternatives, where its citation is, where it sits in the larger project, and
exactly how it breaks. That's the bar every module in this project is held to.

## What this standard deliberately does NOT require

- Comments on trivial lines (`i += 1` needs no comment regardless of context).
- Restating a function's signature in prose inside the docstring body.
- A design-decision note where there was no real alternative under consideration.
- Padding failure-mode notes with hypothetical failures that can't actually occur given how the
  function is called elsewhere in this codebase.

The standard exists to make the *nontrivial* content (why, provenance, failure modes) legible, not
to maximize comment volume.
