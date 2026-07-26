# Day 7 — Package scaffold, CI, ideal model port (Week 1 close)

## Why research code benefits from CI the same way production code does

It's tempting to think a benchmark script just needs to run once, correctly, on the author's own
machine. But the entire point of this project is that someone else should be able to clone it,
install it, and get the same numbers — and "works on my machine" is exactly the failure mode that
breaks that promise silently. A CI pipeline that runs lint, strict type-checking, and the full test
suite on every push, on two different Python versions, catches the gap between "I tested this
locally" and "this actually works from a clean checkout" before it becomes someone else's problem
six weeks from now on Day 35's clean-clone reproduction check.

## What got built

- **`pyproject.toml`** — a proper `src/` layout package, installable via `pip install -e ".[dev]"`,
  with `ruff` (line length 100, targeting Python 3.10) and `mypy --strict` both configured and
  passing clean.
- **`.github/workflows/ci.yml`** — runs lint, strict type-check, and the full test suite (with
  coverage) on every push and PR, across both Python 3.10 and 3.11 — deliberately testing both,
  since Day 0 already found this machine only has 3.10 and the `tomllib`/`tomli` fallback needs to
  actually work on both, not just the one available locally.
- **`src/hoqi_bench/forward_model.py`** — the ideal, distortion-free interferometer model, ported
  from `quadrature-interferometer-sim`.

## The acceptance test, run for real

Day 7's instruction was explicit: the port must reproduce the original project's exact
0.000000% fringe-spacing result, or stop and report which of the two is wrong. Running the ported
test:

```
Expected fringe spacing (lambda/2): 316.4000 nm
Measured mean fringe spacing:       316.4000 nm  (31 fringes)
Relative error: 0.000000%
```

Bit-for-bit identical to the original — same 31 fringes, same exact zero error, not just "under
tolerance." Two additional tests were written beyond the direct port: confirming the ideal (I,Q)
signal traces an exact circle in the plane (the property every later ellipse-fitting method depends
on being violated by distortion), and a zero-displacement degeneracy check that later distortion
transforms' own "identity at zero" tests will build on.

## What's committed as of tonight

All 17 tests pass, `ruff check` and `mypy --strict` both run clean, and the CI workflow is live —
this closes Week 1. Every deliverable from Days 0-6 (VS Code workspace, documentation standard,
verified literature notes with two real corrections caught, a from-scratch symbolically-verified
derivation, an honestly-reported numerical-instability study, a related-work search with a
reproducible query log, and an adversarially-reviewed preregistration) is now sitting on top of a
real, tested, CI-backed package rather than a collection of standalone scripts.
