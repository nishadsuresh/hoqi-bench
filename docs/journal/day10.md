# Day 10 — DC offsets + geometric validation keystone

## Why the combined test matters more than the sum of the individual ones

Day 9 tested amplitude imbalance and quadrature phase error each on their own, and both passed. But
"each piece works alone" is not the same claim as "the pieces work together," and the gap between
those two claims is exactly where a specific, nasty class of bug lives: one that only shows up when
two transforms interact, and is invisible to any test that only ever exercises one transform at a
time. Day 8 already found a live example of this — the first guess at composing amplitude imbalance
and quadrature-error mixing was wrong, but wrong in a way that would have looked perfectly fine if
each transform had only ever been tested in isolation, since each one, alone, does exactly what its
own docstring claims. The bug was purely about how they combine.

Today's keystone test closes that gap by checking all three classic distortions — quadrature phase
error, amplitude imbalance, and now DC offset — applied together, against closed-form geometric
predictions derived independently of the transform code itself (via a covariance-matrix measurement
of the actual output data, the same method validated in Day 9). If this test passes, it's not just
evidence that each transform is individually correct; it's evidence that the specific, verified
composition order from Day 8 generalizes correctly to a genuinely combined case, not just the
two-transform case it was originally checked against.

## What got built

- **`dc_offset`** in `src/hoqi_bench/transforms.py` — the third classic Heydemann parameter, purely
  additive, identity at `(0, 0)`, applied last in the pipeline (commutes with the other two
  algebraically, so its position is a construction-order convention, not a mathematical requirement
  — documented as such, not implied to be load-bearing when it isn't).
- **`tests/test_forward_geometry.py`** — the keystone test. Applies all three transforms together,
  in the documented order, then checks the resulting point cloud's center (trivial closed-form: full
  period average of cos/sin is exactly zero, so center is just `mean_intensity + offset`) and shape
  (covariance matrix, closed-form derived via sympy before writing the test: `Cov = (A^2/2) *
  [[1, g*sin(eps)], [g*sin(eps), g^2]]`) against the actual measured data — across four distinct,
  non-trivial parameter combinations, not just one that might pass by coincidence.

## The result, honestly reported

All three tests passed on the first real run. This is worth stating plainly rather than treated as
unremarkable: it means the composition order verified for two transforms in Day 8 genuinely
generalizes to three, which was not guaranteed in advance — the covariance-matrix formula derived
today is a real, independent mathematical claim about the three-way combination, not just an
extension of the two-way one, and it could easily have failed if some interaction between DC offset
and the other two behaved differently than assumed. It didn't, and that's a real, checked result.

## What this test does NOT cover, and why that's fine for today

Noise (Days 11-12), power-law effects (Day 13), and hysteresis (Day 14) aren't part of this
keystone check — each of those gets its own combined-validation treatment once it exists (Day 14's
task explicitly runs a full forward-model validation across everything). Today's keystone is
deliberately scoped to the three classic, static, Heydemann-model distortions, since those are the
ones with a clean closed-form geometric prediction to check against; the later distortions will need
their own validation strategy suited to what they actually do (a noise model's validation looks
different from a shape-changing distortion's).
