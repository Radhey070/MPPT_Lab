"""
controllers/hold_track.py

Ablation stage D: RLS-VSS (stage C) + confidence-gated HOLD/TRACK state
machine (master prompt section 7-8). No SEARCH yet -- that's stage E, M10.

State machine, with hysteresis AND a persistence count on both directions
(master prompt section 8 -- do not allow chattering on raw threshold
crossings):

  TRACK -> HOLD: confidence > C_enter for `persistence` consecutive samples
  HOLD -> TRACK: confidence < C_exit for `persistence` consecutive samples
  (C_exit < C_enter: hysteresis gap, not a single shared threshold)

In HOLD, duty is NOT perturbed (goal: eliminate unnecessary perturbation,
master prompt section 7). The RLS estimator CONTINUES to be updated with
the (constant D, measured P) pair while holding -- this is intentional: a
change in P at fixed D can only be caused by a change in the underlying PV
operating conditions (irradiance/temperature), so the residual is still a
valid confidence signal even without active perturbation. Whether this is
numerically safe (constant D is a rank-1 regressor -- see
docs/decision_log.md D0.20's windup finding) is checked explicitly during
M9 validation, not assumed; reset_interval provides the same safety net
validated at M6/M8.

SECOND HOLD-ENTRY GATE, found necessary during M9 validation (see
docs/decision_log.md D0.22): M8's confidence metric measures whether the
LOCAL LINEAR MODEL has been fitting consistently (low residual, low
theta_hat variance) -- NOT whether the controller is actually near the
MPP. These coincide AT the true peak (slope near zero AND stable), but
also coincide FALSELY during a smooth, consistent climb up the P-D curve
far from the peak (low residual because RLS tracks a smoothly-changing
slope well; low variance because consecutive theta_hat values are close
together even though their magnitude is large). Observed directly:
confidence reached 0.94 by iteration 20 while theta_hat was still ~88
(nowhere near zero), causing the controller to freeze at D=0.288 --- a 15%
power loss relative to the true MPP. Fixed by requiring BOTH confidence
AND |theta_hat| below a threshold (theta_hold_gate) before entering HOLD --
confidence alone is necessary but not sufficient.
"""

import numpy as np
from coupling import operating_point, clip_duty
from rls import RLSEstimator
from confidence import ConfidenceEstimator


class HoldTrackController:
    def __init__(self, D_init=0.2, eta=0.00008, lam=0.60, delta=1000.0,
                 reset_interval=50, step_cap=0.02, noise_sigma=0.0, seed=None,
                 C_enter=0.70, C_exit=0.40, persistence=5, theta_hold_gate=5.0,
                 conf_window=10, conf_resid_ref=1.0, conf_theta_ref=80.0):
        self.D = clip_duty(D_init)
        self.eta = eta
        self.step_cap = step_cap
        self.est = RLSEstimator(lam=lam, delta=delta, reset_interval=reset_interval)
        self.conf = ConfidenceEstimator(window=conf_window, resid_ref=conf_resid_ref,
                                          theta_ref=conf_theta_ref)
        self.noise_sigma = noise_sigma
        self._rng = np.random.default_rng(seed)

        self.state = "TRACK"
        self.C_enter = C_enter
        self.C_exit = C_exit
        self.persistence = persistence
        self.theta_hold_gate = theta_hold_gate  # |theta_hat| must be below this
        # too, not just confidence -- see module docstring, this is the fix for
        # the premature-HOLD bug found during M9 validation (D0.22)
        self._high_count = 0
        self._low_count = 0
        self.transition_log = []  # (iteration, from_state, to_state)
        self._k = 0

    def step_once(self, G, T_kelvin, R_load):
        V, I, P, converged = operating_point(self.D, G, T_kelvin, R_load)
        if not converged:
            return {"D": self.D, "V": V, "I": I, "P": P, "converged": converged,
                     "theta_hat": 0.0, "confidence": 0.0, "state": self.state,
                     "perturbed": False}

        P_meas = P + (self._rng.normal(0, self.noise_sigma) if self.noise_sigma > 0 else 0.0)
        theta_hat, resid, cov_trace = self.est.update(self.D, P_meas)
        C = self.conf.update(resid, theta_hat)

        perturbed = False
        if self.state == "TRACK":
            raw_step = self.eta * theta_hat
            step = float(np.clip(raw_step, -self.step_cap, self.step_cap))
            self.D = clip_duty(self.D + step)
            perturbed = True

            if C > self.C_enter and abs(theta_hat) < self.theta_hold_gate:
                self._high_count += 1
            else:
                self._high_count = 0
            if self._high_count >= self.persistence:
                self.transition_log.append((self._k, "TRACK", "HOLD"))
                self.state = "HOLD"
                self._high_count = 0
                self._low_count = 0

        elif self.state == "HOLD":
            if C < self.C_exit:
                self._low_count += 1
            else:
                self._low_count = 0
            if self._low_count >= self.persistence:
                self.transition_log.append((self._k, "HOLD", "TRACK"))
                self.state = "TRACK"
                self._high_count = 0
                self._low_count = 0

        self._k += 1
        return {"D": self.D, "V": V, "I": I, "P": P, "converged": converged,
                 "theta_hat": theta_hat, "confidence": C, "state": self.state,
                 "perturbed": perturbed}
