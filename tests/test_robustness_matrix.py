"""
Day 20's robustness matrix, enforced as a permanent CI check: every method
(7) against every adversarial input category (5) -- 35 cells -- must
never crash. A crash mid-sweep would corrupt the Week 4 campaign
(docs/WEEK3-4_PLAN.md Day 20); "graceful failure with a reason code" is
the only acceptable non-success outcome.

Real, non-obvious results found while building the underlying matrix
(scripts/robustness_matrix.py, run once and reported in
docs/journal/day20.md): zero crashes across all 35 cells on the first
real run -- every method's own failure-mode guard (built across Days
17-20, each verified independently against its own adversarial
conditions) held up here too, not just against the specific conditions
each was originally tested against.
"""

from __future__ import annotations

from hoqi_bench.methods import METHOD_REGISTRY
from scripts.robustness_matrix import ADVERSARIAL_INPUTS, classify


def test_no_method_crashes_on_any_adversarial_input() -> None:
    crashes = []
    for method_name in METHOD_REGISTRY:
        for input_name, input_fn in ADVERSARIAL_INPUTS.items():
            i, q = input_fn()
            outcome = classify(method_name, i, q)
            if outcome.startswith("CRASH"):
                crashes.append(f"{method_name} / {input_name}: {outcome}")

    assert not crashes, "found crashes:\n" + "\n".join(crashes)


def test_matrix_covers_all_seven_methods_and_five_input_categories() -> None:
    """A guard against the matrix silently shrinking (e.g. a future
    method registration bug dropping an entry) -- the counts themselves
    are the acceptance criterion the plan names ('every method... every
    adversarial input'), not just 'zero crashes among whatever ran'."""
    assert len(METHOD_REGISTRY) == 7, f"expected 7 methods, found {len(METHOD_REGISTRY)}"
    assert len(ADVERSARIAL_INPUTS) == 5, (
        f"expected 5 input categories, found {len(ADVERSARIAL_INPUTS)}"
    )
