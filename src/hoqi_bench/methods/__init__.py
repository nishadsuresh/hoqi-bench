"""
Registry of every implemented phase-recovery method, name -> `fit()`
callable (`methods.base.PhaseRecoveryMethod`).

Why this exists: Week 4's sweep runner (Day 24, not yet built) needs to
iterate "every method" without hardcoding a list of imports at the call
site, and `config.SweepConfig.methods` (a list of name strings, loaded
from TOML) needs a name -> callable lookup to actually run what a config
requests. Built incrementally as each Day 15-20 method lands -- this file
is updated once per new method, not written all at once, so `METHOD_REGISTRY`
always reflects exactly what's implemented so far, not the full eventual
set of 7 ahead of schedule.

Pipeline position: imported by Week 4's sweep runner; also usable directly
by any Week 3 method's own test (e.g. Day 21's cross-validation gate,
which needs every method callable by name in one place).
"""

from __future__ import annotations

from hoqi_bench.methods import (
    fitzgibbon,
    halir_flusser,
    heydemann,
    kasa,
    koning_wimmer_witkovsky,
    raw_atan2,
    taubin,
)
from hoqi_bench.methods.base import FitResult, PhaseRecoveryMethod, failed_result, timed_fit

METHOD_REGISTRY: dict[str, PhaseRecoveryMethod] = {
    raw_atan2.NAME: raw_atan2.fit,
    kasa.NAME: kasa.fit,
    heydemann.NAME: heydemann.fit,
    halir_flusser.NAME: halir_flusser.fit,
    fitzgibbon.NAME: fitzgibbon.fit,
    taubin.NAME: taubin.fit,
    koning_wimmer_witkovsky.NAME: koning_wimmer_witkovsky.fit,
}

__all__ = [
    "METHOD_REGISTRY",
    "FitResult",
    "PhaseRecoveryMethod",
    "failed_result",
    "timed_fit",
]
