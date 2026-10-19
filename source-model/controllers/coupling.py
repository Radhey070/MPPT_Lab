"""
controllers/coupling.py

Quasi-static PV<->boost-converter coupling used by all algorithm-level
controllers (P&O, VSS-P&O, RLS-VSS, confidence-aware). Given a duty cycle D,
irradiance G, temperature T, and load R_load, finds the PV operating point
(V, I, P) as the intersection of:

  - the PV I-V curve (pv_model.py, single-diode model)
  - the load line the converter presents to the PV source, I = V / R_in,eff(D)
    where R_in,eff(D) = (1-D)^2 * R_load (boost_model/averaged_model.py,
    section 5 of docs/boost_converter_derivation.md)

MODELING SIMPLIFICATION, logged explicitly (see docs/decision_log.md D0.15):
this assumes the boost converter reaches its steady-state operating point
INSTANTLY relative to the controller's perturbation period -- i.e. it uses
the converter's algebraic steady-state relation, not its dynamic transient
(M3's averaged_model.py showed settling can take ~150-200ms at this
operating point). This is standard practice for algorithm-level MPPT
comparison (matches how P&O/INC/VSS-P&O are compared in the literature
surveyed at M1) and is valid as long as the controller's perturbation
period is chosen longer than the converter's settling time -- which must be
verified, not assumed, and is exactly why "Experiment 6: converter
transient effect" exists in the experiment registry as a dedicated,
separate study using the FULL dynamic coupling instead.
"""

import sys
import os
import importlib.util
import numpy as np
from scipy.optimize import brentq

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(name, relpath):
    """Load a module under a unique name to avoid collisions between
    pv_model/parameters.py and boost_model/parameters.py (both named
    'parameters' -- a plain sys.path insert caused exactly this bug on
    first attempt, fixed here rather than worked around by renaming files,
    since the per-directory naming is intentional per the repo layout)."""
    path = os.path.join(_THIS_DIR, "..", relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_pv_parameters = _load_module("pv_parameters", "pv_model/parameters.py")
sys.modules["parameters"] = _pv_parameters  # pv_model.py does `from parameters import ...`
_pv_extraction = _load_module("pv_parameter_extraction", "pv_model/parameter_extraction.py")
sys.modules["parameter_extraction"] = _pv_extraction  # pv_model.py imports this name too
_pv_model = _load_module("pv_model_mod", "pv_model/pv_model.py")

_boost_parameters = _load_module("boost_parameters", "boost_model/parameters.py")
sys.modules["parameters"] = _boost_parameters  # now boost's averaged_model.py sees the right one
_boost_averaged = _load_module("boost_averaged_model", "boost_model/averaged_model.py")

scaled_params = _pv_model.scaled_params
iv_curve = _pv_model.iv_curve
mpp_from_curve = _pv_model.mpp_from_curve
T_STC = _pv_parameters.T_STC
current_at_voltage = _pv_extraction.current_at_voltage
r_in_effective = _boost_averaged.r_in_effective
clip_duty = _boost_averaged.clip_duty
R_LOAD_TYPICAL = _boost_parameters.R_LOAD_TYPICAL
D_MIN_SIM = _boost_parameters.D_MIN_SIM
D_MAX_SIM = _boost_parameters.D_MAX_SIM


def operating_point(D, G, T_kelvin, R_load):
    """Solve for the PV operating point (V, I, P) given duty D, irradiance G,
    temperature T, and load R_load, under the quasi-static assumption above.
    Returns (V, I, P, converged: bool)."""
    D = clip_duty(D)
    Iph, I0, Rs, Rsh, Vt = scaled_params(G, T_kelvin)
    R_in = r_in_effective(D, R_load)

    def g(V):
        if V <= 1e-9:
            I_pv = Iph  # short-circuit-ish limit
        else:
            I_pv = current_at_voltage(V, Iph, I0, Rs, Rsh, Vt, I_guess=Iph)
            if np.isnan(I_pv):
                return np.nan
        I_line = V / R_in
        return I_pv - I_line

    # bracket search: V=0 -> g>0 (I_pv>0=I_line), find where g crosses 0
    v_hi = 60.0  # generous upper bound, above any realistic Voc for this panel class
    try:
        g_lo = g(1e-6)
        g_hi = g(v_hi)
        if np.isnan(g_lo) or np.isnan(g_hi) or g_lo * g_hi > 0:
            return np.nan, np.nan, np.nan, False
        V_sol = brentq(g, 1e-6, v_hi, xtol=1e-8, maxiter=200)
    except (ValueError, RuntimeError):
        return np.nan, np.nan, np.nan, False

    I_sol = current_at_voltage(V_sol, Iph, I0, Rs, Rsh, Vt, I_guess=Iph)
    if np.isnan(I_sol):
        return np.nan, np.nan, np.nan, False
    return V_sol, I_sol, V_sol * I_sol, True
