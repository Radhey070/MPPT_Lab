"""
controllers/rls.py

Duty-space recursive least squares estimator (D0.2, section 2/3 of
docs/boost_converter_derivation.md). Regresses P(k) ~= theta*D(k) + b(k),
theta approx dP/dD. Implemented and validated INDEPENDENTLY of any
controller (master prompt section 18 / M6) before being wired into
RLS-VSS at M7.

Standard RLS with forgetting factor lambda:
  phi(k)   = [D(k), 1]^T
  K(k)     = P(k-1) phi(k) / (lambda + phi(k)^T P(k-1) phi(k))
  theta(k) = theta(k-1) + K(k) * (P_meas(k) - phi(k)^T theta(k-1))
  P(k)     = (P(k-1) - K(k) phi(k)^T P(k-1)) / lambda

Includes optional periodic covariance reset to guard against covariance
windup when the regressor D is not persistently exciting (e.g. held near-
constant for long stretches, such as a future HOLD state) -- a known RLS
failure mode flagged during the M0 architecture design and tested
explicitly in validate_rls.py, not left as a theoretical caveat.
"""

import numpy as np


class RLSEstimator:
    def __init__(self, lam=0.97, delta=1000.0, reset_interval=None):
        self.lam = lam
        self.delta = delta
        self.theta = np.zeros(2)          # [slope, intercept]
        self.P = delta * np.eye(2)          # large initial covariance, standard RLS init
        self.k = 0
        self.reset_interval = reset_interval

    def reset(self):
        self.P = self.delta * np.eye(2)

    def update(self, D, P_meas):
        phi = np.array([D, 1.0])
        Pphi = self.P @ phi
        denom = self.lam + phi @ Pphi
        K = Pphi / denom
        err = P_meas - phi @ self.theta
        self.theta = self.theta + K * err
        self.P = (self.P - np.outer(K, Pphi)) / self.lam
        self.k += 1
        if self.reset_interval is not None and self.k % self.reset_interval == 0:
            self.reset()
        return self.theta[0], err, np.trace(self.P)
