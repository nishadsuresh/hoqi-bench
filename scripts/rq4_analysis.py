"""
Week 5 Task 5, Day 33: RQ4 -- do method rankings change under physically
correct signal-dependent Poisson shot noise vs. the usual Gaussian
assumption? Implements the `llm-council` verdict recorded in
`docs/SUPPLEMENTARY_PROTOCOLS.md` Protocol 2, in full.

Uses ONLY the already-preregistered `photon_scale` and `noise_std` axes
-- no new campaign data. Two analyses, per the protocol:

1. PRIMARY (zero-assumption): each axis's own internal ranking, checked
   for an ordinal flip within its own swept range. Depends on no
   cross-axis equivalence choice.
2. SECONDARY (sensitivity matrix): pairs `photon_scale` and `noise_std`
   grid points under three matching rules (matched realized sigma,
   matched peak-intensity SNR, matched total Fisher information via
   `fisher_information.py`) and compares rankings at each matched pair.
   A ranking difference reported only if it survives a bootstrap-CI
   overlap check against seed-to-seed sampling noise (the gap all 5
   initial council advisors missed, caught in peer review).

Pipeline position: reads `results/main_campaign_summary.csv` (rankings)
and `results/raw/axis_{photon_scale,noise_std}=*.parquet` (per-seed
values, for the bootstrap significance check). Writes
`results/rq4_within_axis_rankings.csv` and
`results/rq4_matched_noise_matrix.csv`.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from hoqi_bench._types import FloatArray  # noqa: E402
from hoqi_bench.aggregate import MAX_UNUSABLE_RATE_FOR_RANKING  # noqa: E402
from hoqi_bench.config import load_sweep_config  # noqa: E402
from hoqi_bench.fisher_information import (  # noqa: E402
    total_fisher_information_gaussian,
    total_fisher_information_poisson,
)
from hoqi_bench.statistics import bootstrap_ci  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "main_campaign.toml"
SUMMARY_PATH = REPO_ROOT / "results" / "main_campaign_summary.csv"
RAW_DIR = REPO_ROOT / "results" / "raw"
WITHIN_AXIS_OUTPUT = REPO_ROOT / "results" / "rq4_within_axis_rankings.csv"
MATRIX_OUTPUT = REPO_ROOT / "results" / "rq4_matched_noise_matrix.csv"

# RQ4's shared baseline (docs/SUPPLEMENTARY_PROTOCOLS.md Protocol 2) --
# amplitude_ratio/quadrature_error_rad/contrast/mean_intensity are NEVER
# swept by either noise axis, so the Fisher-information computation uses
# these fixed values throughout, matching what the actual campaign ran.
BASELINE_MEAN_INTENSITY = 1.0
BASELINE_CONTRAST = 0.9
BASELINE_AMPLITUDE_RATIO = 1.1
BASELINE_QUADRATURE_ERROR_RAD = 0.1
BASELINE_SAMPLES_PER_FIT = 60
BASELINE_ARC_FRACTION = 1.0

BOOTSTRAP_SEED = 20260129  # fixed per this project's no-unseeded-RNG convention


# ---- 1. Primary: within-axis ranking flip (zero assumptions) -------------


def _ranking_at(summary: pd.DataFrame, condition_name: str) -> list[str]:
    """Methods at one condition, ordered best (lowest mean RMSE) to
    worst, restricted to methods meeting the same rankability threshold
    `aggregate.is_rankable` uses elsewhere in this project."""
    rows = summary[summary["condition_name"] == condition_name]
    rankable = rows[rows["unusable_rate"] <= MAX_UNUSABLE_RATE_FOR_RANKING]
    return list(rankable.sort_values("displacement_rmse_mean_m")["method_name"])


def within_axis_ranking_flips(
    summary: pd.DataFrame, config_axes: dict[str, list[float]]
) -> pd.DataFrame:
    rows = []
    for axis in ("photon_scale", "noise_std"):
        values = config_axes[axis]
        rankings = {v: _ranking_at(summary, f"axis:{axis}={v}") for v in values}
        baseline_ranking = rankings[values[0]]
        for v in values:
            rows.append(
                {
                    "axis": axis,
                    "value": v,
                    "ranking": ",".join(rankings[v]),
                    "differs_from_first_grid_point": rankings[v] != baseline_ranking,
                }
            )
    return pd.DataFrame(rows)


# ---- 2. Secondary: matched-noise sensitivity matrix -----------------------


def _measured_poisson_sigma(photon_scale: float) -> float:
    """sqrt(1/photon_scale) -- the closed-form approximation confirmed
    (docs/WEEK5-6_EXECUTION_PLAN.md §2.5) to track the REALIZED residual
    std within ~5% at every campaign photon_scale grid value. Used only
    for nearest-neighbor MATCHING between discrete grid points, not as a
    claim of exact equivalence.
    """
    return float(np.sqrt(1.0 / photon_scale))


def _peak_snr_gaussian(noise_std_absolute: float) -> float:
    """Peak-intensity SNR for Gaussian noise: peak signal amplitude
    (mean_intensity + oscillation amplitude) divided by the (constant)
    noise std."""
    amplitude = BASELINE_MEAN_INTENSITY * BASELINE_CONTRAST
    peak_signal = BASELINE_MEAN_INTENSITY + amplitude
    return peak_signal / noise_std_absolute if noise_std_absolute > 0 else float("inf")


def _peak_snr_poisson(photon_scale: float) -> float:
    """Peak-intensity SNR for Poisson noise: at the signal peak, local
    variance is peak_intensity/photon_scale (signal-dependent, unlike the
    Gaussian case) -- this is the definition that differs from matched
    sigma, per docs/SUPPLEMENTARY_PROTOCOLS.md Protocol 2's requirement
    that (b) be a genuinely different rule from (a), not sigma relabeled.
    """
    amplitude = BASELINE_MEAN_INTENSITY * BASELINE_CONTRAST
    peak_signal = BASELINE_MEAN_INTENSITY + amplitude
    peak_noise_std = np.sqrt(peak_signal / photon_scale)
    return float(peak_signal / peak_noise_std)


def _fisher_information_gaussian(noise_std_absolute: float) -> float:
    phi = np.linspace(
        0.0, BASELINE_ARC_FRACTION * 2 * np.pi, BASELINE_SAMPLES_PER_FIT, endpoint=False
    )
    return total_fisher_information_gaussian(
        phi,
        BASELINE_MEAN_INTENSITY,
        BASELINE_CONTRAST,
        BASELINE_AMPLITUDE_RATIO,
        BASELINE_QUADRATURE_ERROR_RAD,
        noise_std_absolute,
    )


def _fisher_information_poisson(photon_scale: float) -> float:
    phi = np.linspace(
        0.0, BASELINE_ARC_FRACTION * 2 * np.pi, BASELINE_SAMPLES_PER_FIT, endpoint=False
    )
    return total_fisher_information_poisson(
        phi,
        BASELINE_MEAN_INTENSITY,
        BASELINE_CONTRAST,
        BASELINE_AMPLITUDE_RATIO,
        BASELINE_QUADRATURE_ERROR_RAD,
        photon_scale,
    )


def build_matched_pairs(
    photon_scale_values: list[float], noise_std_values: list[float]
) -> pd.DataFrame:
    """For each of the 3 matching rules, pairs every `noise_std` grid
    value with its NEAREST `photon_scale` grid value under that rule
    (nearest-neighbor, since both grids are discrete -- there is no
    guarantee of an exact match). `noise_std=0.0` is excluded: every
    matching rule's Poisson-side quantity diverges or is undefined
    against a zero-noise Gaussian condition (infinite Fisher information,
    infinite SNR, zero sigma), so there is no meaningful nearest neighbor.
    """
    rows = []
    for noise_std in noise_std_values:
        if noise_std <= 0.0:
            continue
        candidates_by_rule = {
            "matched_sigma": {
                p: abs(_measured_poisson_sigma(p) - noise_std) for p in photon_scale_values
            },
            "matched_snr": {
                p: abs(_peak_snr_poisson(p) - _peak_snr_gaussian(noise_std))
                for p in photon_scale_values
            },
            "matched_fisher_information": {
                p: abs(_fisher_information_poisson(p) - _fisher_information_gaussian(noise_std))
                for p in photon_scale_values
            },
        }
        for rule, distances in candidates_by_rule.items():
            best_photon_scale = min(distances, key=lambda p: distances[p])
            rows.append(
                {
                    "matching_rule": rule,
                    "noise_std": noise_std,
                    "matched_photon_scale": best_photon_scale,
                }
            )
    return pd.DataFrame(rows)


def _per_seed_rmse(condition_name: str, method_name: str) -> FloatArray:
    from hoqi_bench.runner import condition_filename

    path = RAW_DIR / condition_filename(condition_name)
    frame = pd.read_parquet(path)
    rows = frame[(frame["method_name"] == method_name) & (~frame["failed"])]
    return rows["displacement_rmse_m"].to_numpy(dtype=np.float64)


def _first_diverging_pair(ranking_a: list[str], ranking_b: list[str]) -> tuple[str, str] | None:
    """The method occupying the FIRST position where two rankings
    disagree, from each ranking -- the actual pair whose relative order
    changed, not necessarily either ranking's #1 method. Returns None if
    the rankings are identical.

    Design decision: only the FIRST divergence, not every position that
    differs -- a single swap near the top of a 7-method ranking cascades
    into every LATER position also "differing" from a naive
    position-by-position comparison, even though only one real swap
    occurred. The first divergence is the one meaningful event; testing
    it directly avoids conflating one swap with several trailing
    "differences" that are really the same swap's downstream effect.
    """
    for method_a, method_b in zip(ranking_a, ranking_b, strict=False):
        if method_a != method_b:
            return method_a, method_b
    return None


def evaluate_matched_pairs(summary: pd.DataFrame, matched_pairs: pd.DataFrame) -> pd.DataFrame:
    """At each matched (noise_std, photon_scale) pair: does the ranking
    differ, and does the SPECIFIC pair of methods that swapped position
    survive a bootstrap-CI significance check.

    Real bug caught before this was trusted (docs/journal/day33.md): an
    earlier version of this function always tested `gaussian_ranking[0]`
    (Heydemann, per docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md's Category 1
    tautological prediction, which is essentially always #1 and never the
    method that actually moves) regardless of WHERE the ranking actually
    diverged -- so every reported "significant" difference was measuring
    an irrelevant method's noise floor, not the swap it claimed to
    validate. Fixed by identifying the actual first-diverging pair
    (`_first_diverging_pair`) and testing THAT pair specifically: bootstrap
    each method's own CI under its own matched condition, and call the
    swap significant only if BOTH methods' CIs, under their respective
    conditions, fail to overlap -- i.e. the ordering itself is
    distinguishable from seed-to-seed noise on both sides, not just one.
    """
    rows = []
    for _, pair in matched_pairs.iterrows():
        gaussian_condition = f"axis:noise_std={pair['noise_std']}"
        poisson_condition = f"axis:photon_scale={pair['matched_photon_scale']}"

        gaussian_ranking = _ranking_at(summary, gaussian_condition)
        poisson_ranking = _ranking_at(summary, poisson_condition)
        rankings_differ = gaussian_ranking != poisson_ranking

        diverging_pair = _first_diverging_pair(gaussian_ranking, poisson_ranking)
        significant_difference = False
        swapped_methods = ""
        if diverging_pair is not None:
            method_higher_under_gaussian, method_higher_under_poisson = diverging_pair
            swapped_methods = f"{method_higher_under_gaussian}<->{method_higher_under_poisson}"

            g_a = _per_seed_rmse(gaussian_condition, method_higher_under_gaussian)
            g_b = _per_seed_rmse(gaussian_condition, method_higher_under_poisson)
            p_a = _per_seed_rmse(poisson_condition, method_higher_under_gaussian)
            p_b = _per_seed_rmse(poisson_condition, method_higher_under_poisson)

            if min(len(g_a), len(g_b), len(p_a), len(p_b)) >= 2:
                # Under Gaussian: is method_higher_under_gaussian's CI
                # entirely below method_higher_under_poisson's CI (the
                # ordering the ranking claims)? Under Poisson: is it
                # entirely ABOVE (the ordering flipped)? Both must hold
                # for the swap to be more than noise.
                ga_low, ga_high = bootstrap_ci(g_a, seed=BOOTSTRAP_SEED)
                gb_low, gb_high = bootstrap_ci(g_b, seed=BOOTSTRAP_SEED)
                pa_low, pa_high = bootstrap_ci(p_a, seed=BOOTSTRAP_SEED)
                pb_low, pb_high = bootstrap_ci(p_b, seed=BOOTSTRAP_SEED)
                gaussian_order_significant = ga_high < gb_low
                poisson_order_significant = pb_high < pa_low
                significant_difference = gaussian_order_significant and poisson_order_significant

        rows.append(
            {
                "matching_rule": pair["matching_rule"],
                "noise_std": pair["noise_std"],
                "matched_photon_scale": pair["matched_photon_scale"],
                "gaussian_ranking": ",".join(gaussian_ranking),
                "poisson_ranking": ",".join(poisson_ranking),
                "rankings_differ": rankings_differ,
                "first_diverging_pair": swapped_methods,
                "significant_after_bootstrap_check": significant_difference,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    config = load_sweep_config(CONFIG_PATH)
    summary = pd.read_csv(SUMMARY_PATH)

    within_axis = within_axis_ranking_flips(summary, config.axes)
    within_axis.to_csv(WITHIN_AXIS_OUTPUT, index=False)
    n_flips = int(within_axis["differs_from_first_grid_point"].sum())
    print(
        f"Within-axis: {n_flips}/{len(within_axis)} grid points differ from "
        f"their axis's own first point"
    )

    matched_pairs = build_matched_pairs(config.axes["photon_scale"], config.axes["noise_std"])
    matrix = evaluate_matched_pairs(summary, matched_pairs)
    matrix.to_csv(MATRIX_OUTPUT, index=False)

    for rule in matrix["matching_rule"].unique():
        rule_rows = matrix[matrix["matching_rule"] == rule]
        n_differ = int(rule_rows["rankings_differ"].sum())
        n_significant = int(rule_rows["significant_after_bootstrap_check"].sum())
        print(
            f"{rule}: {n_differ}/{len(rule_rows)} matched pairs show a ranking difference, "
            f"{n_significant} survive the bootstrap-CI significance check"
        )
    print(f"Wrote {WITHIN_AXIS_OUTPUT} and {MATRIX_OUTPUT}")
