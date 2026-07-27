"""
Day 20 runtime probe + a real, previously-observed crash, guarded against
regressing.

Running the full 125,650-run campaign as a standalone script (bypassing
conftest.py's BLAS-threading pin, since a bare `python -c` invocation
never imports it) crashed partway through with `SystemError: attempting
to create PyCFunction with class but no METH_METHOD flag` -- a low-level
numpy/BLAS internal error under sustained multi-threaded contention across
tens of thousands of rapid `np.linalg` calls. The identical script with
`OMP_NUM_THREADS=1`/`OPENBLAS_NUM_THREADS=1`/`MKL_NUM_THREADS=1` set
completed cleanly in 14.32s, zero crashes -- see conftest.py's own
docstring for the full account. This upgrades that pin from "prevents
non-determinism" to "prevents an actual crash" for Day 24's sweep runner.

This test does NOT re-run the full campaign (that belongs to Day 24's
actual runner and Day 26's smoke test, not the fast unit-test suite) --
it runs enough back-to-back method calls, under pytest's own
conftest.py-pinned process, to be a real stress test of the same
sustained-load pattern that triggered the original crash, without adding
14+ seconds to every CI run.
"""

from __future__ import annotations

from pathlib import Path

from hoqi_bench.config import load_sweep_config
from hoqi_bench.methods import METHOD_REGISTRY
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.simulate import simulate_condition

MAIN_CAMPAIGN_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"


def test_sustained_load_across_all_methods_does_not_crash() -> None:
    """~50 real conditions x 7 methods x 5 seeds = ~1750 back-to-back
    fits, including Koning's iterative np.linalg-heavy path repeatedly --
    the same sustained-load shape that crashed without the BLAS pin.
    Under pytest (conftest.py's pin active), this must complete cleanly."""
    config = load_sweep_config(MAIN_CAMPAIGN_CONFIG)
    conditions = iter_conditions(config)[::7]  # every 7th condition, ~51 total
    assert len(conditions) >= 40

    n_completed = 0
    for condition in conditions:
        for seed_index in range(5):
            signal = simulate_condition(condition.resolved, condition.name, seed_index)
            for name, fit_fn in METHOD_REGISTRY.items():
                kwargs = (
                    {"mean_intensity": condition.resolved["mean_intensity"]}
                    if name == "raw_atan2"
                    else {}
                )
                fit_fn(signal.i, signal.q, **kwargs)  # must not raise
                n_completed += 1

    assert n_completed >= 40 * 5 * 7
