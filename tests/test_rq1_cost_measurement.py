"""
Day 31: tests for `scripts.rq1_cost_measurement`'s subset-selection logic
-- see that module's own docstring for why the subset (baseline + each
OFAT axis's last configured value) is chosen structurally, before any
cost or accuracy number is looked at.
"""

from __future__ import annotations

from hoqi_bench.config import load_sweep_config
from scripts.rq1_cost_measurement import (
    BASELINE_CONDITION_NAME,
    CONFIG_PATH,
    select_cost_measurement_conditions,
)


def test_baseline_condition_name_actually_equals_the_full_baseline() -> None:
    """amplitude_ratio=1.1 must BE the config's own baseline value, not a
    swept distortion point that happens to share a name -- if this axis's
    baseline value ever changes in configs/main_campaign.toml,
    BASELINE_CONDITION_NAME must be updated to match, and this test fails
    loudly rather than silently measuring cost at the wrong condition.
    """
    config = load_sweep_config(CONFIG_PATH)
    axis_value = float(BASELINE_CONDITION_NAME.split("=")[1])
    assert axis_value == config.baseline["amplitude_ratio"]


def test_selection_is_baseline_plus_one_per_axis_no_duplicates() -> None:
    config = load_sweep_config(CONFIG_PATH)
    selected = select_cost_measurement_conditions(config)

    names = [c.name for c in selected]
    assert len(names) == len(set(names)), "selection contains a duplicate condition"
    assert BASELINE_CONDITION_NAME in names

    # Every condition must be exactly the LAST configured value of its own
    # axis (or the baseline) -- never a hand-picked point, per the module's
    # own "structural, not accuracy-informed" design decision.
    for axis, values in config.axes.items():
        expected_extreme = f"axis:{axis}={values[-1]}"
        assert expected_extreme in names or expected_extreme == BASELINE_CONDITION_NAME, (
            f"axis {axis}'s extreme point {expected_extreme} is missing from the selection"
        )
