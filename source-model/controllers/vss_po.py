"""
controllers/vss_po.py

Ablation stage B: Variable-Step-Size P&O (finite-difference slope estimate).
Step size scales with |dP/dD| estimated by finite difference between
consecutive measurements -- large far from the MPP (fast approach), small
near it (low steady-state oscillation). This is the "before RLS" reference
for the noise-robustness experiment (E05): stage C (M6-M7) replaces this
finite-difference slope estimate with an RLS estimate and the two are
compared head-to-head under injected noise.

    step(k) = clip(N * |dP/dD|, step_min, step_max)
    direction flips when dP <= 0 (same logic as P&O, ablation stage A)
"""

import numpy as np
from coupling import operating_point, clip_duty


class VSSPOController:
    def __init__(self, D_init=0.2, step_min=0.0008, step_max=0.02, N_gain=0.00025,
                 noise_sigma=0.0, seed=None):
        self.D = clip_duty(D_init)
        self.D_prev = None
        self.P_prev = None
        self.direction = 1
        self.step_min = step_min
        self.step_max = step_max
        self.N = N_gain
        self.noise_sigma = noise_sigma  # injected measurement noise on P, added here
        # (not just in RLS-VSS) so the M7 head-to-head noise-robustness comparison is
        # actually fair -- an earlier draft of validate_rls_vss.py injected noise into
        # RLS-VSS only and left VSS-P&O reading clean P, which would have made the
        # comparison meaningless. Caught and fixed before running, see D0.19.
        self._rng = np.random.default_rng(seed)

    def step_once(self, G, T_kelvin, R_load):
        V, I, P_true, converged = operating_point(self.D, G, T_kelvin, R_load)
        if not converged:
            return self.D, V, I, P_true, converged, 0.0

        P = P_true + (self._rng.normal(0, self.noise_sigma) if self.noise_sigma > 0 else 0.0)

        if self.P_prev is not None and self.D_prev is not None:
            dP = P - self.P_prev
            dD = self.D - self.D_prev
            slope = dP / dD if abs(dD) > 1e-9 else 0.0
            step = float(np.clip(self.N * abs(slope), self.step_min, self.step_max))
            if dP <= 0:
                self.direction *= -1
        else:
            step = self.step_max  # first call: no slope history yet, take a full step

        self.D_prev = self.D
        self.D = clip_duty(self.D + self.direction * step)
        self.P_prev = P
        return self.D, V, I, P_true, converged, step
