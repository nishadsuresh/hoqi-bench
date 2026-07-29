"""
Week 5 Task 7, Day 35: RQ5 -- how does performance depend on
phase-excursion regime? Uses ONLY the already-preregistered
`arc_fraction` axis and `arc_x_noise` interaction grid -- no new
campaign data.

SCOPE, per `docs/PREREGISTRATION.md` deviation D7: `arc_fraction=1.0` is
EXACTLY one 2*pi cycle (`arc.build_arc_ramp`), not "many fringes." This
analysis therefore answers RQ5 only over the SUB-FRINGE regime (a 0.72
degree arc up to exactly one full cycle) -- the many-fringe half of the
original question was never in the preregistered grid and is not
answered here. Every output states this scope explicitly.

Pipeline position: reads `results/main_campaign_summary.csv` (the
immutable preregistered table). Writes `results/rq5_arc_fraction_full_range.csv`
and `results/rq5_arc_x_noise_interaction.csv`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
SUMMARY_PATH = REPO_ROOT / "results" / "main_campaign_summary.csv"
ARC_FRACTION_OUTPUT = REPO_ROOT / "results" / "rq5_arc_fraction_full_range.csv"
ARC_X_NOISE_OUTPUT = REPO_ROOT / "results" / "rq5_arc_x_noise_interaction.csv"


def build_arc_fraction_table(summary: pd.DataFrame) -> pd.DataFrame:
    """Every method's displacement RMSE and unusable_rate across the
    FULL preregistered arc_fraction range -- not just the single
    arc_fraction=0.02 extreme point RQ1b already reports, so this
    surfaces the SHAPE of the relationship, including non-monotonic
    reliability effects RQ1b's single-point focus cannot show.
    """
    rows = summary[summary["condition_name"].str.startswith("axis:arc_fraction=")].copy()
    rows["arc_fraction"] = rows["condition_name"].str.extract(r"=([\d.]+)")[0].astype(float)
    return rows[
        [
            "arc_fraction",
            "method_name",
            "displacement_rmse_mean_m",
            "unusable_rate",
            "failure_rate",
            "gross_error_rate",
        ]
    ].sort_values(["method_name", "arc_fraction"])


def build_arc_x_noise_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows = summary[summary["condition_name"].str.startswith("grid:arc_x_noise:")].copy()
    rows["arc_fraction"] = (
        rows["condition_name"].str.extract(r"arc_fraction=([\d.]+)")[0].astype(float)
    )
    rows["noise_std"] = rows["condition_name"].str.extract(r"noise_std=([\d.]+)")[0].astype(float)
    return rows[
        [
            "arc_fraction",
            "noise_std",
            "method_name",
            "displacement_rmse_mean_m",
            "unusable_rate",
        ]
    ].sort_values(["method_name", "arc_fraction", "noise_std"])


def heydemann_unusable_everywhere_except_full_circle(arc_table: pd.DataFrame) -> bool:
    """Checks the specific finding this script's own journal entry
    reports: Heydemann's unusable_rate is 1.0 at every swept
    arc_fraction EXCEPT exactly 1.0 (full circle) -- verified
    programmatically rather than eyeballed off the table, so a future
    campaign re-run that changes this doesn't silently go unnoticed."""
    heydemann = arc_table[arc_table["method_name"] == "heydemann"]
    sub_fringe = heydemann[heydemann["arc_fraction"] < 1.0]
    full_circle = heydemann[heydemann["arc_fraction"] == 1.0]
    return bool((sub_fringe["unusable_rate"] == 1.0).all()) and bool(
        (full_circle["unusable_rate"] == 0.0).all()
    )


if __name__ == "__main__":
    summary = pd.read_csv(SUMMARY_PATH)

    arc_table = build_arc_fraction_table(summary)
    arc_table.to_csv(ARC_FRACTION_OUTPUT, index=False)

    interaction_table = build_arc_x_noise_table(summary)
    interaction_table.to_csv(ARC_X_NOISE_OUTPUT, index=False)

    print(f"Wrote {ARC_FRACTION_OUTPUT} ({len(arc_table)} rows)")
    print(f"Wrote {ARC_X_NOISE_OUTPUT} ({len(interaction_table)} rows)")
    print(
        "Heydemann unusable at every sub-fringe point, usable only at full circle: "
        f"{heydemann_unusable_everywhere_except_full_circle(arc_table)}"
    )
