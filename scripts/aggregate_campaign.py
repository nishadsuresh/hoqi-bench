"""
Day 27: collapses the raw per-(condition, method, seed) campaign table
into one row per (method, condition) via `aggregate.summarize` -- the
contract-aware path (failure rate, gross-error rate, unusable rate all
reported alongside the mean, per R1/`docs/WEEK3_METHOD_CONTRACT.md` §2.1),
never a bare `groupby(...).mean()` over the raw table (Day 24's journal:
that silently reproduces R1's survivorship-bias inversion).

Why this is committed and the raw per-seed data is not: the raw table
(359 conditions x 7 methods x 50 seeds = 125,650 rows) is fully
regenerable from the committed config, pinned environment, and this
package's source -- exactly the reproducibility this project's Day 26
hardening exists to guarantee. The aggregate summary (359 x 7 = 2,513
rows) is the actual analysis deliverable Day 28 reads, small enough to
review in a diff, and worth keeping under version control the way a
generated figure or table in a paper would be.

Pipeline position: run once, after `scripts/run_campaign.py`, before Day
28's RQ1/RQ2 analysis. Not part of the pytest suite -- this is a one-shot
campaign step, like `scripts/robustness_matrix.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from hoqi_bench.aggregate import SeedOutcome, summarize
from hoqi_bench.runner import load_results

DEFAULT_INPUT = Path(__file__).parent.parent / "results" / "raw"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "results" / "main_campaign_summary.csv"


def _row_to_outcome(row: pd.Series) -> SeedOutcome:
    """Reconstructs the `SeedOutcome` `aggregate.summarize` needs from one
    row of the raw table -- the raw table already carries every field
    `outcome_from_fit` would have produced, just flattened into columns
    for Parquet storage."""
    return SeedOutcome(
        failed=bool(row["failed"]),
        reason=row["reason"] if pd.notna(row["reason"]) else None,
        displacement_rmse_m=float(row["displacement_rmse_m"]),
        peak_absolute_error_m=float(row["peak_absolute_error_m"]),
        phase_rmse_rad=float(row["phase_rmse_rad"]),
        runtime_s=float(row["runtime_s"]) if pd.notna(row["runtime_s"]) else None,
        converged=bool(row["converged"]) if pd.notna(row["converged"]) else None,
    )


def aggregate_campaign(input_dir: Path) -> pd.DataFrame:
    frame = load_results(input_dir)
    rows = []
    for (condition_name, method_name), group in frame.groupby(
        ["condition_name", "method_name"], sort=False
    ):
        outcomes = [_row_to_outcome(row) for _, row in group.iterrows()]
        summary = summarize(str(method_name), str(condition_name), outcomes)
        rows.append(vars(summary))
    result = pd.DataFrame(rows)
    return result.sort_values(["condition_name", "method_name"]).reset_index(drop=True)


def main() -> int:
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    summary = aggregate_campaign(input_dir)
    summary.to_csv(output_path, index=False)
    print(f"wrote {len(summary)} (method, condition) summaries to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
