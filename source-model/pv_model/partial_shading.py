"""
pv_model/partial_shading.py

M14: simplified partial-shading model. Splits the panel into N_SUB series
substrings (bypass-diode topology), each independently irradiated. This is
the standard simplified technique for generating illustrative multi-peak
P-V curves without full cell-level modeling.

Substring parameters are derived from the SAME extraction method as the
full panel (parameter_extraction.py), using scaled datasheet points:
series-connected cells share the same current, so Isc/Impp are UNCHANGED
per substring; only Voc/Vmpp (and Ns) scale by the substring's fraction of
total cells.

For a given total string current I, each substring's voltage V_i(I) is
solved from its own implicit single-diode equation. If a substring cannot
support that current, its bypass diode is assumed to conduct, clamping
V_i = BYPASS_DROP -- this clamping is what creates the multiple local
maxima in the aggregate P-V curve as substrings drop out one by one.
"""

import sys
import os
import numpy as np
from scipy.optimize import brentq

sys.path.insert(0, os.path.dirname(__file__))
from parameters import PANEL, thermal_voltage, G_STC, T_STC, Q, K_B, EG_REF
from parameter_extraction import extract_parameters

N_SUB = 3
BYPASS_DROP = -0.7

# FIX (see docs/decision_log.md D0.26): an earlier version independently
# re-ran extract_parameters() on scaled per-substring datasheet points
# (Voc/3, Vmpp/3, same Isc/Impp). This introduces a NEW nonlinear fit bias
# per substring -- summing 3 independently-refit substrings under uniform
# irradiance reproduced only ~89% of the original panel's Pmpp, not a close
# match. Root cause: I0 and Rs/Rsh from an independent re-fit to a smaller
# Voc/Vmpp don't combine additively back to the original module's values.
# Correct approach: derive substring parameters by ANALYTIC SCALING of the
# full panel's single extraction (Iph, I0 unchanged -- same photocurrent
# and lumped saturation current per cell technology, shared by series
# connection; Rs, Rsh scale proportionally with cell count; only Ns changes
# for the thermal-voltage calculation).
_FULL_STC = extract_parameters(panel=PANEL, verbose=False)
_NS_SUB = max(1, round(PANEL["Ns"] / N_SUB))


def substring_voltage(I, sub_idx, G_i, T_kelvin=T_STC):
    dT = T_kelvin - T_STC
    Iph = (G_i / G_STC) * (_FULL_STC["Iph"] + PANEL["alpha_Isc"] * dT)
    I0 = _FULL_STC["I0"] * (T_kelvin / T_STC) ** 3 * np.exp(
        (Q * EG_REF) / (PANEL["n"] * K_B) * (1.0 / T_STC - 1.0 / T_kelvin)
    )
    Rs = _FULL_STC["Rs"] / N_SUB
    Rsh = _FULL_STC["Rsh"] / N_SUB
    Vt = thermal_voltage(T_kelvin, Ns=_NS_SUB, n=PANEL["n"])
    Voc_sub_approx = PANEL["Voc"] / N_SUB

    if I >= Iph * 1.02:
        return BYPASS_DROP

    def f(V):
        return Iph - I0 * (np.exp((V + I * Rs) / Vt) - 1.0) - (V + I * Rs) / Rsh - I

    lo, hi = -5.0, Voc_sub_approx * 1.5
    try:
        f_lo, f_hi = f(lo), f(hi)
        if f_lo * f_hi > 0:
            return BYPASS_DROP
        V = brentq(f, lo, hi, xtol=1e-9, maxiter=200)
    except (ValueError, RuntimeError):
        return BYPASS_DROP

    return V if V > BYPASS_DROP else BYPASS_DROP


def shaded_iv_curve(G_list, T_kelvin=T_STC, n_points=400):
    assert len(G_list) == N_SUB
    I_max = max((G / G_STC) * PANEL["Isc"] for G in G_list) * 1.05
    I_arr = np.linspace(1e-6, I_max, n_points)
    V_arr = np.zeros_like(I_arr)
    for k, I in enumerate(I_arr):
        V_arr[k] = sum(substring_voltage(I, i, G_list[i], T_kelvin) for i in range(N_SUB))
    V_arr = np.clip(V_arr, 0, None)
    P_arr = V_arr * I_arr
    return I_arr, V_arr, P_arr


def count_local_maxima(P_arr):
    d = np.diff(P_arr)
    signs = np.sign(d)
    signs = signs[signs != 0]
    return int(np.sum((signs[:-1] > 0) & (signs[1:] < 0)))
