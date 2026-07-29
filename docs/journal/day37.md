# Day 37 — README rewrite, and every command verified by running it

Rewrote `README.md` for a first-time external reader, using yesterday's audit findings as a
complete, verified punch list rather than rediscovering the gaps from scratch.

## What changed

- **Status line corrected**: "Weeks 1-3 of 6, no campaign data exists yet" → "Weeks 1-5 of 6
  complete," with the actual current test count (251, verified via `pytest --collect-only -q`, not
  the stale 136).
- **A new, prominent "What this benchmark does NOT answer" section**, placed directly after the
  abstract — not at the bottom, per the plan's own instruction. States plainly: the preregistered
  campaign never tested direction-dependent hysteresis (only radial inflation), RQ6's design chart
  needed a supplementary grid, RQ5 covers only the sub-fringe regime, and no Poisson-vs-Gaussian
  ranking difference proved statistically real. A benchmark whose contribution is reproducibility
  infrastructure is stronger for saying this where a reader will actually see it.
- **A new "Key results, at a glance" section**, summarizing RQ1-RQ6's actual headline findings —
  previously the README said nothing about what the campaign found, only what it planned to run.
- **Setup instructions rewritten around `uv`** as the primary path, with the plain `venv`+`pip`
  route stated as equally correct where it works — per Day 35's finding that `python -m venv` fails
  outright on this dev machine.
- **Project structure section fully updated**: 12 new/renamed modules since the version README
  described (`waveforms.py`, `fisher_information.py`, `harmonics.py`, `aggregate.py`,
  `reference_scale.py`, `statistics.py`, `runner.py` among them), 8 new analysis scripts, 2 new
  supplementary configs, and every doc added since Week 3.
- **Honest limitations section extended** with the Week 5 findings (the four-RQ supplementary-fix
  point) and the D4 byte-exactness finding, which the old README never mentioned at all.

## Every command in the README verified by running it, not assumed

Built a fresh `.venv` in the actual project directory (gitignored, cleaned up after) and ran every
single command the README now specifies, in order: `uv venv`, `uv pip install -e ".[dev,validation]"`,
`pytest -q` (249 passed, 2 xfailed — exact match to the number now stated in the README),
`ruff check`, `mypy`, and both standalone verification scripts
(`verify_heydemann_derivation.py`, `explore_ellipse_constraints.py`) — all exited clean. Confirmed
via `git status` that the only change left behind was the README edit itself; the exploration
script's regenerated PNG plot was byte-identical to the committed one (git saw no diff), consistent
with this project's own determinism guarantees.

## Verification

249 passed, 2 xfailed (dev venv, unchanged from Day 36 — this task touched only documentation).
`ruff check`, `mypy --strict` clean.

## What's next

Task 11 (Day 38): the abstract and `notes/contribution_claim.md` — the contribution claim's
Lehmann-extension half needs updating to reflect that the preregistered campaign only tested one of
the two claimed nonlinearity mechanisms, per Day 32's finding.
