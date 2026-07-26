# Deriving the Heydemann correction from first principles

This derives, from scratch, the correction that recovers true phase from a distorted quadrature
interferometer signal. It assumes you know trigonometry (angle-addition formulas, `atan2`) but
nothing about interferometry. Every step says what's being done and *why*, not just the algebra.

Provenance: this is a from-scratch derivation, not a copy of Heydemann's (1981) original equations
— that paper is paywalled and wasn't accessible for this project (see `notes/heydemann_1981.md`).
What follows is derived independently, then cross-checked at the end against how the same result
is *described* (not equation-numbered) in accessible secondary sources, including the
already-implemented and tested version of this same correction in the
`quadrature-interferometer-sim` project this benchmark extends from.

## 1. The ideal signal, and why it needs no correction

A quadrature interferometer measures two signals as a mirror moves, `I` and `Q`, generated 90
degrees out of phase with each other so that plotting `Q` against `I` traces a circle as the true
phase `phi` sweeps through its range:

```
I(phi) = cos(phi)
Q(phi) = sin(phi)
```

(Real signals also have a mean intensity offset and an amplitude/contrast scale factor — those are
folded in below as `I0`/`Q0` and `A` once distortion is introduced; for the *ideal* case they're
constants that don't change the argument, so they're dropped here for clarity.)

Because `(cos(phi), sin(phi))` is exactly a point on the unit circle at angle `phi`, recovering the
phase is immediate:

```
phi_recovered = atan2(Q, I) = atan2(sin(phi), cos(phi)) = phi
```

`atan2` (rather than a plain `arctan(Q/I)`) is what makes this unambiguous across the full range —
it uses the sign of both `I` and `Q` to place `phi` in the correct quadrant, so there's no
`+phi`/`-phi` or `phi`/`phi+pi` confusion the way a single-detector, single-argument `arctan` would
have.

## 2. The distorted signal — where the three error sources come from

Real hardware doesn't produce a perfect circle. Three independent, static imperfections distort it,
each with a clear physical cause:

- **Amplitude imbalance (`g`)**: the two photodetector channels don't have identical gain, so one
  channel's swing is systematically larger or smaller than the other's. Ideally `g = 1`.
- **Quadrature phase error (`eps`)**: the two channels aren't exactly 90 degrees apart — some
  optical or electronic imperfection makes the real angle `90 + eps` degrees instead. Ideally
  `eps = 0`.
- **DC offset (`I0`, `Q0`)**: each channel has its own bias/rest level, from stray light, detector
  bias voltage, etc. Ideally `I0 = Q0 = 0`.

Writing the distorted signal with these three sources (and an amplitude scale `A` that isn't itself
one of Heydemann's three "shape" errors, just the physical signal size):

```
I(phi) = I0 + A * cos(phi)
Q(phi) = Q0 + A * g * sin(phi + eps)
```

At `g=1, eps=0, I0=Q0=0` this is exactly the ideal signal from Section 1 — a check worth keeping in
mind, since it's exactly what `hoqi-bench`'s Day 1 forward-model transforms must reduce to at zero
distortion (their "identity at zero" acceptance test).

Geometrically, this traces an ellipse instead of a circle: shifted off-center by `(I0, Q0)`, with
one axis scaled by `g` relative to the other, and tilted because the two channels are no longer
exactly perpendicular.

## 3. Removing the DC offset (why: it's the easiest error to remove, and removing it first
simplifies everything after)

Subtracting the known (or fitted) offsets gives a signal centered at the origin:

```
I' = I - I0 = A * cos(phi)
Q' = Q - Q0 = A * g * sin(phi + eps)
```

This step is purely a translation — it doesn't touch the amplitude imbalance or phase error at all,
which is exactly why it's done first: it's the one distortion source that doesn't interact
algebraically with the other two, so isolating it first leaves a strictly simpler problem (a
tilted, scaled ellipse *centered at the origin*) for the next two steps.

## 4. Expanding the phase error (why: `sin(phi + eps)` mixes `phi` and `eps` together — expanding
it separates them, so `eps` can be isolated as a known correction factor rather than trapped inside
a sine argument alongside the unknown we actually want, `phi`)

Using the angle-addition identity `sin(a+b) = sin(a)cos(b) + cos(a)sin(b)`:

```
sin(phi + eps) = sin(phi)*cos(eps) + cos(phi)*sin(eps)
```

Substituting into `Q'`:

```
Q' = A*g*cos(eps)*sin(phi) + A*g*sin(eps)*cos(phi)
```

## 5. Substituting in what's already known (why: `A*cos(phi)` is exactly `I'` from Step 3 — reusing
it means the equation for `Q'` no longer has `cos(phi)` in it at all, only the one remaining unknown
we need, `A*sin(phi)`)

Since `I' = A*cos(phi)`:

```
Q' = A*g*cos(eps)*sin(phi) + g*sin(eps)*I'
```

## 6. Solving for the missing piece (why: this isolates `A*sin(phi)` — the exact analogue of `I'`
that the ellipse distortion had been hiding inside a scaled, phase-shifted combination)

Rearranging:

```
Q' - g*sin(eps)*I' = A*g*cos(eps)*sin(phi)

A*sin(phi) = (Q' - g*sin(eps)*I') / (g*cos(eps))
```

This step requires dividing by `g*cos(eps)` — which only works if neither factor is zero. That
condition turns out to matter a lot; see Section 8.

## 7. The corrected signal is exactly the ideal circle, scaled by `A`

Define:

```
I_c = I'                                       = A*cos(phi)
Q_c = (Q' - g*sin(eps)*I') / (g*cos(eps))       = A*sin(phi)
```

`(I_c, Q_c)` is now *exactly* `(A*cos(phi), A*sin(phi))` — a point on a circle of radius `A`, at
angle `phi`. All three distortions (offset, gain imbalance, phase error) have been undone. Phase
recovery is now the same as the ideal case in Section 1:

```
phi_recovered = atan2(Q_c, I_c) = atan2(A*sin(phi), A*cos(phi)) = phi
```

(exactly, for any `A > 0` — `atan2` only depends on the *signs and ratio* of its two arguments, not
their absolute scale, so the leftover amplitude factor `A` never affects the recovered phase.)

## 8. The assumption this correction depends on (don't skip this — it's scientifically load-bearing)

Step 6 divides by `g * cos(eps)`. That means the correction above is only valid when:

```
g != 0        (the Q channel has some nonzero gain -- true for any working detector)
cos(eps) != 0  <=>  eps != +90 degrees and eps != -90 degrees
```

The second condition is the interesting one. `eps = +-90` degrees is exactly the case where the
"quadrature" phase error is so large that the two channels have collapsed onto the *same* axis
instead of being perpendicular — geometrically, the ellipse degenerates into a line segment, and
there's no longer enough information in `(I, Q)` to recover `phi` uniquely (many different phases
project onto the same point on that line). The correction doesn't fail suddenly at exactly `eps =
90` — `cos(eps)` shrinks continuously as `eps` approaches 90 degrees, so the correction becomes
numerically fragile (dividing by a small number amplifies any noise or fitting error in `g` and
`eps` themselves) well before it becomes mathematically undefined. This is exactly the kind of
near-degenerate case `hoqi-bench`'s later robustness testing (Day 17's degeneracy test, Day 20's
robustness matrix) needs to probe directly, not just note here in passing.

## 9. Cross-check against secondary sources

This derivation was checked against two independent secondary descriptions of the same correction,
both post-dating and citing Heydemann's original result rather than being it directly:

1. **Lehmann et al. 2025** (`notes/lehmann_2025.md`) describes correcting the same three error
   types (gain mismatch, quadrature phase error, DC offset) by fitting the distorted ellipse's
   parameters and normalizing back to a circle — consistent with the structure derived above,
   though that paper doesn't walk through the algebra step by step the way this document does.
2. **The already-implemented and tested version of this exact correction**, in the
   `quadrature-interferometer-sim` project's `apply_ellipse_correction` function (that project's
   `src/analysis.py`), uses the identical formula derived independently here:
   `I_c = I - dc_i`, `Q_c = (Q - dc_q - g*sin(eps)*I_c) / (g*cos(eps))`. That implementation was
   built and verified (against hand-constructed synthetic ellipses with known parameters, and
   against a real bug where an early draft of the derivation silently assumed unit amplitude scale
   — see that project's log) in an earlier, separate project, before this derivation was written
   fresh here. The fact that an independent from-scratch derivation lands on the exact same formula
   is a real, meaningful cross-check, not a coincidence to wave away — it's the strongest evidence
   available (short of Heydemann's original paper) that this is correct.

No discrepancy was found between this derivation and either secondary source.
