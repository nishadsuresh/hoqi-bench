# Day 39 — packaging dry-run: everything that doesn't need Nishi's credentials, verified

## Build

`python -m build` produced both `dist/hoqi_bench-0.1.0.tar.gz` (sdist) and
`dist/hoqi_bench-0.1.0-py3-none-any.whl` (wheel) cleanly.

**Contents, verified by direct inspection, not assumed from the build log:**
- **sdist**: contains `LICENSE`, `CITATION.cff`, and `CHANGELOG.md` — confirmed via `tar tzf`.
- **wheel**: contains `LICENSE` (at `hoqi_bench-0.1.0.dist-info/licenses/LICENSE`, modern
  setuptools' automatic license-file handling) but **not** `CITATION.cff` or `CHANGELOG.md`.
  Checked whether this is a defect before treating it as one: it isn't — this is standard Python
  packaging convention. A wheel is the installable *package* (source + license metadata); project-
  level documentation like a changelog or citation file belongs in the sdist/repository, not copied
  into every user's installed site-packages. Numpy, pandas, and every other wheel on PyPI follow the
  same convention. Recorded here so this doesn't get miscategorized as a packaging gap later.

## Validation

`twine check dist/*` — **PASSED** on both artifacts (installed via pip, not previously present in
the dev venv).

## Installation and smoke test

Built a fresh `uv venv` (Python 3.10, outside the repo, cleaned up after) and installed the **built
wheel artifact itself** (`uv pip install dist/hoqi_bench-0.1.0-py3-none-any.whl`) — not
`pip install -e .`, which only proves the source tree works, not that the actual packaged artifact
does. Every pinned dependency resolved to its exact declared version with no conflicts. End-to-end
smoke test: imported `hoqi_bench`, confirmed `hoqi_bench.__version__ == "0.1.0"` (matches
`pyproject.toml` exactly), listed `METHOD_REGISTRY` (all 7 methods present), generated a synthetic
signal via `forward_model.simulate_ideal_interferometer`, and ran a real Kasa fit against it through
`fit_by_name` — completed without error, `failed=False`, correctly-shaped output.

## Python 3.11

No 3.11 interpreter is available on this dev machine (consistent with every earlier day's notes on
this environment). Not re-verified locally — CI's 3-OS × 2-Python matrix has run this exact pinned
dependency set on 3.11 continuously throughout Weeks 5-6, green on every push including today's.
Treated as already covered by the existing, continuously-green CI evidence rather than re-proven
redundantly.

## What could not be done today — a new blocker, not previously named as such

**Uploading to TestPyPI requires a TestPyPI account and API token.** This project's plan named
Day 40 (real PyPI) and Day 41 (Zenodo) as explicitly requiring Nishi's credentials, but did not
separately flag that the TestPyPI *dry-run* step itself has the same requirement — there is no
anonymous or credential-free path to an actual upload, even to the test index. Everything that does
**not** require an account has been completed and verified above (build, content inspection,
`twine check`, and — arguably more informative than a round-trip upload would have been — a direct
install-and-run test of the actual built wheel from local disk). The one thing genuinely deferred is
the specific act of publishing to an index, which Day 40 already required Nishi for regardless.

## Verification

No source code changed today. `dist/` and `build/` are gitignored, as they were before — nothing
new to commit besides this journal entry.

## What's next

Task 13 (Day 40): the real PyPI release — requires Nishi's PyPI API token, as already flagged.
Given today's dry-run found no defects, this should be a clean upload of the exact artifacts already
built and verified.
