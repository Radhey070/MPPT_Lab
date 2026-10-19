"""
boost_model/averaged_model.py

State-space averaged CCM boost model, derived in
docs/boost_converter_derivation.md sections 1-6. Lossless by default
(R_L_ESR / R_C_ESR are None unless explicitly supplied -- never silently
defaulted to a guessed nonzero value, per parameters.py).
"""

import numpy as np
from scipy.integrate import solve_ivp

from parameters import L, C_OUT, F_SW, D_MIN_SIM, D_MAX_SIM


def clip_duty(D):
    """Enforce simulation-only software duty limits. D=1 is a singularity
    in Vout=Vin/(1-D) and must never be reached."""
    return float(np.clip(D, D_MIN_SIM, D_MAX_SIM))


def averaged_rhs(t, x, Vin, D, R_load, R_L_ESR=None):
    """dx/dt for the averaged model. x = [iL, Vout].
    Derivation: docs/boost_converter_derivation.md section 2 (lossless) /
    section 6 (loss-inclusive form, only used if R_L_ESR is not None)."""
    iL, Vout = x
    D = clip_duty(D)
    if R_L_ESR is None:
        diL_dt = (Vin - (1 - D) * Vout) / L
    else:
        diL_dt = (Vin - (1 - D) * Vout - iL * R_L_ESR) / L
    dVout_dt = ((1 - D) * iL - Vout / R_load) / C_OUT
    return [diL_dt, dVout_dt]


def steady_state_prediction(Vin, D, R_load):
    """Ideal lossless steady-state prediction, section 3."""
    D = clip_duty(D)
    Vout_ss = Vin / (1 - D)
    IL_ss = Vout_ss / ((1 - D) * R_load)
    return Vout_ss, IL_ss


def simulate_step_response(Vin, D, R_load, t_end, x0=(0.0, 0.0), R_L_ESR=None, n_eval=2000):
    """Integrate the averaged ODE from x0 under constant Vin, D, R_load."""
    sol = solve_ivp(
        averaged_rhs, [0, t_end], list(x0), args=(Vin, D, R_load, R_L_ESR),
        t_eval=np.linspace(0, t_end, n_eval), method="RK45", rtol=1e-9, atol=1e-12,
    )
    return sol.t, sol.y[0], sol.y[1]  # t, iL(t), Vout(t)


def r_in_effective(D, R_load):
    """Section 5: effective input resistance presented to the PV source."""
    D = clip_duty(D)
    return (1 - D) ** 2 * R_load


def r_crit_ccm_boundary(D, R_load_unused, f_sw=F_SW):
    """Section 4: critical load resistance, CCM boundary.
    R_load < R_crit(D)  =>  CCM assumption holds."""
    D = clip_duty(D)
    return 2 * L * f_sw / (D * (1 - D))


def lc_corner_frequency():
    """f_0 = 1/(2*pi*sqrt(L*C_out)) -- averaging-validity check, section 7 item 2."""
    return 1.0 / (2 * np.pi * np.sqrt(L * C_OUT))


def settling_time_estimate(D, R_load, tol=1e-3):
    """Analytic settling-time estimate for the LOSSLESS averaged model,
    treated as LTI for fixed D. wn = sqrt((1-D)^2/(L*C_out)),
    2*zeta*wn = 1/(R_load*C_out) (R_load is the only damping source when
    R_L_ESR is unset -- this system is typically very underdamped).
    t_settle = ln(1/tol) / (zeta*wn). See docs/boost_converter_derivation.md
    finding: with no R_L_ESR, zeta is small and settling is slow -- this is
    a property of the lossless model, not a simulation bug."""
    D = clip_duty(D)
    zeta_wn = 0.5 / (R_load * C_OUT)
    return np.log(1.0 / tol) / zeta_wn
