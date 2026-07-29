"""
Day 30: tests for `scripts.rq3_power_law_analysis`'s zero-condition
exclusion and honesty-gate routing -- see that module's own docstring for
the full design (why R_SQUARED_FLOOR=0.90 was calibrated before looking at
any real result, and why the `hysteresis_magnitude` axis is labeled
"radial_inflation" throughout, per `docs/PREREGISTRATION.md` deviation D5).

Oracle-independent per this project's own testing convention
(`docs/WEEK4_EXECUTION_PLAN.md` §0.5 rule 5): synthetic magnitude/error
arrays are constructed directly in this file, never imported from the
module under test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.rq3_power_law_analysis import (
    _AXIS_MAGNITUDE_TRANSFORM,
    R_SQUARED_FLOOR,
    _method_error_series,
)


def test_amplitude_ratio_magnitude_transform_excludes_the_zero_distortion_point() -> None:
    """amplitude_ratio's zero-distortion value is 1.0 (an undistorted
    circle), not 0.0 -- `_method_error_series` must map it to magnitude
    0.0 via the axis's own transform and then exclude it, the same as
    every other axis's literal 0.0 grid point.
    """
    transform = _AXIS_MAGNITUDE_TRANSFORM["amplitude_ratio"]
    assert transform(1.0) == 0.0
    assert transform(1.5) == 0.5


def test_method_error_series_excludes_zero_magnitude_condition() -> None:
    swept_values = [1.0, 1.1, 1.2]
    summary = pd.DataFrame(
        [
            {
                "condition_name": f"axis:amplitude_ratio={v}",
                "method_name": "kasa",
                "unusable_rate": 0.0,
                "displacement_rmse_mean_m": 1e-9 * (1 + i),
            }
            for i, v in enumerate(swept_values)
        ]
    )
    magnitudes, errors, n_excluded = _method_error_series(
        summary, "amplitude_ratio", "kasa", swept_values
    )
    # 1.0 -> magnitude 0.0 -> excluded; only 1.1 and 1.2 survive.
    assert len(magnitudes) == 2
    assert 0.0 not in magnitudes
    assert np.all(magnitudes > 0)


def test_method_error_series_excludes_high_unusable_rate_points() -> None:
    swept_values = [0.1, 0.2, 0.3]
    summary = pd.DataFrame(
        [
            {
                "condition_name": "axis:dc_offset=0.1",
                "method_name": "heydemann",
                "unusable_rate": 0.0,
                "displacement_rmse_mean_m": 1e-9,
            },
            {
                "condition_name": "axis:dc_offset=0.2",
                "method_name": "heydemann",
                "unusable_rate": 0.9,  # above MAX_UNUSABLE_RATE_FOR_RANKING (0.20)
                "displacement_rmse_mean_m": 5e-9,
            },
            {
                "condition_name": "axis:dc_offset=0.3",
                "method_name": "heydemann",
                "unusable_rate": 0.0,
                "displacement_rmse_mean_m": 3e-9,
            },
        ]
    )
    magnitudes, errors, n_excluded = _method_error_series(
        summary, "dc_offset", "heydemann", swept_values
    )
    assert n_excluded == 1
    assert len(magnitudes) == 2
    assert 0.2 not in magnitudes


def test_flat_synthetic_relationship_falls_below_the_r_squared_floor() -> None:
    """The honesty gate this module exists to enforce: a genuinely flat
    error-vs-magnitude relationship must route to `no_clean_power_law`,
    not be reported as a spuriously confident power-law fit.

    Uses the same magnitude grid and noise level as the calibration in
    `scripts/rq3_power_law_analysis.py`'s own docstring (5% relative
    noise, 9 points) -- reproduced here as an independent oracle rather
    than imported from that calibration.
    """
    from hoqi_bench.power_law import fit_power_law_exponent

    rng = np.random.default_rng(123)
    magnitudes = np.array([0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5])
    errors = np.abs(
        np.full_like(magnitudes, 1e-9) * (1 + rng.normal(0, 0.05, size=magnitudes.shape))
    )
    _, _, r_squared = fit_power_law_exponent(magnitudes, errors)
    assert r_squared < R_SQUARED_FLOOR


def test_genuine_power_law_relationship_meets_the_r_squared_floor() -> None:
    """The inverse check: a genuine n=3 power-law relationship (matching
    Lehmann et al. 2025's reported exponent), with realistic noise, must
    clear the floor -- otherwise the floor would be too strict to ever
    detect a real relationship, which would be a different, opposite
    failure of the same honesty gate.
    """
    from hoqi_bench.power_law import fit_power_law_exponent

    rng = np.random.default_rng(456)
    magnitudes = np.array([0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5])
    clean = 1e-9 * magnitudes**3
    errors = np.abs(clean * (1 + rng.normal(0, 0.05, size=magnitudes.shape)))
    exponent, _, r_squared = fit_power_law_exponent(magnitudes, errors)
    assert r_squared >= R_SQUARED_FLOOR
    assert abs(exponent - 3.0) < 0.5
