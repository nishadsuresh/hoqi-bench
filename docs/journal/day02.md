# Day 2 — Heydemann derivation, derived and symbolically verified

## What got built

1. **`docs/derivations/heydemann.md`** — a from-scratch, step-by-step derivation of the correction
   that recovers true phase from a distorted (amplitude-imbalanced, phase-error'd, DC-offset)
   quadrature signal, written for a reader who knows trigonometry but nothing about
   interferometry. Every step explains *why* it's being done, not just what.
2. **`scripts/verify_heydemann_derivation.py`** — a sympy script that reconstructs the same
   derivation symbolically and checks it mechanically, independent of whether the by-hand algebra
   "looks right."

## The geometric intuition, in plain language

Imagine the true phase as a point walking around a circle — that's the ideal, undistorted signal.
Now imagine three things going wrong with the two detectors reading that circle out: one detector
is a bit more sensitive than the other (so the circle gets squashed into an oval along one axis),
the two detectors aren't quite reading at a perfect right angle to each other (so that oval also
gets tilted), and each detector has its own small constant bias (so the whole shape gets shifted
off-center). All three together turn a clean circle into a tilted, off-center ellipse.

The correction works by literally undoing those three things in reverse, one at a time: shift the
ellipse back to center (undoes the offset), then use a bit of trigonometry to "unmix" the tilt and
the squashing, which turns out to require nothing more exotic than the angle-addition formula for
sine that shows up in any trig class. Once all three are undone, what's left is exactly the
original clean circle again — scaled up or down depending on how bright the signal was, but a
circle nonetheless — and reading the phase off a circle is the easy, unambiguous part.

## What "verify symbolically" actually caught (or would have caught)

Running the sympy script confirmed, mechanically and independently of the hand-derivation:

```
I_c - A*cos(phi) simplifies to: 0
Q_c - A*sin(phi) simplifies to: 0
```

Both differences simplify to *exactly* zero, for every value of the distortion parameters (not
just for one numeric example) — meaning the corrected signal really is the ideal circle, scaled by
`A`, exactly as claimed. This is a stronger check than plugging in a few numbers: sympy is proving
this holds as an algebraic identity, not just for a handful of test cases.

The script also directly confirms the one assumption the derivation depends on isn't just an
unmotivated caveat: the correction divides by `g * cos(eps)`, and that expression really does equal
zero exactly when `eps` is `+90` or `-90` degrees (checked symbolically: `cos(pi/2)` and
`cos(-pi/2)` both simplify to `0`). That's the case where the two detector channels have become so
misaligned they're no longer really "quadrature" at all — they've collapsed onto the same axis, and
there's genuinely not enough information left in the signal to recover phase uniquely no matter how
clever the math is. This isn't a limitation of this particular correction; it's a real, physical
limit on what any correction could do with that data.

A separate sanity check confirmed the correction is a true no-op at zero distortion (`g=1, eps=0,
I0=Q0=0` gives back exactly the original uncorrected signal) — the same "identity at zero"
requirement the forward-model transforms in Week 2 are held to.

If the derivation *hadn't* simplified cleanly, the plan was to investigate what assumption would be
needed to force it to hold and treat that as a real finding worth documenting rather than a bug to
quietly patch — that didn't end up being necessary here, since it verified cleanly on the first
attempt, but it's worth stating that the script was written to surface that kind of problem, not
just to print "PASSED" regardless.

## Cross-check against secondary sources

Since Heydemann's original 1981 paper is paywalled (see `notes/heydemann_1981.md`), this derivation
was cross-checked against two things instead: how Lehmann et al. 2025 describes the same three
error types and correction concept (consistent, though that paper doesn't show step-by-step
algebra), and — more directly informative — an already-built and tested implementation of this
exact correction from an earlier, separate project (`quadrature-interferometer-sim`'s
`apply_ellipse_correction` function). That implementation used the identical final formula this
derivation arrived at independently, which is a real point in favor of both being correct, not a
coincidence to note in passing. No discrepancy was found between this derivation and either source.
