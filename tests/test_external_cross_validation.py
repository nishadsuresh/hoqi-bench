"""
Tier 2 external cross-validation (docs/WEEK3-4_PLAN.md Day 19, moved up
from Day 21 deliberately -- days of debugging headroom instead of hours
before a blocking gate).

Cross-checks this project's Halir & Flusser and Fitzgibbon implementations
against two independently-installed, independently-authored packages:
`lsq-ellipse` (Halir & Flusser only) and `ellipsinator` (both Halir &
Flusser and a Fitzgibbon-family fit). Requires the `validation` extra
(`pip install -e ".[validation]"`) -- NEVER a runtime dependency of the
package itself, only of this test file.

**Known coverage hole, stated plainly, not hidden**: these two packages
cover only Halir & Flusser and Fitzgibbon -- the two most algebraically
similar of this project's 7 methods. Kasa, Heydemann, Taubin, and Koning
remain externally uncrossed here and rely on the Tier 1 analytic oracle
(Day 21) instead.

This test is machine-checkable and runs in CI on every future commit --
stronger, ongoing evidence than a one-time paper-replication check would
have been (see docs/WEEK3-4_PLAN.md Part 0.1 for the full reasoning on why
this replaced the original build plan's Day 21 literature-reproduction
criterion).
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("ellipse", reason="requires the 'validation' extra")
pytest.importorskip("ellipsinator", reason="requires the 'validation' extra")

import ellipsinator  # noqa: E402
from ellipse import LsqEllipse  # noqa: E402

from hoqi_bench._types import FloatArray  # noqa: E402
from hoqi_bench.methods.fitzgibbon import _fit_ellipse_conic as fit_fitzgibbon_conic  # noqa: E402
from hoqi_bench.methods.halir_flusser import _fit_ellipse_conic as fit_hf_conic  # noqa: E402


def _sample_ellipse(
    center_x: float,
    center_y: float,
    semi_major: float,
    semi_minor: float,
    rotation_rad: float,
    n_points: int,
    seed: int,
) -> tuple[FloatArray, FloatArray]:
    rng = np.random.default_rng(seed)
    theta = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    ex, ey = semi_major * np.cos(theta), semi_minor * np.sin(theta)
    cos_r, sin_r = np.cos(rotation_rad), np.sin(rotation_rad)
    x = center_x + ex * cos_r - ey * sin_r + rng.normal(0, 0.02, n_points)
    y = center_y + ex * sin_r + ey * cos_r + rng.normal(0, 0.02, n_points)
    return x, y


def _normalized_distance(a: FloatArray, b: FloatArray) -> float:
    """Ellipse conics are defined only up to overall scale AND sign --
    normalize both to unit norm and take the smaller of the two possible
    sign alignments, matching this project's established methodology
    (tests/test_halir_flusser.py, tests/test_fitzgibbon.py)."""
    a_n = a / np.linalg.norm(a)
    b_n = b / np.linalg.norm(b)
    return float(min(np.linalg.norm(a_n - b_n), np.linalg.norm(a_n + b_n)))


# Well-conditioned regime only (Day 3's own conditioning-spectrum
# terminology) -- the regime where all four fits (this project's two,
# plus both external packages) are expected to closely agree; Day 3
# already established that even THIS project's own two methods diverge
# by design in ill-conditioned regimes, so cross-package agreement is only
# a meaningful check where convergence is expected in the first place.
_WELL_CONDITIONED: dict[str, float] = dict(
    center_x=2.0, center_y=-1.0, semi_major=5.0, semi_minor=4.0, rotation_rad=0.3
)
_N_POINTS = 60


def test_halir_flusser_matches_lsq_ellipse() -> None:
    x, y = _sample_ellipse(**_WELL_CONDITIONED, n_points=_N_POINTS, seed=0)

    ours = fit_hf_conic(x, y)
    assert ours is not None

    external = LsqEllipse().fit(np.c_[x, y]).coef_.ravel()

    distance = _normalized_distance(np.array(ours), external)
    assert distance < 1e-6, f"normalized distance from lsq-ellipse: {distance:.2e}"


def test_halir_flusser_matches_ellipsinator() -> None:
    x, y = _sample_ellipse(**_WELL_CONDITIONED, n_points=_N_POINTS, seed=1)

    ours = fit_hf_conic(x, y)
    assert ours is not None

    external = ellipsinator.fit_ellipse_halir(x, y)

    distance = _normalized_distance(np.array(ours), external)
    assert distance < 1e-6, f"normalized distance from ellipsinator: {distance:.2e}"


def test_fitzgibbon_matches_ellipsinator() -> None:
    """Tolerance 1e-3, not the 1e-6 Halir & Flusser gets: Fitzgibbon's
    unreduced 6x6 system with a singular constraint matrix is the LESS
    numerically stable path by design (the entire reason Halir & Flusser's
    paper exists) -- independent eigenvalue solvers (this project's
    scipy.linalg.eig vs. ellipsinator's own implementation) show a real,
    small, seed-independent floating-point difference here (measured
    1.0e-5 to 2.1e-5 across 10 seeds), unlike Halir & Flusser's well-
    conditioned reduced system, which agrees to near machine precision.
    1e-3 keeps ~50x margin above the observed range while still being an
    extremely tight agreement bound in absolute terms."""
    x, y = _sample_ellipse(**_WELL_CONDITIONED, n_points=_N_POINTS, seed=2)

    ours = fit_fitzgibbon_conic(x, y)
    assert ours is not None

    external = ellipsinator.fit_ellipse_fitzgibon(x, y)

    distance = _normalized_distance(np.array(ours), external)
    assert distance < 1e-3, f"normalized distance from ellipsinator: {distance:.2e}"


def test_all_three_agree_with_each_other_across_several_seeds() -> None:
    """A stronger, ongoing regression guard than any single-seed check:
    5 independent seeds, all four fits (this project's HF and Fitzgibbon,
    lsq-ellipse, ellipsinator's HF and Fitzgibbon) must mutually agree.

    Tolerance 1e-3 throughout (not the 1e-6 an HF-only comparison could
    use): this loop compares EVERY pair, including Fitzgibbon-vs-anything
    pairs, which carry Fitzgibbon's own real, small, less-stable-by-design
    floating-point spread -- see test_fitzgibbon_matches_ellipsinator's
    docstring for the measured magnitude this is grounded in."""
    for seed in range(5):
        x, y = _sample_ellipse(**_WELL_CONDITIONED, n_points=_N_POINTS, seed=seed)

        our_hf = fit_hf_conic(x, y)
        our_fb = fit_fitzgibbon_conic(x, y)
        assert our_hf is not None
        assert our_fb is not None

        lsq = LsqEllipse().fit(np.c_[x, y]).coef_.ravel()
        ell_hf = ellipsinator.fit_ellipse_halir(x, y)
        ell_fb = ellipsinator.fit_ellipse_fitzgibon(x, y)

        candidates = [np.array(our_hf), np.array(our_fb), lsq, ell_hf, ell_fb]
        for i, a in enumerate(candidates):
            for b in candidates[i + 1 :]:
                distance = _normalized_distance(a, b)
                assert distance < 1e-3, f"seed={seed}: distance={distance:.2e} between two fits"
