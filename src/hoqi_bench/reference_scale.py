"""
The physical reference scale: what a displacement error of a given size
actually MEANS for a real homodyne quadrature interferometer.

Why this exists (`docs/WEEK3-4_PLAN.md` §0.6, the Outsider advisor's
finding, scheduled for Day 22): without it, 125,650 runs produce a ranking
nobody can act on. "Method A achieves 0.3 mrad RMS" is not a result until
someone can say whether 0.3 mrad is comfortable, marginal, or useless for
the instrument this benchmark is about. Every number below is grounded in
Lehmann et al. 2025 (arXiv:2511.04386, `refs/references.bib`
`Lehmann2025`), the real-hardware anchor this simulation-only project
extends from, with the section each figure comes from named so a reader can
check it rather than trust it.

**The headline consequence, and the reason this is not a decorative
constant file.** The preregistered breakdown tolerance is 1% relative RMS
error (`configs/main_campaign.toml`'s `tolerance = 0.01`). At
`arc_fraction = 1.0` the record's full scale is one fringe, `lambda/2 =
316.4 nm` for the HeNe wavelength this project uses, so 1% of full scale is
**3.16 nm** of displacement error. Lehmann et al. measure on-resonance
motion "always less than 5 nm, and often even below 1 nm" (Section III.3).
So a method that merely satisfies the preregistered tolerance has an error
comparable to the entire signal that paper is measuring, and roughly
**31,600x** the sub-100 fm sensitivity a HoQI exists to deliver.

That is not an argument for changing the preregistered tolerance -- it was
committed pre-data and stays (`docs/PREREGISTRATION.md`). It is the reason
Week 4's reporting must place every result on the scale below as well as
against that tolerance, or it will describe methods as "within tolerance"
that are useless for the application.

Pipeline position: consumed by Day 28's analysis and by any plot axis or
results table that quotes a displacement error; imported by `aggregate.py`
only for the gross-error threshold's own justification. Deliberately
separate from `metrics.py`, which answers "how big is the error" -- this
module answers "is that big".
"""

from __future__ import annotations

from hoqi_bench.forward_model import HENE_WAVELENGTH_M

# ---- 1. What the instrument can do (Lehmann et al. 2025) ----

# Abstract: HoQIs offer "sensitivities in the sub 100 fm regime, at
# frequencies from 1 Hz and above". Section II.2: "noise floors below
# 1e-13 m/sqrt(Hz) can be achieved for stationary test masses". A
# phase-recovery error below this is invisible against the instrument's own
# noise -- there is nothing to be gained by a method being more accurate
# than this, and any method above it is the limiting factor rather than the
# hardware.
INSTRUMENT_NOISE_FLOOR_M = 1.0e-13

# Section III.3: on-resonance motion "always less than 5 nm, and often even
# below 1 nm". This is the signal a HoQI is actually measuring in the
# reference application, so it is the right denominator for "what fraction
# of the measurement does this method's error consume".
TYPICAL_MEASURED_MOTION_M = 1.0e-9

# Section IV.2: sub-FSR working range of "0.1-0.3 um"; Section III.2: near
# full-FSR excursions of "just under one FSR"; Section III.1: up to "5 FSRs"
# during ringdown excitation. Recorded for context on what `arc_fraction`
# spans physically -- the campaign's arc_fraction=1.0 is one FSR.
SUB_FSR_WORKING_RANGE_M = (1.0e-7, 3.0e-7)

# ---- 2. What the campaign's own numbers mean on that scale ----

# One full fringe of phase (2*pi) is lambda/2 of mirror displacement -- the
# double-pass factor of 4 in forward_model.py's phi = 4*pi*x/lambda. This is
# the full scale of a record at arc_fraction = 1.0.
FULL_FRINGE_DISPLACEMENT_M = HENE_WAVELENGTH_M / 2

# The preregistered 1% relative RMS tolerance, expressed in meters at full
# arc coverage -- see this module's docstring for why this number is the
# point of the whole file.
PREREGISTERED_TOLERANCE_M = 0.01 * FULL_FRINGE_DISPLACEMENT_M

# ---- 3. The interpretive bands Day 28 reports against ----
#
# Fixed here, before any campaign result exists, so that a band cannot be
# drawn around whatever the results turn out to be. Three bands, each
# anchored to a measured quantity above rather than to a round number:
#
#   negligible   error <= the instrument's own noise floor. The method is
#                not the limiting factor; hardware is.
#   usable       error <= 1% of the typical measured motion (10 pm). The
#                method consumes at most a hundredth of the signal being
#                measured -- the conventional "measurement system is not
#                the dominant uncertainty" bar.
#   marginal     error <= the typical measured motion itself (1 nm). The
#                method's error is the same size as the signal. Reportable,
#                but not usable for this application.
#   unusable     anything larger, including everything that merely meets
#                the preregistered 3.16 nm tolerance.
NEGLIGIBLE_ERROR_M = INSTRUMENT_NOISE_FLOOR_M
USABLE_ERROR_M = 0.01 * TYPICAL_MEASURED_MOTION_M
MARGINAL_ERROR_M = TYPICAL_MEASURED_MOTION_M


def classify_displacement_error(error_m: float) -> str:
    """Places a displacement RMSE on the bands above: `"negligible"`,
    `"usable"`, `"marginal"`, or `"unusable"`.

    Design decision -- returns a plain string rather than an enum, matching
    this project's convention of plain data over behavior-carrying objects
    (`methods/base.py`'s own registry-of-functions note), and because these
    labels go straight into a results table and a plot legend.

    Failure mode: a NaN error (a failed fit that bypassed `aggregate.py`'s
    explicit exclusion) classifies as `"unusable"`, since every comparison
    against a NaN is False. That is the correct direction to fail in, but it
    means this function must not be used to DETECT failure -- use the
    `failed` flag for that, per `docs/WEEK3_METHOD_CONTRACT.md` §2.
    """
    if error_m <= NEGLIGIBLE_ERROR_M:
        return "negligible"
    if error_m <= USABLE_ERROR_M:
        return "usable"
    if error_m <= MARGINAL_ERROR_M:
        return "marginal"
    return "unusable"
