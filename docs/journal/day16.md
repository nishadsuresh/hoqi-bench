# Day 16 — Kåsa circle fit (Method 2)

## What a circle fit assumes, and why it breaks under this week's own distortions

A circle has exactly one shape parameter that matters here: its center. `(I, Q)` traces a
circle of radius `V` centered at `(I0, I0)` because `I - I0 = V*cos(phi)`,
`Q - I0 = V*sin(phi)` — a circle, whatever `V` and `phi` happen to be, as long as both
channels share the same gain and are genuinely 90 degrees apart. Kåsa's method exploits this
directly: expanding `(I-a)^2 + (Q-b)^2 = r^2` gives `I^2+Q^2 = 2aI + 2bQ + (r^2-a^2-b^2)`,
*linear* in `[2a, 2b, (r^2-a^2-b^2)]`, so recovering the center is an ordinary least-squares
solve — no iteration, no nonlinear optimization, independent of how many fringes the record
spans or how the oscillation is shaped.

That "whatever V and phi happen to be" is exactly the assumption Week 2's classic
distortions violate. Amplitude imbalance scales the Q channel's oscillation independently of
I's — the trajectory is no longer equidistant from any single center at every angle, it's an
ellipse. Quadrature phase error mixes I's content into Q — same result, a tilted ellipse.
Kåsa's circle has no parameter for eccentricity or tilt at all; fitting a circle to an
ellipse doesn't fail outright, it just returns *some* center, biased by however elliptical
the data actually is. This is the entire research question Week 3 exists to explore: DC
offset alone (a genuine circle, just off-center) is exactly what a circle fit was built to
solve; amplitude imbalance and quadrature phase error are not.

## A corrected acceptance criterion — and why the plan's original one is untestable here

The build plan's stated criterion for this day is reproducing `quadrature-interferometer-sim`'s
"0.0395% displacement RMS error, 0.0019% vibration-frequency error." Neither number is a
Kåsa output — `0.0019%` comes from an FFT-based vibration-frequency detector, and `0.0395%`
comes from that project's *entire* pipeline (mains removal, unwrapping, displacement
conversion). hoqi-bench's method interface is `(I, Q) -> recovered phase`, nothing more;
there is no FFT stage and no mains-removal stage to reproduce those figures with. Using
that criterion here would test something this project doesn't build.

Replaced with a strictly tighter check on the thing this day actually does build: the ported
`_fit_circle_center` must return a **bit-identical** center estimate to an independent
reconstruction of the original algorithm, on real distorted signals — not a percentage match
on a downstream composite. That test passed exactly, at every named condition tried.

**Separately, non-blocking**, ran the original project's own `validate.py` directly (it still
exists, unmodified) to confirm the 0.0395% figure itself still reproduces: it does, to all
four decimal places (`0.0395%`, 1.5890 nm RMS on 4026.29 nm peak-to-peak). The published
number is real and stable — just not something this project's narrower method interface
could reproduce internally, which is why the acceptance test needed correcting rather than
the number needing re-chasing.

## A test that needed correcting, not the code

The first version of a "Kåsa should strongly outperform raw atan2 on `dc_offset`" test
asserted a ≥10x improvement and got only 2.8x. Rather than loosen the number, checked *why*:
the campaign's `dc_offset` axis holds `amplitude_ratio=1.1` and `quadrature_error_rad=0.1`
at their nonzero baseline while sweeping `dc_offset` — real baseline ellipse eccentricity
that biases Kåsa's circle-fit center even on this axis. Confirmed directly: on a *true*
circle (baseline distortion zeroed out), Kåsa recovers `dc_offset` to within ~500x of raw
atan2's error; on the real campaign condition, "only" ~2.8x. Both are now separate, passing
tests — one confirming the mechanism works as designed, one confirming (and quantifying) how
much baseline eccentricity degrades it in the actual swept conditions. A third test confirms
the complementary structural prediction directly: on `amplitude_ratio`, Kåsa shows no strong
correction at all, exactly as `docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` predicted in advance.

## What got built

- **`src/hoqi_bench/methods/kasa.py`** — Method 2, registered in `METHOD_REGISTRY`.
- **`tests/test_kasa.py`** — 4 tests: bit-identical port fidelity, near-exact dc_offset
  recovery on a true circle, the weaker-but-real recovery on the actual campaign condition
  (with the eccentricity-bias explanation), and the amplitude_ratio no-structural-advantage
  check.

## Status

97/97 tests passing (was 93; +4), ruff clean, mypy --strict clean (38 files). Day 17 next:
the Heydemann correction — the one method whose dominance on the three classic axes is
*tautological by construction* (`docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md` §1), so its own
docstring will need to say so plainly rather than let a later strong result look like a
finding.
