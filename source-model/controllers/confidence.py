"""
controllers/confidence.py

M8: deterministic, bounded, interpretable confidence metric (D0.5 -- no ML
classifier by default). Combines RLS residual magnitude and slope
(theta_hat) variance over a short sliding window into a single score
C in (0, 1]:

    C = 1 / (1 + w_r * resid_norm + w_t * theta_norm)

where resid_norm and theta_norm are RMS residual / theta-std, each
normalized by a fixed reference scale so C is dimensionless and bounded.
High C means the local linear model has been fitting well AND the slope
estimate has been stable -- i.e. it is safe to reduce perturbation
(the eventual HOLD state, M9). Low C means either the model doesn't fit
(residual spike -- e.g. an irradiance step) or the slope estimate is noisy
(as characterized in M7, D0.19) -- i.e. keep tracking or consider SEARCH.

Deliberately NOT machine-learned: two weights and two reference scales,
computable from a small circular buffer, trivially portable to STM32/ESP32.
"""

import numpy as np
from collections import deque


class ConfidenceEstimator:
    def __init__(self, window=10, resid_ref=1.0, theta_ref=80.0, w_resid=1.0, w_theta=1.0):
        self.window = window
        self.resid_ref = resid_ref   # normalization scale for RMS residual (power units, W)
        self.theta_ref = theta_ref     # normalization scale for slope std (W/duty units)
        self.w_resid = w_resid
        self.w_theta = w_theta
        self.resid_buf = deque(maxlen=window)
        self.theta_buf = deque(maxlen=window)

    def update(self, residual, theta_hat):
        self.resid_buf.append(residual)
        self.theta_buf.append(theta_hat)

        if len(self.resid_buf) < 2:
            return 0.0  # not enough history yet -- explicitly low confidence, not a guess

        resid_rms = float(np.sqrt(np.mean(np.square(self.resid_buf))))
        theta_std = float(np.std(self.theta_buf))

        resid_norm = resid_rms / self.resid_ref
        theta_norm = theta_std / self.theta_ref

        C = 1.0 / (1.0 + self.w_resid * resid_norm + self.w_theta * theta_norm)
        return C
