"""
boost_model/switched_model.py

Raw switching-cycle simulator (docs/boost_converter_derivation.md section 1)
-- integrates the ACTUAL two-subinterval equations cycle by cycle, so its
output shows real switching ripple that the averaged model (section 2)
cannot. Used only as a cross-check against averaged_model.py, per the
master prompt's requirement to clearly distinguish the averaged model from
real switching hardware.
"""

import numpy as np

from parameters import L, C_OUT, F_SW


def simulate_switched(Vin, D, R_load, n_cycles, steps_per_cycle=200, x0=(0.0, 0.0)):
    """Fixed-step RK4 integration of the switched (non-averaged) equations
    over n_cycles switching periods."""
    T_sw = 1.0 / F_SW
    dt = T_sw / steps_per_cycle
    t_on_steps = int(round(D * steps_per_cycle))

    iL, Vout = x0
    t = 0.0
    ts, iLs, Vouts = [t], [iL], [Vout]

    def rhs(state, switch_on):
        iL_, Vout_ = state
        if switch_on:
            diL = Vin / L
            dVout = -Vout_ / (R_load * C_OUT)
        else:
            diL = (Vin - Vout_) / L
            dVout = (iL_ - Vout_ / R_load) / C_OUT
        return np.array([diL, dVout])

    state = np.array([iL, Vout])
    for cycle in range(n_cycles):
        for step in range(steps_per_cycle):
            switch_on = step < t_on_steps
            k1 = rhs(state, switch_on)
            k2 = rhs(state + 0.5 * dt * k1, switch_on)
            k3 = rhs(state + 0.5 * dt * k2, switch_on)
            k4 = rhs(state + dt * k3, switch_on)
            state = state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
            state[0] = max(state[0], 0.0)  # iL cannot go negative in CCM/boundary
            t += dt
            ts.append(t)
            iLs.append(state[0])
            Vouts.append(state[1])

    return np.array(ts), np.array(iLs), np.array(Vouts)
