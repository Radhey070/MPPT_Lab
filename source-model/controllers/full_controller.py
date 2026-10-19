"""
controllers/full_controller.py

Ablation stage E, the final proposed controller: HOLD/TRACK (stage D, M9)
plus a bounded, confidence-triggered coarse SEARCH (D0.3 -- "bounded coarse
GMPP localization", never described as guaranteed global optimization;
D0.4 -- event-triggered, never periodic).

SEARCH TRIGGER GATE (learned from M9's premature-HOLD lesson, D0.22 --
a state transition firing during an unrepresentative phase is a real risk
class, not a one-off bug): SEARCH is only allowed to trigger from TRACK
AFTER the controller has reached HOLD at least once (self._ever_held).
Without this gate, low confidence during the normal startup climb (before
RLS has converged) could spuriously trigger a SEARCH sweep before the
controller has ever found a real peak to lose in the first place --
SEARCH's purpose is recovering from a LOST/degraded condition, not
substituting for normal initial convergence.

SEARCH mechanics: a fixed, deterministic sweep of N_search_steps duty
values spanning [D_MIN_SIM, D_MAX_SIM], each measured directly via
operating_point (bypassing the gradient controller). Terminates in exactly
N_search_steps steps (bounded, provable termination -- not iterative/
stochastic). Seeds D at the best sampled point, resets the RLS estimator
(the pre-search local model is stale after a large duty jump), and hands
back to TRACK.
"""

import numpy as np
from coupling import operating_point as _default_operating_point, clip_duty, D_MIN_SIM, D_MAX_SIM
from rls import RLSEstimator
from confidence import ConfidenceEstimator


class FullController:
    def __init__(self, D_init=0.2, eta=0.00008, lam=0.60, delta=1000.0,
                 reset_interval=50, step_cap=0.02, noise_sigma=0.0, seed=None,
                 C_enter=0.70, C_exit=0.40, persistence=5, theta_hold_gate=5.0,
                 C_search=0.15, persistence_search=60, N_search_steps=15,
                 conf_window=10, conf_resid_ref=1.0, conf_theta_ref=80.0,
                 operating_point_fn=None):
        self.D = clip_duty(D_init)
        self.eta = eta
        self.step_cap = step_cap
        self.est = RLSEstimator(lam=lam, delta=delta, reset_interval=reset_interval)
        self.conf = ConfidenceEstimator(window=conf_window, resid_ref=conf_resid_ref,
                                          theta_ref=conf_theta_ref)
        self.noise_sigma = noise_sigma
        self._rng = np.random.default_rng(seed)
        # pluggable coupling function -- defaults to the standard single-diode
        # coupling; M14 injects the shaded multi-peak coupling instead, so
        # this same controller class can be tested against both PV models
        # without duplicating any control logic
        self.operating_point = operating_point_fn or _default_operating_point

        self.state = "TRACK"
        self.C_enter = C_enter
        self.C_exit = C_exit
        self.persistence = persistence
        self.theta_hold_gate = theta_hold_gate
        self.C_search = C_search
        self.persistence_search = persistence_search
        self._high_count = 0
        self._low_count = 0
        self._search_count = 0
        self._ever_held = False  # SEARCH gate -- see module docstring

        self.N_search_steps = N_search_steps
        self._search_candidates = np.linspace(D_MIN_SIM, D_MAX_SIM, N_search_steps)
        self._search_idx = 0
        self._search_best_P = -np.inf
        self._search_best_D = self.D

        self.transition_log = []
        self._k = 0

    def step_once(self, G, T_kelvin, R_load):
        if self.state == "SEARCH":
            return self._search_step(G, T_kelvin, R_load)

        V, I, P, converged = self.operating_point(self.D, G, T_kelvin, R_load)
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
                self._ever_held = True
                self._high_count = 0
                self._low_count = 0
                self._search_count = 0

            if self._ever_held:
                if C < self.C_search:
                    self._search_count += 1
                else:
                    self._search_count = 0
                if self._search_count >= self.persistence_search:
                    self.transition_log.append((self._k, "TRACK", "SEARCH"))
                    self.state = "SEARCH"
                    self._search_idx = 0
                    self._search_best_P = -np.inf
                    self._search_count = 0

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

    def _search_step(self, G, T_kelvin, R_load):
        D_probe = float(self._search_candidates[self._search_idx])
        V, I, P, converged = self.operating_point(D_probe, G, T_kelvin, R_load)
        self.D = D_probe
        if converged and P > self._search_best_P:
            self._search_best_P = P
            self._search_best_D = D_probe

        self._search_idx += 1
        if self._search_idx >= self.N_search_steps:
            # sweep complete -- seed D at best candidate, reset the stale
            # RLS model, hand back to TRACK
            self.D = clip_duty(self._search_best_D)
            self.est = RLSEstimator(lam=self.est.lam, delta=self.est.delta,
                                      reset_interval=self.est.reset_interval)
            self.conf = ConfidenceEstimator(window=self.conf.window,
                                              resid_ref=self.conf.resid_ref,
                                              theta_ref=self.conf.theta_ref)
            self.transition_log.append((self._k, "SEARCH", "TRACK"))
            self.state = "TRACK"

        self._k += 1
        return {"D": self.D, "V": V, "I": I, "P": P, "converged": converged,
                 "theta_hat": 0.0, "confidence": 0.0, "state": self.state,
                 "perturbed": True}
