# Day 8 — Composable transform architecture

## What a "forward model" is, and why composable transforms make it trustworthy

A forward model is the piece of a simulation study that goes the "easy" direction: given a known
true signal and known distortions, generate what a real detector would actually measure. (The hard
direction, which every method in this benchmark attempts, is the reverse — given the messy measured
signal, recover the true one.) The trustworthiness problem is that the forward model is the thing
every other number in this project is checked against — if it's subtly wrong, every method looks
better or worse than it really is, uniformly, in a way that's very hard to notice from the results
alone.

Writing the forward model as one large function with every distortion (amplitude imbalance,
quadrature error, DC offset, noise, power-law effects, hysteresis) hardcoded inline would make this
risk worse, not better: a bug in the noise term could silently corrupt the amplitude-imbalance term
too, and there'd be no way to check "does turning off distortion X actually turn off exactly
distortion X" without reading the entire function line by line. Separating each distortion into its
own small, independently testable transform — each checkable against a known analytic property in
isolation (Days 9-14) — means a bug in one transform can't hide inside another, and "zero distortion
reproduces the exact ideal signal" (today's keystone test) is a single, precise, checkable claim
instead of something to just hope is true of one big function.

## What got built

- **`src/hoqi_bench/pipeline.py`** — a `Transform` type (any function taking `(I, Q)` and returning
  distorted `(I, Q)`) and `apply_pipeline`, which composes a sequence of transforms in order. With
  zero transforms, it's a pure passthrough.
- **`tests/test_pipeline.py`** — the keystone test (empty pipeline is bit-identical to Day 7's
  ideal model, checked with `np.array_equal`, not an approximate tolerance), a determinism check,
  and a minimal check that the composition mechanism genuinely applies transforms in sequence
  (each seeing the previous one's output) using two trivial order-sensitive stub functions.

## A real design mistake caught before it became documentation

The instructions for this day didn't just ask for "some order, documented" — they asked for the
order to be *justified*, since order matters physically. Working through what that justification
should say surfaced a genuine mistake: the first, intuitive guess was "amplitude imbalance first,
then quadrature-phase-error mixing." Checking this against Day 2's own combined formula
symbolically (rather than trusting the intuition) showed it's wrong — it leaves a residual term
that only vanishes when the amplitude ratio is exactly 1, meaning it silently reproduces the wrong
distorted signal for every other case. The correct order, verified to match Day 2's formula exactly
(symbolic difference of zero, confirmed numerically too): quadrature-error mixing happens first, on
the still-unscaled signal, and amplitude-imbalance scaling is applied second, to whatever signal —
mixed or not — physically reaches that channel. This matches the actual physical picture (channel
gain is downstream of the optical quadrature relationship between the two channels) and it would
have been very easy to document the wrong order confidently if it hadn't been checked before
writing it down. `src/hoqi_bench/pipeline.py`'s module docstring keeps both the correct order and a
short account of why the first guess was wrong, rather than only showing the final answer.

## What's still a placeholder

`TRANSFORM_ORDER` in `pipeline.py` names all seven planned transforms (quadrature-phase-error
through hysteresis) but only documents their intended sequence — none of them are implemented yet.
That's Days 9-14's job; today's scope was strictly the architecture and the keystone test, as
instructed, not jumping ahead into transforms that haven't been designed and verified yet.
