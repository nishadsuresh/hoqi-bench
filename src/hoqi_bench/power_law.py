"""
Power-law characterization of residual nonlinearity, per Lehmann et al.
2025 (RQ3, `docs/PREREGISTRATION.md`).

IMPORTANT SCOPE NOTE, resolved with Nishad on Day 13 rather than guessed:
Lehmann et al. 2025's "power-law nonlinearity" is NOT a distinct,
injectable forward-model distortion mechanism the way amplitude imbalance,
quadrature phase error, and DC offset are (`transforms.py`). Reading the
actual paper (`notes/lehmann_2025.md`) shows it is an EMPIRICALLY OBSERVED
SCALING RELATIONSHIP: after ellipse correction, their residual nonlinearity
(measured via a noise-floor harmonic's prominence) scales with motion range
roughly as a power of 3 (Section III.C: "residual nonlinearity follows a
power-law trend (close to power of 3)"). There is no single equation in the
paper describing a distortion MECHANISM with that name to inject into a
forward model.

Per Day 6's preregistration (revision item 3) and confirmed directly with
Nishad on Day 13: this module does NOT add a new forward-model transform.
Instead, it provides the ANALYSIS function needed to characterize this
relationship in already-collected sweep data (error vs. distortion
magnitude, from the existing transforms.py mechanisms) -- fitting a power
law to that relationship and checking whether the recovered exponent is
close to Lehmann's reported ~3. The stated fallback, if this produces no
clean power-law relationship at all in this project's own sweep data
(a real, reportable possibility, not a failure to hide): treat power-law as
a separate injected forward-model transform instead, built and tested the
way hysteresis will be (Day 14).

Equation provenance: log-log linear regression is the standard technique
for power-law exponent estimation (error = c * magnitude^n implies
log(error) = log(c) + n*log(magnitude), linear in log-log space, solvable
by ordinary least squares) -- not specific to Lehmann et al., a general
statistical method applied to their reported relationship.

Pipeline position: called by Day 30's RQ3 analysis (once Days 15-20's
methods exist and produce real error-vs-magnitude sweep data), not by the
forward model itself -- this module has no `Transform`-compatible function
and is never composed into `pipeline.apply_pipeline`'s transform sequence.
"""

from __future__ import annotations

import numpy as np

from hoqi_bench._types import AnyFloatArray


def fit_power_law_exponent(
    magnitudes: AnyFloatArray, errors: AnyFloatArray
) -> tuple[float, float, float]:
    """Fits `error = coefficient * magnitude^exponent` via log-log linear
    regression. Returns (exponent, coefficient, r_squared).

    `r_squared` (coefficient of determination of the LOG-LOG fit) is
    returned alongside the exponent deliberately -- per this module's
    fallback plan, a low r_squared here (no clean power-law relationship in
    this project's own data) is itself the trigger to fall back to modeling
    power-law as an injected transform instead, not something to discard
    silently.

    Design decision: fits in log-log space (ordinary least squares on
    log(magnitude) vs log(error)) rather than nonlinear least squares
    directly on `error = c*magnitude^n` -- the log-log form is linear in its
    parameters, so it has a unique, closed-form solution with no risk of a
    nonlinear optimizer converging to a local minimum; standard practice for
    power-law exponent estimation.

    Failure mode: requires all `magnitudes` and `errors` to be strictly
    positive (log of zero or a negative number is undefined) -- a zero
    entry (e.g. the identity/no-distortion condition, where error may be
    exactly 0) must be excluded by the caller before calling this function,
    not passed in and silently producing NaN/-inf.
    """
    # ---- 1. Reject inputs a log-log fit cannot handle ----
    if np.any(magnitudes <= 0) or np.any(errors <= 0):
        raise ValueError(
            "fit_power_law_exponent requires strictly positive magnitudes and errors "
            "(log-log fit is undefined at zero or negative values) -- exclude the "
            "zero-distortion / zero-error condition before calling this function"
        )

    # ---- 2. Linearize: log(error) = exponent*log(magnitude) + log(coefficient) ----
    log_magnitudes = np.log(magnitudes)
    log_errors = np.log(errors)

    # ---- 3. Ordinary least squares in log-log space ----
    design = np.column_stack([log_magnitudes, np.ones_like(log_magnitudes)])
    coeffs, _, _, _ = np.linalg.lstsq(design, log_errors, rcond=None)
    exponent, log_coefficient = coeffs
    coefficient = np.exp(log_coefficient)

    # ---- 4. Goodness of fit (R^2), returned so a poor fit is visible, not hidden ----
    predicted_log_errors = design @ coeffs
    ss_res = np.sum((log_errors - predicted_log_errors) ** 2)
    ss_tot = np.sum((log_errors - np.mean(log_errors)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return float(exponent), float(coefficient), float(r_squared)
