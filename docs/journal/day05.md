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

## The two things flagged for a second look

Per this day's own instructions, the proposed ranges are presented for approval, not silently
locked in. `docs/experimental_design.md`'s "Approval requested" section names the two ranges that
are engineering judgment calls rather than numbers pulled from Lehmann et al. 2025 (quadrature phase
error and DC offset), plus the hysteresis-magnitude sweep for the same reason, and the `total_runs =
10,290` figure as worth a sanity check. Waiting on that before Day 6 locks anything into
`docs/PREREGISTRATION.md`.
