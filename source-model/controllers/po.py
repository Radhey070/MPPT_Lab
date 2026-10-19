"""
controllers/po.py

Ablation stage A: fixed-step, duty-cycle-domain Perturb & Observe.
Standard formulation for boost-converter MPPT (perturbs D directly, not V --
consistent with D0.2's duty-space framing used by every controller in this
project's ablation):

    if P(k) > P(k-1):  D(k+1) = D(k) + direction * step
    else:              direction = -direction; D(k+1) = D(k) + direction * step

Uses the quasi-static coupling in coupling.py -- see that module's docstring
and docs/decision_log.md D0.15 for the explicit modeling-simplification
caveat (converter assumed to reach steady state each perturbation step).
"""

from coupling import operating_point, clip_duty
import numpy as np


class POController:
    def __init__(self, D_init=0.3, step=0.01, noise_sigma=0.0, seed=None):
        self.D = clip_duty(D_init)
        self.step = step
        self.direction = 1
        self.P_prev = None
        self.noise_sigma = noise_sigma  # added at M12 for a fair ablation
        # comparison under noise -- same class of gap already caught and
        # fixed for VSS-P&O at M7 (D0.19); P&O was missed at the time since
        # M4-M6 never needed a noisy P&O run. Fixed here rather than left
        # as another asymmetric comparison.
        self._rng = np.random.default_rng(seed)

    def step_once(self, G, T_kelvin, R_load):
        V, I, P_true, converged = operating_point(self.D, G, T_kelvin, R_load)
        if not converged:
            # do not silently continue on a failed solve
            return self.D, V, I, P_true, converged

        P = P_true + (self._rng.normal(0, self.noise_sigma) if self.noise_sigma > 0 else 0.0)

        if self.P_prev is not None and P <= self.P_prev:
            self.direction *= -1
        # always perturb after measuring, including the first call -- an
        # earlier version only perturbed inside the `if P_prev is not None`
        # block, which meant the first two calls measured the SAME
        # operating point and incorrectly triggered a direction flip on
        # equality. Fixed by always updating D here (caught during M4
        # validation, see docs/decision_log.md).
        self.D = clip_duty(self.D + self.direction * self.step)

        self.P_prev = P
        return self.D, V, I, P_true, converged
