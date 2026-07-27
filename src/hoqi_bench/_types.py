"""Shared type aliases for hoqi_bench. Kept in one place rather than
redefined identically in every module that needs it (pipeline.py,
transforms.py, noise.py, power_law.py all used to redefine this)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
