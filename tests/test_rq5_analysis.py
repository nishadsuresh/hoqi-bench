"""
Tests for scripts.rq5_analysis -- Week 5 Task 7, Day 35.
"""

from __future__ import annotations

import pandas as pd

from scripts.rq5_analysis import (
    build_arc_fraction_table,
    heydemann_unusable_everywhere_except_full_circle,
)


def test_heydemann_all_or_nothing_helper_detects_true_case() -> None:
    rows = [
        {"condition_name": f"axis:arc_fraction={v}", "method_name": "heydemann", "unusable_rate": u}
        for v, u in [(0.02, 1.0), (0.5, 1.0), (0.75, 1.0), (1.0, 0.0)]
    ]
    for extra in ["displacement_rmse_mean_m", "failure_rate", "gross_error_rate"]:
        for row in rows:
            row[extra] = 0.0
    summary = pd.DataFrame(rows)
    table = build_arc_fraction_table(summary)
    assert heydemann_unusable_everywhere_except_full_circle(table)


def test_heydemann_all_or_nothing_helper_detects_false_case() -> None:
    """A method that is only PARTLY unusable at sub-fringe values (the
    real halir_flusser pattern) must not be misreported as the
    all-or-nothing case."""
    rows = [
        {"condition_name": f"axis:arc_fraction={v}", "method_name": "heydemann", "unusable_rate": u}
        for v, u in [(0.02, 1.0), (0.5, 0.3), (0.75, 0.0), (1.0, 0.0)]
    ]
    for extra in ["displacement_rmse_mean_m", "failure_rate", "gross_error_rate"]:
        for row in rows:
            row[extra] = 0.0
    summary = pd.DataFrame(rows)
    table = build_arc_fraction_table(summary)
    assert not heydemann_unusable_everywhere_except_full_circle(table)
