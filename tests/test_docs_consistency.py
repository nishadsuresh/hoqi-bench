"""
Doc-consistency check: asserts claimed run/seed counts in prose match the
actual, loaded main_campaign.toml -- programmatically, not by eye.

Why this exists (Weeks 1-2 audit, 2026-07-26, findings F7/F8): this project
was caught, twice, stating a number in prose that had drifted from the
config it was supposed to describe -- docs/experimental_design.md's Section
5 said "30 seeds" while every other section and the config said 50
(finding F7); src/hoqi_bench/config.py's own module docstring said
total_runs=10,290 after the config had been expanded to 117,950 (finding
F8). The Day 14 triple-check caught these by hand, once; this test makes
that check automatic and permanent, so it fails LOUDLY the next time the
config changes and a doc doesn't, rather than sitting undetected until the
next manual audit.

Design decision: greps for the literal formatted number in each file rather
than parsing markdown structure -- simple, and exactly matches how a human
reader would notice (or fail to notice) the drift.
"""

from __future__ import annotations

from pathlib import Path

from hoqi_bench.config import load_sweep_config

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


def test_total_runs_is_consistent_across_config_and_docs() -> None:
    config = load_sweep_config(REPO_ROOT / "configs" / "main_campaign.toml")
    total = config.total_runs()
    formatted = f"{total:,}"  # e.g. "125,650" -- matches this project's prose style

    files_that_must_state_it = [
        "docs/PREREGISTRATION.md",
        "docs/experimental_design.md",
        "src/hoqi_bench/config.py",
    ]
    for relative_path in files_that_must_state_it:
        content = _read(relative_path)
        assert formatted in content, (
            f"{relative_path} does not contain the current total_runs value "
            f"({formatted}, from configs/main_campaign.toml) -- likely stale "
            f"prose after a config change (Weeks 1-2 audit findings F7/F8)"
        )


def test_n_seeds_is_consistent_across_config_and_docs() -> None:
    config = load_sweep_config(REPO_ROOT / "configs" / "main_campaign.toml")
    n_seeds = config.n_seeds

    prereg = _read("docs/PREREGISTRATION.md")
    design = _read("docs/experimental_design.md")

    assert f"{n_seeds} seeds" in prereg or f"n_seeds == {n_seeds}" in prereg
    # experimental_design.md's v2 addendum states seeds via the total_runs
    # formula and Section 5's "Seeds per condition: 50" line -- both must
    # agree with the config, not just with each other (this is the exact
    # shape of finding F7: two sections of the SAME document disagreeing).
    assert f"Seeds per condition**: {n_seeds}" in design
