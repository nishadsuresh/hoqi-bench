# Day 5 — Experimental design and config schema

## What a parameter sweep is, and why the choice of ranges determines what conclusions are even possible

A parameter sweep is just running an experiment many times, each time changing one thing (say, how
badly a detector's gain is mismatched) while measuring what happens to the result. The entire point
is to find out *how sensitive* the outcome is to that one thing — does a little bit of gain mismatch
barely matter, or does everything fall apart the moment it's nonzero? But that question can only be
answered as far as the range actually tested. If a sweep only tests gain mismatch up to 5% and the
real, interesting breakdown happens at 25%, the experiment will report "looks fine" and simply never
find out otherwise — not because the method is actually fine, but because nobody looked far enough.
This is why every range in `docs/experimental_design.md` is justified rather than picked by feel,
and why the ones that *aren't* solidly grounded in a real measured number are flagged as such rather
than presented with false confidence.

## What got built

1. **`docs/experimental_design.md`** — forward-model equations, parameter ranges (with justification
   for each, honestly split into "grounded in Lehmann et al. 2025's actual reported numbers" versus
   "a reasoned engineering choice, not read from any paper"), the sweep structure (one-factor-at-a-time
   axes plus one justified 2D interaction grid, not a full combinatorial cross), metrics, and the
   statistical protocol.
2. **`src/hoqi_bench/config.py`** — a TOML sweep-config loader with real validation: 9 distinct ways
   a config can be malformed, each producing a specific error message, plus a `total_runs()`
   calculator so the cost of a sweep is visible and checked *before* it's run, not discovered by
   waiting for it to finish (or not).
3. **`configs/main_campaign.toml`** — the actual proposed config for the main campaign, and
   `configs/smoke.toml` — a tiny config for Day 0's smoke-test tooling and Day 26's end-to-end test.
4. **`tests/test_config.py`** — 14 tests, including the specific claim `docs/experimental_design.md`
   makes by hand (49 conditions, `total_runs = 10,290`), confirmed programmatically rather than
   trusted from arithmetic done in a markdown file.

## Why the sweep isn't a full factorial

Crossing every proposed axis against every other would be 2,500 conditions before even multiplying
by 7 methods and 30 seeds — 525,000 individual runs. That's not "thorough," it's mostly waste: most
pairs of parameters don't meaningfully interact, so testing every combination burns runtime without
buying much information. The one exception — arc coverage and noise level, which Day 3's findings
showed actually do interact in ways neither does alone — gets the one full 2D cross the design
includes. Everything else is one-factor-at-a-time against a fixed "typical hardware" baseline. This
brought the real total down to 49 conditions, 10,290 runs — checked by the `total_runs()` calculator
built today, not asserted by hand.

## Approval outcome

Per this day's own instructions, the proposed ranges were presented for approval rather than
silently locked in. Nishad approved both engineering-judgment ranges (quadrature phase error, DC
offset) as originally proposed, and asked for the sweep to be expanded on four fronts: finer
per-axis resolution, more Monte Carlo seeds, more interaction grids, and folding the two Day 20
"stretch" methods (Taubin, Köning/Wimmer/Witkovský) into the required main-campaign method set.

The approved design: 10-point axes for amplitude ratio, quadrature error, and noise (up from 5),
9 points for arc coverage and 8 for DC offset (up from 5 and 4), 50 seeds per condition (up from
30), three 2D interaction grids instead of one (adding amplitude-ratio-vs-quadrature-error and
amplitude-ratio-vs-noise, alongside the original arc-vs-noise), and all 7 methods required rather
than 5 required + 2 optional. New total: **337 conditions x 7 methods x 50 seeds = 117,950 runs**
— still fast at this problem size (each run is a cheap ellipse fit on ~60 points), so no runtime
concern despite the roughly 11x increase in scope.

One thing worth flagging plainly rather than quietly absorbing into the bigger number: promoting
Köning/Wimmer/Witkovský's method from "stretch, if time allows" to "required" runs ahead of how
well that method is actually understood right now — `notes/koning_2014.md` is honest that it's
currently title/abstract-level knowledge only, not enough to implement faithfully yet. This is now
a real dependency for Day 19-20: either get real access to that 2014 paper before implementing it,
or build a best-effort version explicitly labeled as an approximation rather than a faithful
reproduction. Making required something that isn't fully understood yet is a real scope risk this
project's own documentation standard (equation provenance, honest failure-mode notes) would call
out if it showed up in someone else's plan — so it's named here rather than quietly carried
forward.
