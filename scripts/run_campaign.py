"""
Campaign entry point: `python scripts/run_campaign.py [config] [output_dir]`.

Thin by design -- every decision lives in `hoqi_bench.runner`, so that the
thing Day 27 launches and the thing Day 24's tests exercise are the same
code. A script that reimplements any part of the runner is a script that
can drift from what was tested.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from hoqi_bench.config import load_sweep_config
from hoqi_bench.resolve import iter_conditions
from hoqi_bench.runner import condition_filename, run_campaign

DEFAULT_CONFIG = Path(__file__).parent.parent / "configs" / "main_campaign.toml"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "results" / "raw"


def main() -> int:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    config = load_sweep_config(config_path)
    conditions = iter_conditions(config)
    total_fits = len(conditions) * len(config.methods) * config.n_seeds

    already_done = sum(1 for c in conditions if (output_dir / condition_filename(c.name)).exists())
    print(f"config:     {config_path}")
    print(f"output:     {output_dir}")
    print(f"conditions: {len(conditions)} ({already_done} already complete)")
    print(f"methods:    {len(config.methods)}  seeds: {config.n_seeds}")
    print(f"total fits: {total_fits:,}")

    start = time.perf_counter()
    run_campaign(config, output_dir, resume=True)
    elapsed = time.perf_counter() - start

    print(f"done in {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
