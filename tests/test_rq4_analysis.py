"""
Tests for scripts.rq4_analysis -- Week 5 Task 5, Day 33. Focused on
`_first_diverging_pair`, the fix for the real bug found on Day 33
(docs/journal/day33.md): an earlier version always tested
`gaussian_ranking[0]` for significance regardless of which methods
actually swapped position, so every "significant" result was measuring
an irrelevant method's noise floor.
"""

from __future__ import annotations

from scripts.rq4_analysis import _first_diverging_pair


def test_identical_rankings_have_no_divergence() -> None:
    ranking = ["heydemann", "halir_flusser", "fitzgibbon", "kasa"]
    assert _first_diverging_pair(ranking, list(ranking)) is None


def test_divergence_at_the_top_is_found() -> None:
    a = ["heydemann", "halir_flusser", "fitzgibbon"]
    b = ["halir_flusser", "heydemann", "fitzgibbon"]
    assert _first_diverging_pair(a, b) == ("heydemann", "halir_flusser")


def test_divergence_deep_in_the_ranking_is_found_not_the_top() -> None:
    """The exact bug shape: the two rankings AGREE at position 0 (the
    tautologically-favored method per
    docs/STRUCTURAL_ADVANTAGE_PREDICTIONS.md) and diverge only at
    position 2 -- the returned pair must be the position-2 methods, not
    position 0's method paired with itself."""
    a = ["heydemann", "halir_flusser", "fitzgibbon", "koning_wimmer_witkovsky"]
    b = ["heydemann", "halir_flusser", "koning_wimmer_witkovsky", "fitzgibbon"]
    assert _first_diverging_pair(a, b) == ("fitzgibbon", "koning_wimmer_witkovsky")


def test_only_the_first_divergence_is_returned_not_every_later_one() -> None:
    """A single swap near the top cascades into every later position
    also 'differing' under a naive comparison -- only the first, actual
    swap should be returned."""
    a = ["heydemann", "kasa", "taubin", "raw_atan2"]
    b = ["kasa", "heydemann", "taubin", "raw_atan2"]
    assert _first_diverging_pair(a, b) == ("heydemann", "kasa")
