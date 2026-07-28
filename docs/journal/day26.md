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

## What actually happened on the first push: a real cross-platform finding, not a hypothetical one

Pushed the single-hash version and it failed exactly where it was designed to be able to fail:
Linux matched on both Python versions; macOS produced one different hash (identical across its own
two Python versions); Windows produced a third different hash (likewise identical across its own
two Python versions). Every platform is internally deterministic — the same OS always reproduces
its own result — but the three disagree with each other. That's the textbook signature of genuine
floating-point non-portability (transcendental functions and LAPACK routines aren't required to
round identically across platforms' math libraries), not a flaky bug: a real bug would not survive
identically across two independent Python versions on each of three OSes.

This is precisely the scenario `docs/WEEK3-4_PLAN.md` Day 26 names as a stop-and-ask trigger, so it
went to Nishi rather than getting resolved unilaterally. Decision: keep Linux's exact hash as the
source of truth (it's the environment the real 125,650-run campaign, Day 27, actually executes in),
and verify macOS/Windows against the same reference **numerically** instead — `rtol=1e-9,
atol=1e-15`, loose enough to absorb platform-level floating-point noise, far tighter than any real
regression this project's own bugs have produced (D1's arc-sampling defect was ~1e-2 relative, five
orders of magnitude looser). Implemented as two tests in `tests/test_reproducibility.py`: the exact
hash check now skips on non-Linux platforms; a second, universal test compares every numeric column
against a committed CSV reference within that tolerance, on all three OSes including Linux (where
it's a strictly weaker restatement that should never fail if the exact check passes). Recorded as
D4 in `docs/PREREGISTRATION.md`.

The tolerance is deliberately marked in its own comment as "the first value tried, not yet
calibrated against a real cross-platform failure" — if the next CI run still fails on macOS or
Windows, that's new information about the actual magnitude of the discrepancy, not a signal to
keep widening the number until it goes green.

## Verified before committing the reference hash — and then falsified by the very next push

Ran the smoke campaign three times locally (Linux, Python 3.10, pinned deps) and confirmed the
hash was identical across all three runs before writing it down as `EXPECTED_SMOKE_CAMPAIGN_HASH`.
Also checked what metadata pyarrow actually embeds in the Parquet files (`pyarrow.parquet.
read_metadata`) — only a `created_by` string and pinned pandas/pyarrow version numbers, no
hostname or timestamp, which is what makes a byte-identical match plausible rather than something
metadata noise alone would sink regardless of real determinism.

That verification was real, but it was only ever one Linux machine — mine. The very next push
(no functional change, only the test file) showed Linux itself producing a *third* hash, different
from its own first CI run, on a fully isolated pytest process. GitHub's `ubuntu-latest` is not one
machine; it's a label over a heterogeneous fleet, and numpy's vectorized transcendental functions
and LAPACK routines can dispatch different CPU instructions depending on which physical machine a
given run lands on — producing different low-order bits even under "the same OS" across separate
invocations, not only across genuinely different OSes.

This directly falsified the premise I'd presented in the first version of this decision ("Linux is
bit-stable, only macOS/Windows aren't"). Re-presented to Nishi with the corrected picture rather
than quietly patching around it — the honest fix wasn't "give Linux a slightly better tolerance
too," it was recognizing that *no platform* had actually earned a byte-exact claim, on any of the
evidence gathered so far. Decision: drop the exact-hash test entirely. One universal numeric-
tolerance check, applied identically everywhere, is both simpler and a more honest statement of
what this project can actually promise. Full reasoning recorded as D4's corrected text in
`docs/PREREGISTRATION.md` — the first (wrong) conclusion is kept in that document's history rather
than erased, since seeing a real conclusion get corrected by the next piece of evidence is itself
useful evidence of the process working, not something to hide.

Confirmed the tolerance check passes on both of Linux's two different hashes, on macOS, and on
Windows — the underlying numbers agree comfortably; only the exact bytes differ. `tests/
test_runner.py`'s own determinism tests (two runs in the same process) remain untouched and still
valid — same-process, same-hardware byte-identity is a different, still-true claim from
cross-invocation, cross-machine byte-identity, which is the claim that turned out to be false.
