"""
Day 20 robustness matrix: every method (7) against every adversarial
input category (5) -- 35 cells, `method x failure-mode x
graceful/degraded/crash`.

Why this exists (docs/WEEK3-4_PLAN.md Day 20): a method that throws
mid-sweep would corrupt the Week 4 campaign -- every crash must become a
graceful failure with a reason code, not a silently-skipped or aborted
run. This script builds the actual matrix once and reports it; the
corresponding acceptance test (tests/test_robustness_matrix.py) re-runs
the same 35 cells and asserts programmatically that NONE crash, so this
guarantee is checked on every future commit, not just today.

Pipeline position: standalone script (like verify_heydemann_derivation.py,
explore_ellipse_constraints.py), not imported by the package. Run via
`python scripts/robustness_matrix.py`, prints the matrix as a markdown
table.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import FloatArray
from hoqi_bench.methods import METHOD_REGISTRY

# ---- 1. Adversarial input categories, per docs/WEEK3-4_PLAN.md Day 20 ----


def _near_zero_phase_excursion() -> tuple[FloatArray, FloatArray]:
    """A handful of points clustered within a fraction of a degree --
    more extreme than the campaign's own smallest arc_fraction=0.02."""
    phi = np.linspace(0, np.deg2rad(0.5), 30)
    return 1.0 + 0.9 * np.cos(phi), 1.0 + 0.9 * np.sin(phi)


def _near_perfect_circle() -> tuple[FloatArray, FloatArray]:
    """A genuine circle (amplitude_ratio=1, quadrature_error_rad=0
    exactly) -- degenerate in the OTHER direction from a highly
    eccentric ellipse: tests whether ellipse-fitting methods handle the
    a~=c near-degenerate-eccentricity case gracefully."""
    phi = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    return 1.0 + 0.9 * np.cos(phi), 1.0 + 0.9 * np.sin(phi)


def _very_short_record() -> tuple[FloatArray, FloatArray]:
    """10 samples -- below the campaign's own smallest samples_per_fit=20."""
    phi = np.linspace(0, 2 * np.pi, 10, endpoint=False)
    return 1.0 + 0.9 * np.cos(phi), 1.0 + 0.9 * np.sin(phi)


def _extreme_noise() -> tuple[FloatArray, FloatArray]:
    """noise_std = 0.5*A -- 5x the campaign's own top swept value."""
    rng = np.random.default_rng(0)
    phi = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    i = 1.0 + 0.9 * np.cos(phi) + rng.normal(0, 0.45, 60)
    q = 1.0 + 0.9 * np.sin(phi) + rng.normal(0, 0.45, 60)
    return i, q


def _all_identical_points() -> tuple[FloatArray, FloatArray]:
    """The most degenerate possible input -- zero variance in both
    channels, no oscillation at all."""
    return np.full(60, 1.0), np.full(60, 1.0)


ADVERSARIAL_INPUTS = {
    "near_zero_phase_excursion": _near_zero_phase_excursion,
    "near_perfect_circle": _near_perfect_circle,
    "very_short_record": _very_short_record,
    "extreme_noise": _extreme_noise,
    "all_identical_points": _all_identical_points,
}


def classify(method_name: str, fit_fn: object, i: FloatArray, q: FloatArray) -> str:
    """Returns "graceful" (succeeded or returned failed=True cleanly),
    or "CRASH" (raised an exception) -- the one outcome
    docs/WEEK3-4_PLAN.md Day 20 says must never happen."""
    try:
        kwargs = {"mean_intensity": 1.0} if method_name == "raw_atan2" else {}
        result = fit_fn(i, q, **kwargs)  # type: ignore[operator]
        if result.failed:
            return f"graceful (failed: {result.reason})"
        return "graceful (succeeded)"
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: this IS the crash detector
        return f"CRASH: {type(exc).__name__}: {exc}"


def build_matrix() -> dict[str, dict[str, str]]:
    matrix: dict[str, dict[str, str]] = {}
    for method_name, fit_fn in METHOD_REGISTRY.items():
        matrix[method_name] = {}
        for input_name, input_fn in ADVERSARIAL_INPUTS.items():
            i, q = input_fn()
            matrix[method_name][input_name] = classify(method_name, fit_fn, i, q)
    return matrix


def print_matrix(matrix: dict[str, dict[str, str]]) -> None:
    input_names = list(ADVERSARIAL_INPUTS.keys())
    header = "| method | " + " | ".join(input_names) + " |"
    separator = "|---|" + "|".join(["---"] * len(input_names)) + "|"
    print(header)
    print(separator)
    for method_name, row in matrix.items():
        cells = [row[name] for name in input_names]
        print(f"| {method_name} | " + " | ".join(cells) + " |")

    crash_count = sum(1 for row in matrix.values() for v in row.values() if v.startswith("CRASH"))
    print(f"\nTotal crashes: {crash_count} / {len(matrix) * len(input_names)} cells")


if __name__ == "__main__":
    print_matrix(build_matrix())
