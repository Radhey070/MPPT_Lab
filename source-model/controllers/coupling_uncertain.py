"""
controllers/coupling_uncertain.py

M16, Part A: same quasi-static coupling as coupling.py, but with PV
single-diode parameters (Rs, Rsh, I0, Iph) perturbable by explicit
multipliers -- simulates the real panel deviating from our modeling
assumptions by +/-5/10/20%, while every controller remains UNAWARE of
this (they only ever see measured P, exactly as in reality). Tests
whether the closed-loop controllers still find the ACTUAL (perturbed)
panel's true MPP despite the model mismatch.
"""

import numpy as np
from scipy.optimize import brentq

from coupling import _pv_model, _pv_extraction, _pv_parameters, r_in_effective, clip_duty

_BASE_STC = _pv_extraction.extract_parameters(verbose=False)
current_at_voltage = _pv_extraction.current_at_voltage
PANEL = _pv_parameters.PANEL
thermal_voltage = _pv_parameters.thermal_voltage
G_STC = _pv_parameters.G_STC
T_STC = _pv_parameters.T_STC
Q = _pv_parameters.Q
K_B = _pv_parameters.K_B
EG_REF = _pv_parameters.EG_REF


def scaled_params_uncertain(G, T_kelvin, rs_mult=1.0, rsh_mult=1.0,
                              i0_mult=1.0, iph_mult=1.0):
    dT = T_kelvin - T_STC
    Iph = iph_mult * (G / G_STC) * (_BASE_STC["Iph"] + PANEL["alpha_Isc"] * dT)
    I0 = i0_mult * _BASE_STC["I0"] * (T_kelvin / T_STC) ** 3 * np.exp(
        (Q * EG_REF) / (PANEL["n"] * K_B) * (1.0 / T_STC - 1.0 / T_kelvin)
    )
    Rs = rs_mult * _BASE_STC["Rs"]
    Rsh = rsh_mult * _BASE_STC["Rsh"]
    Vt = thermal_voltage(T_kelvin, Ns=PANEL["Ns"], n=PANEL["n"])
    return Iph, I0, Rs, Rsh, Vt


def operating_point_uncertain(D, G, T_kelvin, R_load, rs_mult=1.0, rsh_mult=1.0,
                                i0_mult=1.0, iph_mult=1.0):
    D = clip_duty(D)
    Iph, I0, Rs, Rsh, Vt = scaled_params_uncertain(G, T_kelvin, rs_mult, rsh_mult,
                                                     i0_mult, iph_mult)
    R_in = r_in_effective(D, R_load)

    def g(V):
        if V <= 1e-9:
            I_pv = Iph
        else:
            I_pv = current_at_voltage(V, Iph, I0, Rs, Rsh, Vt, I_guess=Iph)
            if np.isnan(I_pv):
                return np.nan
        return I_pv - V / R_in

    v_hi = 60.0
    try:
        g_lo, g_hi = g(1e-6), g(v_hi)
        if np.isnan(g_lo) or np.isnan(g_hi) or g_lo * g_hi > 0:
            return np.nan, np.nan, np.nan, False
        V_sol = brentq(g, 1e-6, v_hi, xtol=1e-8, maxiter=200)
    except (ValueError, RuntimeError):
        return np.nan, np.nan, np.nan, False

    I_sol = current_at_voltage(V_sol, Iph, I0, Rs, Rsh, Vt, I_guess=Iph)
    if np.isnan(I_sol):
        return np.nan, np.nan, np.nan, False
    return V_sol, I_sol, V_sol * I_sol, True


def true_mpp_uncertain(G, T_kelvin, rs_mult=1.0, rsh_mult=1.0, i0_mult=1.0,
                         iph_mult=1.0, n_points=300):
    Iph, I0, Rs, Rsh, Vt = scaled_params_uncertain(G, T_kelvin, rs_mult, rsh_mult,
                                                     i0_mult, iph_mult)
    V_arr = np.linspace(0, 30, n_points)
    best_P = -np.inf
    I_prev = Iph
    for V in V_arr:
        I_prev = current_at_voltage(V, Iph, I0, Rs, Rsh, Vt, I_guess=I_prev)
        if np.isnan(I_prev):
            continue
        I_prev = max(I_prev, 0)
        P = V * I_prev
        if P > best_P:
            best_P = P
    return best_P
