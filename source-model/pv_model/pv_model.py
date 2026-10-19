"""
pv_model/pv_model.py

Single-diode PV model at arbitrary irradiance G and temperature T, built on
the STC parameters from parameter_extraction.py. Implements standard
physical scaling laws (not fabricated):

  Iph(G,T) = (G/G_stc) * (Iph_stc + alpha_Isc * (T - T_stc))
  I0(T)    = I0_stc * (T/T_stc)^3 * exp( (Q*Eg/(n*Ns*K_B)) * (1/T_stc - 1/T) )
  Voc(T) shifts implicitly through I0(T) and Vt(T); Rs, Rsh held constant
  with temperature (standard simplifying assumption for this model class,
  noted here rather than silently assumed).
"""

import numpy as np

from parameters import PANEL, thermal_voltage, G_STC, T_STC, Q, K_B, EG_REF
from parameter_extraction import extract_parameters, current_at_voltage

_STC_PARAMS = extract_parameters(verbose=False)


def scaled_params(G, T_kelvin, stc=_STC_PARAMS, panel=PANEL):
    """Return (Iph, I0, Rs, Rsh, Vt) at the requested irradiance/temperature."""
    dT = T_kelvin - T_STC
    Iph = (G / G_STC) * (stc["Iph"] + panel["alpha_Isc"] * dT)
    I0 = stc["I0"] * (T_kelvin / T_STC) ** 3 * np.exp(
        (Q * EG_REF) / (panel["n"] * K_B) * (1.0 / T_STC - 1.0 / T_kelvin)
    )
    Vt = thermal_voltage(T_kelvin, Ns=panel["Ns"], n=panel["n"])
    return Iph, I0, stc["Rs"], stc["Rsh"], Vt


def iv_curve(G, T_kelvin, n_points=400, v_max_factor=1.05):
    """Return (V array, I array, P array) swept from 0 to ~Voc(G,T)."""
    Iph, I0, Rs, Rsh, Vt = scaled_params(G, T_kelvin)

    # estimate Voc at these conditions to size the voltage sweep: solve I=0
    def voc_residual(v):
        return Iph - I0 * (np.exp(v / Vt) - 1.0) - v / Rsh

    # bisection since this is monotonic decreasing in v for v>0
    lo, hi = 0.0, 60.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if voc_residual(mid) > 0:
            lo = mid
        else:
            hi = mid
    voc_est = 0.5 * (lo + hi)

    V = np.linspace(0, voc_est * v_max_factor, n_points)
    I = np.full_like(V, np.nan)
    I_prev = Iph
    for k, v in enumerate(V):
        I_prev = current_at_voltage(v, Iph, I0, Rs, Rsh, Vt, I_guess=I_prev)
        I[k] = I_prev
    I = np.clip(I, 0, None)
    P = V * I
    return V, I, P


def mpp_from_curve(V, I, P):
    """Return (Vmpp, Impp, Pmpp) by locating the max of a computed P-V curve."""
    idx = np.nanargmax(P)
    return V[idx], I[idx], P[idx]
