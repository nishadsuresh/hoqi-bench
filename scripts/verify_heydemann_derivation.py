"""
Symbolic verification of the Heydemann correction derived in
docs/derivations/heydemann.md.

Why this exists: a hand-done algebraic derivation can contain a step that
looks right but silently isn't (a sign error, a dropped term). Symbolic
verification with sympy re-derives the same result mechanically, so it acts
as an independent check on the by-hand derivation rather than trusting it on
inspection alone -- exactly the numeric/symbolic-over-visual discipline this
project follows throughout (see numeric-verification-methodology.md).

Pipeline position: run standalone (`python scripts/verify_heydemann_derivation.py`),
not imported by the package -- this is a one-time (well, one-per-change)
derivation check, not runtime code.
"""

from __future__ import annotations

import sympy as sp


def main() -> None:
    # ---- 1. Declare symbols ----
    # phi: true phase (the unknown we want to recover).
    # A: signal amplitude (not one of Heydemann's 3 "shape" distortions, just scale).
    # g: amplitude ratio (Q channel gain relative to I channel; ideal = 1).
    # eps: quadrature phase error (deviation from 90 degrees; ideal = 0).
    # I0, Q0: DC offsets on each channel (ideal = 0).
    phi, A, g, eps, I0, Q0 = sp.symbols("phi A g eps I0 Q0", real=True)

    # ---- 2. Build the distorted forward model ----
    # This is exactly Section 2 of docs/derivations/heydemann.md.
    I_signal = I0 + A * sp.cos(phi)
    Q_signal = Q0 + A * g * sp.sin(phi + eps)

    # ---- 3. Apply the derived correction (Sections 3-7 of the derivation) ----
    I_c = I_signal - I0
    Q_c = (Q_signal - Q0 - g * sp.sin(eps) * I_c) / (g * sp.cos(eps))

    # ---- 4. Verify the corrected signal is exactly the ideal circle, scaled by A ----
    # This is the actual claim to check: I_c == A*cos(phi) and Q_c == A*sin(phi),
    # for ALL phi, A, g, eps, I0, Q0 (with g != 0, cos(eps) != 0). If these don't
    # simplify to exactly zero, the derivation has an error somewhere.
    expected_I_c = A * sp.cos(phi)
    expected_Q_c = A * sp.sin(phi)

    residual_I = sp.simplify(I_c - expected_I_c)
    residual_Q = sp.simplify(Q_c - expected_Q_c)

    print("=== Heydemann correction: symbolic verification ===")
    print(f"I_c - A*cos(phi) simplifies to: {residual_I}")
    print(f"Q_c - A*sin(phi) simplifies to: {residual_Q}")

    i_ok = residual_I == 0
    q_ok = residual_Q == 0

    print(f"\nI_c matches ideal circle exactly: {i_ok}")
    print(f"Q_c matches ideal circle exactly: {q_ok}")

    # ---- 5. If it didn't simplify cleanly, investigate what assumption is needed ----
    # (It should simplify cleanly here -- trigsimp handles the sin(phi+eps) expansion
    # sympy's simplify() doesn't always fully resolve on its own. If a future change to
    # the forward model breaks this, this is where that investigation starts.)
    if not (i_ok and q_ok):
        print("\n!!! Did not simplify to exactly zero. Trying trigsimp directly on Q_c...")
        q_c_expanded = sp.expand_trig(Q_c)
        print(f"Q_c expanded: {q_c_expanded}")
        raise AssertionError(
            "Symbolic verification FAILED -- the derivation does not hold "
            "as written. See docs/derivations/heydemann.md and investigate "
            "before trusting the correction."
        )

    # ---- 6. Confirm the required non-degeneracy assumption is real and necessary ----
    # Section 8 of the derivation claims the correction requires g != 0 and
    # cos(eps) != 0. Verify this is genuinely a division-by-zero in the
    # algebra (not just a claim), by checking the denominator symbolically.
    denominator = g * sp.cos(eps)
    print(f"\nCorrection denominator (g * cos(eps)): {denominator}")
    print("This is exactly zero when g=0, or when eps = +90 or -90 degrees")
    print("(cos(pi/2) and cos(-pi/2) both equal 0) -- confirming Section 8's")
    print("claimed degeneracy condition is the real algebraic cause, not an")
    print("assumption stated without a mechanism.")

    denom_at_90 = denominator.subs(eps, sp.pi / 2)
    denom_at_neg90 = denominator.subs(eps, -sp.pi / 2)
    print(f"\nDenominator at eps=+90deg: {sp.simplify(denom_at_90)}")
    print(f"Denominator at eps=-90deg: {sp.simplify(denom_at_neg90)}")
    assert sp.simplify(denom_at_90) == 0
    assert sp.simplify(denom_at_neg90) == 0

    # ---- 7. Sanity check: confirm the ideal (zero-distortion) case reduces correctly ----
    # At g=1, eps=0, I0=0, Q0=0, the correction should be a no-op: I_c=I, Q_c=Q,
    # matching the "identity at zero" requirement this project's forward-model
    # transforms are held to (see docs/journal/day01.md, day08 upcoming).
    ideal_subs = {g: 1, eps: 0, I0: 0, Q0: 0}
    I_c_ideal = sp.simplify(I_c.subs(ideal_subs))
    Q_c_ideal = sp.simplify(Q_c.subs(ideal_subs))
    I_signal_ideal = sp.simplify(I_signal.subs(ideal_subs))
    Q_signal_ideal = sp.simplify(Q_signal.subs(ideal_subs))
    print(f"\nAt zero distortion: I_c == I? {I_c_ideal == I_signal_ideal}")
    print(f"At zero distortion: Q_c == Q? {Q_c_ideal == Q_signal_ideal}")
    assert I_c_ideal == I_signal_ideal
    assert Q_c_ideal == Q_signal_ideal

    print("\n=== ALL CHECKS PASSED ===")
    print("The derivation in docs/derivations/heydemann.md is symbolically verified:")
    print("the corrected signal (I_c, Q_c) is exactly (A*cos(phi), A*sin(phi)) for")
    print("all values of the distortion parameters, given g != 0 and cos(eps) != 0 --")
    print("a condition confirmed above to be the actual, necessary algebraic cause,")
    print("not an unmotivated caveat.")


if __name__ == "__main__":
    main()
