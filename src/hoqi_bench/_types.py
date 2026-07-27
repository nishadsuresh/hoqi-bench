"""Shared type aliases for hoqi_bench. Kept in one place rather than
redefined identically in every module that needs it (pipeline.py,
transforms.py, noise.py, power_law.py all used to redefine this)."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

# For functions that do dtype-independent arithmetic (log, lstsq, etc.) and
# have no reason to require float64 specifically -- numpy's own generic
# functions (e.g. np.linspace) return NDArray[floating[Any]], not
# NDArray[float64], so a strict FloatArray parameter forces every caller to
# cast for no functional reason. Use FloatArray for module-internal signal
# data (where the precision is a real invariant, per Day 7's forward model);
# use this for boundary functions like power_law.fit_power_law_exponent that
# accept whatever float array a caller happens to have.
AnyFloatArray = NDArray[np.floating[Any]]
