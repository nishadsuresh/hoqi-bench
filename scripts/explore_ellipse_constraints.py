"""
Numerical study: why Halir & Flusser (1998) reformulated Fitzgibbon et al.
(1999)'s direct least-squares ellipse fit.

Why this exists: Halir & Flusser's paper *describes* Fitzgibbon's numerical
fragility in prose ("can produce unoptimal or even completely wrong
results"), but this project's documentation standard (equation provenance,
failure-mode notes) calls for SHOWING a failure mode with real numbers, not
just citing that someone else described one. This script generates synthetic
ellipse data across a conditioning spectrum, runs both formulations on
identical data over many random seeds, and reports where each one breaks.

A real bug was caught and fixed while building this (see docs/journal/day03.md
for the full account): the first version of fit_ellipse_fitzgibbon() selected
the generalized eigenvector by eigenvalue sign ("pick the negative one"), a
rule copied from memory of public reference implementations without
re-deriving it for THIS script's specific sign convention of the constraint
matrix C. That rule is convention-dependent and was wrong here, making
Fitzgibbon's method look far more broken than it actually is. The correct,
convention-independent selection rule is a^T C a > 0 (the actual constraint,
eq. 6/9), which is what's implemented below.

Pipeline position: standalone exploratory script (like verify_heydemann_derivation.py),
not part of the installed package. Method 4 (Halir & Flusser, Day 18) and
Method 5 (Fitzgibbon, Day 19) reuse this corrected core algebra once promoted
into the package proper.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import scipy.linalg

# ---- 1. Synthetic ellipse point generator ----


@dataclass
class TrueEllipse:
    """Ground-truth ellipse parameters used to generate synthetic (x, y) points."""

    center_x: float
    center_y: float
    semi_major: float
    semi_minor: float
    rotation_rad: float

    def sample(
        self, n_points: int, arc_start_rad: float, arc_end_rad: float,
        noise_std: float, seed: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate n_points on this ellipse over the given angular arc, with
        additive Gaussian noise on the resulting (x, y) coordinates."""
        rng = np.random.default_rng(seed)
        theta = np.linspace(arc_start_rad, arc_end_rad, n_points)
        ex = self.semi_major * np.cos(theta)
        ey = self.semi_minor * np.sin(theta)
        cos_r, sin_r = np.cos(self.rotation_rad), np.sin(self.rotation_rad)
        x = self.center_x + ex * cos_r - ey * sin_r
        y = self.center_y + ex * sin_r + ey * cos_r
        x = x + rng.normal(0, noise_std, size=n_points)
        y = y + rng.normal(0, noise_std, size=n_points)
        return x, y


def true_conic_coefficients(ellipse: TrueEllipse) -> np.ndarray:
    """Converts geometric ellipse parameters to the [a,b,c,d,e,f] conic form
    (Halir & Flusser eq. 1), by rotating/translating the axis-aligned conic
    (x/semi_major)^2 + (y/semi_minor)^2 = 1."""
    cos_r, sin_r = np.cos(ellipse.rotation_rad), np.sin(ellipse.rotation_rad)
    p, q = 1 / ellipse.semi_major**2, 1 / ellipse.semi_minor**2
    a = p * cos_r**2 + q * sin_r**2
    b = 2 * (p - q) * cos_r * sin_r
    c = p * sin_r**2 + q * cos_r**2
    cx, cy = ellipse.center_x, ellipse.center_y
    d = -2 * a * cx - b * cy
    e = -b * cx - 2 * c * cy
    f = a * cx**2 + b * cx * cy + c * cy**2 - 1
    return np.array([a, b, c, d, e, f])


# ---- 2. Fitzgibbon (1999) naive direct formulation ----
# Equation provenance: Halir & Flusser 1998, eq. 1-10 (reproducing Fitzgibbon's
# original formulation as background) -- see notes/halir_flusser_1998.md.


def fit_ellipse_fitzgibbon(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray | None, str]:
    """Fitzgibbon et al.'s direct ellipse-specific least-squares fit: one 6x6
    generalized eigenvalue problem S*a = lambda*C*a (eq. 10), with the
    ellipse-specific solution among the 6 candidate eigenvectors selected by
    the ACTUAL constraint a^T C a > 0 (equivalently 4ac - b^2 > 0, eq. 2/6) --
    NOT by eigenvalue sign, which is a convention-dependent folklore rule (see
    this file's module docstring for the bug that taught this the hard way).

    Failure mode this demonstrates: C (eq. 9) is singular (rank 3). A
    generalized eigenvalue problem with singular C produces infinite
    eigenvalues for C's null-space directions, and under floating-point
    roundoff on ill-conditioned data, the remaining finite eigenvectors can
    (a) have NONE satisfying a^T C a > 0 (no valid ellipse found), or
    (b) have MORE THAN ONE satisfying it (genuine ambiguity, no principled way
    to pick between them) -- both observed empirically below, not assumed.

    Returns (coefficients [a,b,c,d,e,f] or None, status string).
    """
    design = np.column_stack([x**2, x * y, y**2, x, y, np.ones_like(x)])  # eq. 8
    scatter = design.T @ design  # S

    constraint = np.zeros((6, 6))  # C, eq. 9
    constraint[0, 2] = constraint[2, 0] = 2
    constraint[1, 1] = -1

    try:
        eigvals, eigvecs = scipy.linalg.eig(scatter, constraint)
    except (np.linalg.LinAlgError, ValueError) as exc:
        return None, f"generalized eigenvalue solve raised: {exc}"

    real_eigvecs = eigvecs.real
    # a^T C a for every candidate -- the actual constraint (eq. 6), convention-
    # independent unlike "pick the negative eigenvalue."
    a_t_c_a = np.array([real_eigvecs[:, i] @ constraint @ real_eigvecs[:, i] for i in range(6)])
    finite = np.all(np.isfinite(real_eigvecs), axis=0) & np.isfinite(eigvals.real)
    valid = finite & (a_t_c_a > 1e-9)

    n_candidates = int(np.sum(valid))
    if n_candidates == 0:
        return None, "no valid ellipse candidate (a^T C a > 0 unsatisfied by any eigenvector)"
    if n_candidates > 1:
        return None, f"AMBIGUOUS: {n_candidates} candidates satisfy a^T C a > 0"

    a = real_eigvecs[:, valid][:, 0]
    return a, "ok"


# ---- 3. Halir & Flusser (1998) numerically stable reformulation ----


def fit_ellipse_halir_flusser(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray | None, str]:
    """Halir & Flusser's numerically stable direct least-squares ellipse fit.

    Design decision: splits a=[a1;a2] into quadratic part a1=[a,b,c] and
    linear part a2=[d,e,f], and S into 3x3 blocks S1/S2/S3. Eliminating
    a2 = -S3^-1 S2^T a1 (valid whenever S3 is invertible -- generically true,
    unlike the full 6x6 C) reduces the problem to a 3x3 generalized
    eigenvalue problem on a1 alone, small enough that C1 (the nonzero 3x3
    block of C) is itself invertible -- removing the singular-matrix problem
    Fitzgibbon's direct approach cannot avoid.

    Returns (coefficients [a,b,c,d,e,f] or None, status string).
    """
    d1 = np.column_stack([x**2, x * y, y**2])
    d2 = np.column_stack([x, y, np.ones_like(x)])

    s1, s2, s3 = d1.T @ d1, d1.T @ d2, d2.T @ d2

    try:
        s3_inv = np.linalg.inv(s3)
    except np.linalg.LinAlgError:
        return None, "S3 (linear-block scatter matrix) is singular -- cannot eliminate a2"

    t_matrix = -s3_inv @ s2.T
    m_reduced = s1 + s2 @ t_matrix

    c1 = np.array([[0, 0, 2], [0, -1, 0], [2, 0, 0]], dtype=float)
    m_final = np.linalg.inv(c1) @ m_reduced  # C1 is invertible by construction, unlike full C

    eigvals, eigvecs = np.linalg.eig(m_final)
    cond = 4 * eigvecs[0, :] * eigvecs[2, :] - eigvecs[1, :] ** 2
    valid = (cond.real > 1e-9) & (np.abs(cond.imag) < 1e-9)

    n_candidates = int(np.sum(valid))
    if n_candidates == 0:
        return None, "no eigenvector satisfies the ellipse-specific condition (4ac - b^2 > 0)"

    a1 = eigvecs[:, valid][:, 0].real
    if not np.all(np.isfinite(a1)):
        return None, "selected eigenvector contains non-finite values"

    a2 = t_matrix @ a1
    return np.concatenate([a1, a2]), "ok"


# ---- 4. Comparison metric ----


def normalized_coefficient_error(fitted: np.ndarray, true_coeffs: np.ndarray) -> float:
    """Conic coefficients are defined only up to an arbitrary nonzero scale,
    so compare after normalizing both to unit L2 norm and aligning sign via
    the largest-magnitude component."""
    def normalize(v: np.ndarray) -> np.ndarray:
        v = v / np.linalg.norm(v)
        return v * np.sign(v[np.argmax(np.abs(v))])

    return float(np.linalg.norm(normalize(fitted) - normalize(true_coeffs)))


# ---- 5. The conditioning spectrum, evaluated over MANY seeds per regime ----
# (a single seed near the degenerate boundary is noise-realization-dependent
# and can mislead -- see docs/journal/day03.md for the specific case this
# caught: one seed showed Fitzgibbon beating Halir & Flusser at a moderately
# extreme arc, purely a fluke of that one noise draw.)


def build_conditioning_spectrum() -> dict[str, dict]:
    base = TrueEllipse(
        center_x=2.0, center_y=-1.0, semi_major=5.0, semi_minor=4.0, rotation_rad=0.3
    )
    thin = TrueEllipse(
        center_x=2.0, center_y=-1.0, semi_major=8.0, semi_minor=0.4, rotation_rad=0.3
    )
    very_thin = TrueEllipse(
        center_x=2.0, center_y=-1.0, semi_major=8.0, semi_minor=0.05, rotation_rad=0.3
    )
    return {
        "well_conditioned": dict(ellipse=base, n_points=60, arc=(0, 2 * np.pi), noise_std=0.02),
        "high_eccentricity": dict(ellipse=thin, n_points=60, arc=(0, 2 * np.pi), noise_std=0.02),
        "partial_arc_30deg": dict(ellipse=base, n_points=60, arc=(0, np.pi / 6), noise_std=0.02),
        "tight_clustering_3deg": dict(ellipse=base, n_points=60, arc=(0.7, 0.75), noise_std=0.02),
        "near_degenerate_15deg": dict(
            ellipse=very_thin, n_points=60, arc=(0, np.deg2rad(15)), noise_std=0.001
        ),
    }


def run_study(n_seeds: int = 30) -> list[dict]:
    spectrum = build_conditioning_spectrum()
    results = []
    for regime_name, cfg in spectrum.items():
        ellipse: TrueEllipse = cfg["ellipse"]
        true_coeffs = true_conic_coefficients(ellipse)

        fb_errors, hf_errors = [], []
        fb_fail_count, hf_fail_count = 0, 0
        cond_numbers = []

        for seed in range(n_seeds):
            x, y = ellipse.sample(cfg["n_points"], *cfg["arc"], cfg["noise_std"], seed=seed)
            design_full = np.column_stack([x**2, x * y, y**2, x, y, np.ones_like(x)])
            cond_numbers.append(np.linalg.cond(design_full))

            fb_coeffs, _ = fit_ellipse_fitzgibbon(x, y)
            hf_coeffs, _ = fit_ellipse_halir_flusser(x, y)

            if fb_coeffs is None:
                fb_fail_count += 1
            else:
                fb_errors.append(normalized_coefficient_error(fb_coeffs, true_coeffs))

            if hf_coeffs is None:
                hf_fail_count += 1
            else:
                hf_errors.append(normalized_coefficient_error(hf_coeffs, true_coeffs))

        results.append(dict(
            regime=regime_name,
            mean_cond_D=float(np.mean(cond_numbers)),
            fitzgibbon_fail_rate=fb_fail_count / n_seeds,
            fitzgibbon_mean_error=float(np.mean(fb_errors)) if fb_errors else float("nan"),
            fitzgibbon_std_error=float(np.std(fb_errors)) if fb_errors else float("nan"),
            halir_flusser_fail_rate=hf_fail_count / n_seeds,
            halir_flusser_mean_error=float(np.mean(hf_errors)) if hf_errors else float("nan"),
            halir_flusser_std_error=float(np.std(hf_errors)) if hf_errors else float("nan"),
            n_seeds=n_seeds,
        ))
    return results


def print_report(results: list[dict]) -> None:
    print(
        f"{'regime':<24}{'cond(D)':>10}{'FB fail%':>10}{'FB err':>16}"
        f"{'H&F fail%':>11}{'H&F err':>16}"
    )
    for r in results:
        fb_err = f"{r['fitzgibbon_mean_error']:.4f}+-{r['fitzgibbon_std_error']:.4f}"
        hf_err = f"{r['halir_flusser_mean_error']:.4f}+-{r['halir_flusser_std_error']:.4f}"
        print(
            f"{r['regime']:<24}{r['mean_cond_D']:>10.1e}"
            f"{r['fitzgibbon_fail_rate']*100:>9.0f}%{fb_err:>16}"
            f"{r['halir_flusser_fail_rate']*100:>10.0f}%{hf_err:>16}"
        )


def demonstrate_clean_divergence() -> None:
    """A single, targeted, reproducible case where the two methods genuinely
    diverge on IDENTICAL input: float32-precision data (simulating the
    single/limited-precision hardware Halir & Flusser's own paper benchmarked
    on -- 'MATLAB v5.0 on one SPARC Ultra-1', per their Conclusion) at a
    moderately extreme (not fully degenerate) 15-degree arc."""
    ellipse = TrueEllipse(2.0, -1.0, semi_major=8.0, semi_minor=0.001, rotation_rad=0.3)
    true_coeffs = true_conic_coefficients(ellipse)
    x, y = ellipse.sample(60, 0, np.deg2rad(15), 0.001, seed=0)
    x32, y32 = x.astype(np.float32).astype(np.float64), y.astype(np.float32).astype(np.float64)

    fb_coeffs, fb_status = fit_ellipse_fitzgibbon(x32, y32)
    hf_coeffs, hf_status = fit_ellipse_halir_flusser(x32, y32)

    print(
        "\n=== Clean divergence case: float32-precision data, "
        "15-degree arc, high eccentricity ==="
    )
    print(f"Fitzgibbon (naive):      {fb_status}")
    hf_error_suffix = (
        f", error={normalized_coefficient_error(hf_coeffs, true_coeffs):.4f}"
        if hf_coeffs is not None
        else ""
    )
    print(f"Halir & Flusser (stable): {hf_status}{hf_error_suffix}")


def make_plot(results: list[dict], output_path: str) -> None:
    """Grouped bar plot: mean coefficient recovery error (with std error bars)
    per regime, Fitzgibbon vs Halir & Flusser, annotated with failure rates
    since a silent NaN gap would hide the more important failure-rate finding."""
    regimes = [r["regime"] for r in results]
    x_pos = np.arange(len(regimes))
    width = 0.35

    fb_means = [r["fitzgibbon_mean_error"] for r in results]
    fb_stds = [r["fitzgibbon_std_error"] for r in results]
    hf_means = [r["halir_flusser_mean_error"] for r in results]
    hf_stds = [r["halir_flusser_std_error"] for r in results]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(
        x_pos - width / 2, [m if np.isfinite(m) else 0 for m in fb_means], width,
        yerr=[s if np.isfinite(s) else 0 for s in fb_stds],
        label="Fitzgibbon (naive)", color="#d62728", capsize=4,
    )
    ax.bar(
        x_pos + width / 2, [m if np.isfinite(m) else 0 for m in hf_means], width,
        yerr=[s if np.isfinite(s) else 0 for s in hf_stds],
        label="Halir & Flusser (stable)", color="#2ca02c", capsize=4,
    )

    for i, r in enumerate(results):
        ax.annotate(
            f"fail: {r['fitzgibbon_fail_rate']*100:.0f}%", (x_pos[i] - width / 2, 0.02),
            ha="center", fontsize=8, color="#d62728",
        )
        ax.annotate(
            f"fail: {r['halir_flusser_fail_rate']*100:.0f}%", (x_pos[i] + width / 2, 0.02),
            ha="center", fontsize=8, color="#2ca02c",
        )

    n_seeds = results[0]["n_seeds"]
    ax.set_ylabel(f"Mean normalized conic-coefficient error (n={n_seeds} seeds/regime)")
    ax.set_title(
        "Ellipse-fitting recovery error and failure rate across a conditioning spectrum\n"
        "(Fitzgibbon 1999 vs Halir & Flusser 1998, corrected selection rule)"
    )
    ax.set_xticks(x_pos)
    ax.set_xticklabels(regimes, rotation=15, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"\nPlot saved to {output_path}")


if __name__ == "__main__":
    results = run_study(n_seeds=30)
    print_report(results)
    demonstrate_clean_divergence()

    output_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(output_dir, exist_ok=True)
    make_plot(results, os.path.join(output_dir, "day03_ellipse_constraint_comparison.png"))
