# Day 26 — Reproducibility hardening, and pinning the exact gap Day 24 found

## Why this is the highest-leverage day, not busywork

`docs/WEEK1-2_AUDIT.md` item B5 calls reproducibility this project's *stated contribution*. Every
test written so far checks *internal* consistency — run the campaign twice, get the same bytes.
That's necessary but doesn't actually evidence the claim "this benchmark is reproducible": it only
proves the campaign doesn't fight itself. It says nothing about whether the same commit produces
the same numbers on a different machine, a different OS, or six months from now after a dependency
bump. Today closes that gap directly, using a defect Day 24 already handed us as the concrete
motivating example rather than a hypothetical.

## Pinning: not a floor, exact versions

`pyproject.toml` previously specified floors (`pandas>=2.0`, etc.). Day 24 showed exactly why that
isn't "reproducible": the same commit resolved pandas 2.3.3 on CI's Python 3.10 job and pandas
3.0.5 — a major version — on the 3.11 job. A floor doesn't pin an environment, it just describes
the oldest thing that happens to still work today.

Every core dependency is now pinned to an exact version, verified (via PyPI's own wheel listing,
not assumed) to actually ship wheels for both Python 3.10 and 3.11 across Linux, macOS, and
Windows — the same three-OS matrix this day adds to CI. Pinning a version that's missing a wheel
for one of those six cells would just move today's failure to install-time instead of run-time, so
each one was checked before being written down: numpy 2.2.6, scipy 1.15.3, sympy 1.14.0 (a pure
Python `py3-none-any` wheel, no per-platform concern), matplotlib 3.10.9, pandas 2.3.3, pyarrow
25.0.0. Dev tooling (pytest, ruff, mypy, pandas-stubs, etc.) pinned the same way, since a ruff or
mypy version bump landing silently between two CI runs is its own small reproducibility gap.

Reinstalled locally against the new pins and reran the full suite before touching anything else —
181 passed, ruff and mypy clean, exactly as before pinning. Pinning changed nothing about behavior
today; it only removes the freedom for a *future* install to resolve something different.

## The new CI job, and what it actually checks that nothing else does

Added `cross-platform-reproducibility`: a 3-OS × 2-Python-version matrix (6 cells) that installs
the package and runs exactly one test — the smoke campaign, hashed, compared against a single
committed SHA-256 constant recorded in `tests/test_reproducibility.py`. This is deliberately *not*
a second full lint/typecheck/test pass on six platforms; that would just duplicate the existing
`lint-type-test` job six times over for no new information. The one thing this job checks that
nothing else can is whether the actual floating-point output — the numbers, not just the code —
match across environments.

**An honest note on "fresh clone," which the plan named as its own separate step.** GitHub
Actions runners are already fully ephemeral — every job starts from a genuinely clean VM, not a
reused working tree, so the specific failure mode the plan describes ("the repo only works because
of state in the developer's working tree — an uncommitted file, a stale `.egg-info`") is already
structurally prevented by `actions/checkout` on every job, including the one that already existed
before today. Adding a second, separate job that does a literal `git clone` on top of that would
check the same thing GitHub Actions already guarantees, not add real coverage. The genuinely new
protection this day adds is the assertion against a *committed* reference hash — internal-
consistency tests can't catch silent drift over time or across platforms; this can. Framed
honestly here rather than manufacturing a redundant step to match the plan's original wording
literally.

## What this job is actually testing, for the first time, live

This is the first time this project's numerical output gets checked against Apple's Accelerate
framework (macOS) and Windows' OpenBLAS build, rather than only Linux's. There is a real,
non-hypothetical chance the hash doesn't match on one of those platforms even with byte-for-byte
identical code and pinned dependencies, purely from floating-point summation order differing
across BLAS implementations. That is not a bug in this codebase if it happens — but per
`docs/WEEK3-4_PLAN.md` Day 26's own stop-and-ask trigger, if it does happen, the resolution (pin a
specific BLAS, relax to a tolerance-based comparison, or document the platform dependence as a
finding) is Nishi's call, not something to resolve unilaterally by loosening the assertion until
it passes.

## Verified before committing the reference hash

Ran the smoke campaign three times locally (Linux, Python 3.10, pinned deps) and confirmed the
hash was identical across all three runs before writing it down as `EXPECTED_SMOKE_CAMPAIGN_HASH`.
Also checked what metadata pyarrow actually embeds in the Parquet files (`pyarrow.parquet.
read_metadata`) — only a `created_by` string and pinned pandas/pyarrow version numbers, no
hostname or timestamp, which is what makes a byte-identical cross-platform match plausible rather
than something metadata noise would sink regardless of real determinism.
