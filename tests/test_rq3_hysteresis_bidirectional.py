"""
Day 32: tests for `scripts.rq3_hysteresis_bidirectional`'s comparison
logic -- specifically the bug caught by inspecting real output on Day 32
(`docs/journal/day32.md`): a method that goes fully unusable under the
bidirectional waveform produces `displacement_rmse_mean_m_bidirectional =
NaN`, which makes the RMSE-difference criterion silently register as "no
difference" (a NaN comparison is always False) for the single most
dramatic possible outcome. `bidirectional_became_unusable` is the
separate, always-visible flag that catches this.
"""

from __future__ import annotations

import pandas as pd

from scripts.rq3_hysteresis_bidirectional import build_comparison_table


def test_became_unusable_flag_catches_what_the_rmse_criterion_cannot(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A synthetic reproduction of the exact Day 32 finding: heydemann at
    hysteresis_magnitude=0.2 went from unusable_rate=0.0 (monotonic) to
    unusable_rate=1.0 (bidirectional), which sets
    displacement_rmse_mean_m_bidirectional to NaN. Confirms
    `exceeds_monotonic_noise_floor` is False in that row (documenting WHY
    the second flag is needed, not just asserting the fix) while
    `bidirectional_became_unusable` is True.
    """
    import scripts.rq3_hysteresis_bidirectional as module

    bidirectional_summary = pd.DataFrame(
        [
            {
                "condition_name": "axis:hysteresis_magnitude=0.2",
                "method_name": "heydemann",
                "displacement_rmse_mean_m": float("nan"),
                "displacement_rmse_std_m": float("nan"),
                "unusable_rate": 1.0,
            }
        ]
    )
    monotonic_summary = pd.DataFrame(
        [
            {
                "condition_name": "axis:hysteresis_magnitude=0.2",
                "method_name": "heydemann",
                "displacement_rmse_mean_m": 3.06e-10,
                "displacement_rmse_std_m": 1.57e-12,
                "unusable_rate": 0.0,
            },
            {
                "condition_name": "axis:hysteresis_magnitude=0.0",
                "method_name": "heydemann",
                "displacement_rmse_mean_m": 1.0e-10,
                "displacement_rmse_std_m": 1.0e-12,
                "unusable_rate": 0.0,
            },
        ]
    )
    monotonic_path = tmp_path / "main_campaign_summary.csv"
    monotonic_summary.to_csv(monotonic_path, index=False)

    monkeypatch.setattr(module, "aggregate_campaign", lambda _dir: bidirectional_summary)
    monkeypatch.setattr(module, "MAIN_CAMPAIGN_SUMMARY", monotonic_path)

    table = build_comparison_table()

    assert len(table) == 1
    row = table.iloc[0]
    assert pd.isna(row["displacement_rmse_mean_m_bidirectional"])
    # The exact bug this test pins: a NaN RMSE difference makes the
    # RMSE-based criterion False (never True, never raises) -- silently
    # reporting "no difference" for the most dramatic possible outcome.
    assert not bool(row["exceeds_monotonic_noise_floor"])
    # The fix: a SEPARATE flag that IS true for this row.
    assert bool(row["bidirectional_became_unusable"])


def test_matched_condition_with_real_difference_is_flagged(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A synthetic, oracle-independent check of the RMSE criterion itself:
    a difference larger than the monotonic run's own seed-to-seed std must
    be flagged; a difference smaller must not."""
    import scripts.rq3_hysteresis_bidirectional as module

    bidirectional_summary = pd.DataFrame(
        [
            {
                "condition_name": "axis:hysteresis_magnitude=0.02",
                "method_name": "fitzgibbon",
                "displacement_rmse_mean_m": 4.36e-11,
                "displacement_rmse_std_m": 3.0e-12,
                "unusable_rate": 0.0,
            },
            {
                "condition_name": "axis:hysteresis_magnitude=0.02",
                "method_name": "kasa",
                "displacement_rmse_mean_m": 3.608059e-09,  # tiny diff, within noise
                "displacement_rmse_std_m": 2.7e-12,
                "unusable_rate": 0.0,
            },
        ]
    )
    monotonic_summary = pd.DataFrame(
        [
            {
                "condition_name": "axis:hysteresis_magnitude=0.02",
                "method_name": "fitzgibbon",
                "displacement_rmse_mean_m": 7.45e-11,  # large diff vs. bidirectional
                "displacement_rmse_std_m": 4.8e-12,
                "unusable_rate": 0.0,
            },
            {
                "condition_name": "axis:hysteresis_magnitude=0.02",
                "method_name": "kasa",
                "displacement_rmse_mean_m": 3.607998e-09,
                "displacement_rmse_std_m": 2.68e-12,
                "unusable_rate": 0.0,
            },
        ]
    )
    monotonic_path = tmp_path / "main_campaign_summary.csv"
    monotonic_summary.to_csv(monotonic_path, index=False)

    monkeypatch.setattr(module, "aggregate_campaign", lambda _dir: bidirectional_summary)
    monkeypatch.setattr(module, "MAIN_CAMPAIGN_SUMMARY", monotonic_path)

    table = build_comparison_table()

    by_method = table.set_index("method_name")
    assert by_method.loc["fitzgibbon", "exceeds_monotonic_noise_floor"]
    assert not by_method.loc["kasa", "exceeds_monotonic_noise_floor"]
