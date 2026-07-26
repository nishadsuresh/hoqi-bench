# Day 9 — Amplitude imbalance + quadrature phase error transforms

## The geometric intuition: why these two imperfections turn a circle into a tilted ellipse

Picture the ideal (I,Q) signal as a point walking around a perfect circle as phase sweeps through
its range — I and Q are just cosine and sine of the same angle, always the same distance from
center. Amplitude imbalance is what happens when one detector channel is more sensitive than the
other: the circle gets squashed along one axis, becoming an ellipse that's still aligned with the
I/Q axes (no tilt), with the amount of squashing given directly by the gain ratio.

Quadrature phase error is different in kind, not just degree. It happens when the two detectors
aren't quite reading at a true 90-degree angle to each other — some of what should be "purely I"
leaks into the Q reading, and vice versa. This isn't a squash, it's a *shear*: some of the I signal's
own oscillation gets mixed into Q. The genuinely interesting geometric fact (derived and verified
today, not assumed): this kind of mixing always tilts the resulting ellipse by *exactly* 45 degrees,
regardless of how large the phase error is — only the ellipse's axis ratio changes with the error's
size, never the tilt angle. That's a real, non-obvious consequence of the trigonometry, not
something guessable from the plain-language description alone.

## What got built

- **`src/hoqi_bench/transforms.py`** — `amplitude_imbalance` and `quadrature_phase_error`, each an
  exact identity at its zero/one-valued default, each citing Heydemann 1981 and Day 2's derivation
  for the exact equation it implements.
- **`tests/test_transforms.py`** — for each transform, a check against an *independently derived*
  geometric property (via a covariance-matrix/PCA method on the resulting point cloud, not a
  restatement of the transform's own formula): amplitude imbalance produces a known axis ratio with
  no tilt; quadrature phase error produces a known 45-degree tilt with a known axis ratio, checked
  across five different error magnitudes, not just one.

## Two real bugs caught today, both root-caused rather than patched around

**First**, before writing any test, the exact geometric prediction for quadrature phase error was
derived with sympy rather than guessed: for `x=A*cos(t), y=A*sin(t+eps)`, the covariance matrix is
`(A²/2)*[[1, sin(eps)], [sin(eps), 1]]`. This was actually the *second* attempt — Day 8's pipeline
architecture work had already shown that trusting an intuitive-but-unverified guess about
trigonometric composition leads to real errors, so this day's design didn't repeat that mistake:
the covariance prediction was checked symbolically before a single test was written against it.

**Second**, a bug that *did* make it into a first test draft: the test initially compared the
covariance matrix's eigenvalue ratio directly against the measured semi-axis ratio and failed
(1.43 measured vs. 2.04 "expected"). Rather than loosening the tolerance to make the number pass —
which would have hidden a real transcription error — the actual cause was tracked down: eigenvalues
of a covariance matrix are proportional to *squared* semi-axis length, not semi-axis length itself,
so the correct comparison needed a square root that the first draft's formula was missing. Fixed the
formula, reran, and it passed cleanly — the transform code itself was correct the entire time; only
the test's own arithmetic had the bug. This is exactly the "when a fix changes a number, re-verify;
when a test fails, find out whether the code or the test is wrong before changing either"
discipline this project is built on, and it's worth naming plainly that today it was the test, not
the implementation, that needed fixing.

## What's still ahead

Both transforms are currently standalone functions, not yet wired into `pipeline.apply_pipeline` as
bound `Transform` closures — that wiring, plus DC offset (the third classic Heydemann parameter) and
the combined keystone validation across all three at once, is Day 10's task, not jumped ahead into
today.
