"""
controllers/coupling_shaded.py

M14: PV-converter coupling using the shaded multi-peak PV model
(pv_model/partial_shading.py). Given a duty D, solves for the string
current I such that the shaded array's V(I) matches the load line
I = V/R_in,eff(D) -- same quasi-static principle as coupling.py (D0.15),
parameterized by I instead of V since the shaded model is naturally
I-parameterized.
"""

import sys
import os
import importlib.util
import numpy as np
from scipy.optimize import brentq

from coupling import r_in_effective, clip_duty  # this already sets up isolated
# pv_model/boost_model imports correctly (D0.16) -- reuse that infrastructure
# rather than a fresh plain sys.path insert, which hit the exact same
# module-name collision bug here on the first attempt.

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(name, relpath):
    path = os.path.join(_THIS_DIR, "..", relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ensure "parameters" and "parameter_extraction" point at the PV versions
# before loading partial_shading.py, which needs both
sys.modules["parameters"] = sys.modules["pv_parameters"]
sys.modules["parameter_extraction"] = sys.modules["pv_parameter_extraction"]
_partial_shading = _load_module("partial_shading_mod", "pv_model/partial_shading.py")

N_SUB = _partial_shading.N_SUB
substring_voltage = _partial_shading.substring_voltage


def shaded_operating_point(D, G_list, T_kelvin, R_load):
    D = clip_duty(D)
    R_in = r_in_effective(D, R_load)

    def g(I):
        V = sum(substring_voltage(I, i, G_list[i], T_kelvin) for i in range(N_SUB))
        V = max(V, 0.0)
        return V - I * R_in

    I_max = max(G / 1000.0 for G in G_list) * 4.0
    try:
        g_lo, g_hi = g(1e-6), g(I_max)
        if g_lo * g_hi > 0:
            return np.nan, np.nan, np.nan, False
        I_sol = brentq(g, 1e-6, I_max, xtol=1e-8, maxiter=200)
    except (ValueError, RuntimeError):
        return np.nan, np.nan, np.nan, False

    V_sol = max(sum(substring_voltage(I_sol, i, G_list[i], T_kelvin) for i in range(N_SUB)), 0.0)
    return V_sol, I_sol, V_sol * I_sol, True
