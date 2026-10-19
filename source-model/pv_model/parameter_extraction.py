"""
pv_model/parameter_extraction.py

Extracts single-diode model parameters (Iph, I0, Rs, Rsh) at STC from
datasheet-style four points (Voc, Isc, Vmpp, Impp) plus an assumed ideality
factor n. Method: standard iterative approach (consistent with the
NR-based extraction literature logged in docs/literature_gap_table.md,
arXiv:1601.03257) --

Given a trial (Rs, Rsh):
  1. Iph and I0 are found in closed form by solving two LINEAR equations:
       (a) I=0 at V=Voc:  Iph - I0*(exp(Voc/Vt)-1) - Voc/Rsh = 0
       (b) I=Isc at V=0:  Iph - I0*(exp(Isc*Rs/Vt)-1) - Isc*Rs/Rsh - Isc = 0
  2. With (Iph, I0) known, solve the implicit diode equation for I(V) via
     Newton-Raphson at V=Vmpp, and evaluate two residuals:
       r1 = P(Vmpp) - Vmpp*Impp        (module must produce rated power at Vmpp)
       r2 = dP/dV at Vmpp              (Vmpp must actually be the power peak)
  3. Outer 2D root-find (scipy.optimize.fsolve) over (Rs, Rsh) drives r1,r2 -> 0.

This is a numerically-solved fit, not a guessed/hardcoded pair -- required by
the master prompt's "numerically stable solver" instruction.
"""

import numpy as np
from scipy.optimize import fsolve

from parameters import PANEL, thermal_voltage, T_STC


def solve_iph_i0(Rs, Rsh, Voc, Isc, Vt):
    """Solve the 2x2 linear system for (Iph, I0) given a trial Rs, Rsh."""
    a11, a12 = 1.0, -(np.exp(Voc / Vt) - 1.0)
    a21, a22 = 1.0, -(np.exp(Isc * Rs / Vt) - 1.0)
    A = np.array([[a11, a12], [a21, a22]])
    b = np.array([Voc / Rsh, Isc + Isc * Rs / Rsh])
    Iph, I0 = np.linalg.solve(A, b)
    return Iph, I0


def current_at_voltage(V, Iph, I0, Rs, Rsh, Vt, I_guess=None, tol=1e-10, max_iter=100):
    """Newton-Raphson solve of the implicit single-diode equation for I at
    a given V. Returns NaN (not a silently wrong number) if it fails to
    converge, so callers can detect and report failures rather than plot
    garbage."""
    I = Iph if I_guess is None else I_guess
    for _ in range(max_iter):
        exp_term = np.exp((V + I * Rs) / Vt)
        f = Iph - I0 * (exp_term - 1.0) - (V + I * Rs) / Rsh - I
        df_dI = -I0 * exp_term * Rs / Vt - Rs / Rsh - 1.0
        if df_dI == 0:
            return np.nan
        dI = f / df_dI
        I_new = I - dI
        if abs(I_new - I) < tol:
            return I_new
        I = I_new
    return np.nan  # did not converge


def _residuals(x, Voc, Isc, Vmpp, Impp, Vt, dV=1e-4):
    Rs, Rsh = x
    if Rs < 0 or Rsh < 1.0:
        return [1e6, 1e6]  # keep solver away from unphysical region
    Iph, I0 = solve_iph_i0(Rs, Rsh, Voc, Isc, Vt)

    I_mpp = current_at_voltage(Vmpp, Iph, I0, Rs, Rsh, Vt, I_guess=Impp)
    if np.isnan(I_mpp):
        return [1e6, 1e6]
    P_mpp = Vmpp * I_mpp

    I_plus = current_at_voltage(Vmpp + dV, Iph, I0, Rs, Rsh, Vt, I_guess=I_mpp)
    I_minus = current_at_voltage(Vmpp - dV, Iph, I0, Rs, Rsh, Vt, I_guess=I_mpp)
    if np.isnan(I_plus) or np.isnan(I_minus):
        return [1e6, 1e6]
    P_plus = (Vmpp + dV) * I_plus
    P_minus = (Vmpp - dV) * I_minus
    dPdV = (P_plus - P_minus) / (2 * dV)

    r1 = P_mpp - Vmpp * Impp
    r2 = dPdV
    return [r1, r2]


def extract_parameters(panel=PANEL, T_kelvin=T_STC, Rs0=0.3, Rsh0=300.0, verbose=True):
    Voc, Isc, Vmpp, Impp = panel["Voc"], panel["Isc"], panel["Vmpp"], panel["Impp"]
    Vt = thermal_voltage(T_kelvin, Ns=panel["Ns"], n=panel["n"])

    sol, info, ier, msg = fsolve(
        _residuals, x0=[Rs0, Rsh0], args=(Voc, Isc, Vmpp, Impp, Vt), full_output=True
    )
    Rs, Rsh = sol
    Iph, I0 = solve_iph_i0(Rs, Rsh, Voc, Isc, Vt)

    converged = (ier == 1)
    if verbose:
        status = "CONVERGED" if converged else f"DID NOT CONVERGE ({msg})"
        print(f"[parameter_extraction] {status}")
        print(f"  Rs  = {Rs:.5f} ohm")
        print(f"  Rsh = {Rsh:.3f} ohm")
        print(f"  Iph = {Iph:.5f} A")
        print(f"  I0  = {I0:.5e} A")

    return {"Rs": Rs, "Rsh": Rsh, "Iph": Iph, "I0": I0, "Vt": Vt, "converged": converged}


if __name__ == "__main__":
    result = extract_parameters()
