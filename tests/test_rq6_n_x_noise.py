"""
Tests for scripts.rq6_n_x_noise -- Week 5 Task 6, Day 34. Focused on the
scan-direction correctness `docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 3
explicitly flags as the easy-to-get-wrong part: samples_per_fit must be
scanned DESCENDING (large N = easy), unlike the only other
breakdown_threshold call site's ascending convention
(amplitude_ratio/arc_fraction, where ascending = harder).
"""

from __future__ import annotations

import pandas as pd

from scripts.rq6_n_x_noise import SAMPLES_PER_FIT_SCAN_ORDER, build_design_chart


def test_scan_order_is_descending() -> None:
    """Pins the literal fact Protocol 3 depends on -- if this ever
    silently became ascending, build_design_chart would report the
    wrong crossing direction without any other test catching it."""
    assert SAMPLES_PER_FIT_SCAN_ORDER == sorted(SAMPLES_PER_FIT_SCAN_ORDER, reverse=True)
    assert SAMPLES_PER_FIT_SCAN_ORDER == [1000, 500, 200, 100, 60, 40, 20]


def _synthetic_summary_row(
    method: str, samples_per_fit: int, noise_std: float, rmse: float
) -> dict[str, object]:
    return {
        "condition_name": f"grid:n_x_noise:samples_per_fit={samples_per_fit},noise_std={noise_std}",
        "method_name": method,
        "displacement_rmse_mean_m": rmse,
        "unusable_rate": 0.0,
    }


def test_finds_correct_crossing_as_n_decreases() -> None:
    """A synthetic case where error is low (below tolerance) at high N
    and rises above tolerance as N shrinks -- the crossing must be found
    scanning FROM high N TOWARD low N, not the reverse. Tolerance here is
    reconstructed as the real PREREGISTERED_TOLERANCE_M value to keep
    this an honest end-to-end check of the actual constant used."""
    from hoqi_bench.reference_scale import PREREGISTERED_TOLERANCE_M

    rows = []
    # Error DECREASES as N increases (the real, physically expected
    # shape): rises above tolerance somewhere between N=100 and N=200.
    rmse_by_n = {
        1000: PREREGISTERED_TOLERANCE_M * 0.5,
        500: PREREGISTERED_TOLERANCE_M * 0.6,
        200: PREREGISTERED_TOLERANCE_M * 0.8,
        100: PREREGISTERED_TOLERANCE_M * 1.3,
        60: PREREGISTERED_TOLERANCE_M * 1.6,
        40: PREREGISTERED_TOLERANCE_M * 2.0,
        20: PREREGISTERED_TOLERANCE_M * 3.0,
    }
    for n, rmse in rmse_by_n.items():
        rows.append(_synthetic_summary_row("test_method", n, 0.05, rmse))
    summary = pd.DataFrame(rows)

    chart = build_design_chart(summary)
    assert len(chart) == 1
    row = chart.iloc[0]
    assert row["min_samples_per_fit_status"] == "found"
    # The crossing must land strictly between 100 and 200 -- the two
    # bracketing grid points -- not at either endpoint.
    assert 100 < row["min_samples_per_fit"] < 200


def test_broken_at_start_when_even_largest_n_exceeds_tolerance() -> None:
    from hoqi_bench.reference_scale import PREREGISTERED_TOLERANCE_M

    rows = [
        _synthetic_summary_row("always_bad", n, 0.05, PREREGISTERED_TOLERANCE_M * 5.0)
        for n in SAMPLES_PER_FIT_SCAN_ORDER
    ]
    summary = pd.DataFrame(rows)

    chart = build_design_chart(summary)
    assert chart.iloc[0]["min_samples_per_fit_status"] == "broken_at_start"


def test_no_breakdown_when_even_smallest_n_meets_tolerance() -> None:
    from hoqi_bench.reference_scale import PREREGISTERED_TOLERANCE_M

    rows = [
        _synthetic_summary_row("always_good", n, 0.05, PREREGISTERED_TOLERANCE_M * 0.1)
        for n in SAMPLES_PER_FIT_SCAN_ORDER
    ]
    summary = pd.DataFrame(rows)

    chart = build_design_chart(summary)
    assert chart.iloc[0]["min_samples_per_fit_status"] == "no_breakdown_in_range"
