"""
controllers/rls_vss.py

Ablation stage C: RLS-VSS. Replaces VSS-P&O's finite-difference slope
estimate (stage B) with the validated duty-space RLS estimator (M6) to
drive a gradient-scaled duty update. Always tracking -- no HOLD/SEARCH yet
(those are ablation stages D/E, M9/M10).

SIGN VERIFICATION (master prompt section 5 -- do not blindly assume the
naive law is correct): the naive form D(k+1) = D(k) - eta*theta_hat(k) was
checked numerically before implementation (see docs/decision_log.md D0.19)
by probing dP/dD on both sides of the known MPP duty. Result: dP/dD > 0 for
D < D_mpp (need to INCREASE D) and dP/dD < 0 for D > D_mpp (need to
DECREASE D). The naive minus-sign law would therefore move AWAY from the
MPP -- it is wrong for this problem's sign convention. The correct update
is gradient ASCENT:

    D(k+1) = D(k) + eta * theta_hat(k)

theta_hat comes from the RLS estimator regressing P ~ theta*D + b (M6),
which is noise-robust by construction, unlike VSS-P&O's raw finite
difference.

LAMBDA RECALIBRATION FOR CLOSED-LOOP USE (see docs/decision_log.md D0.19):
M6's lambda=0.995 was tuned for noise rejection against a STATIC true
slope -- exactly the scope caveat flagged at the time. In THIS closed loop,
the regression target (local dP/dD) itself moves every step as the
controller changes D, and lambda=0.995's ~200-sample memory made RLS fit a
slowly-updating GLOBAL model across the whole visited duty range instead of
the LOCAL slope, causing severe overshoot (observed: converging near
D=0.48-0.54 instead of the true D_mpp=0.4069, with theta_hat still ~85 at
the true MPP because it was lagging by dozens of samples). Recalibrated by
sweeping lambda x eta empirically against the coupled PV+boost model
(not guessed): lambda=0.60, eta=0.00008 gives near-zero final duty error
and zero residual dither, versus lambda=0.995's severe overshoot. This is a
DIFFERENT operating point on the same speed/noise-rejection trade-off
characterized at M6 -- lower lambda trades away some of that noise
rejection for the tracking responsiveness this closed loop actually needs.

COVARIANCE WINDUP IN CLOSED-LOOP OPERATION (found at M8, see D0.20):
reset_interval defaults to 50, not None. Discovered while validating the
confidence metric at M8: after an irradiance step, the controller can enter
an exact 2-value duty limit cycle (e.g. bouncing between D=0.3894 and
D=0.4094 every sample). With only two distinct D values visited repeatedly,
the duty-space regressor loses persistent excitation and the RLS covariance
blows up exactly as characterized in M6's synthetic windup test -- observed
theta_hat reaching physically absurd values (-4529 W/duty). This is the
SAME mechanism M6 validated a fix for, now triggered for real by the
controller's own closed-loop dynamics rather than an artificial held-input
test. Enabling periodic reset (interval=50) breaks the limit cycle and the
controller correctly re-converges (verified against a numerical MPP search
at G=700 W/m^2: converges to D=0.293, matching the true MPP duty exactly).
"""

import numpy as np
from coupling import operating_point, clip_duty
from rls import RLSEstimator


class RLSVSSController:
    def __init__(self, D_init=0.2, eta=0.00008, lam=0.60, delta=1000.0,
                 reset_interval=50, step_cap=0.02, noise_sigma=0.0, seed=None):
        self.D = clip_duty(D_init)
        self.eta = eta
        self.step_cap = step_cap  # safety clamp on |D_new - D|, guards against
        # a bad theta_hat during the RLS's own initial transient
        self.est = RLSEstimator(lam=lam, delta=delta, reset_interval=reset_interval)
        self.noise_sigma = noise_sigma  # optional injected measurement noise on P,
        # used by the head-to-head noise-robustness comparison against VSS-P&O
        self._rng = np.random.default_rng(seed)

    def step_once(self, G, T_kelvin, R_load):
        V, I, P, converged = operating_point(self.D, G, T_kelvin, R_load)
        if not converged:
            return {"D": self.D, "V": V, "I": I, "P": P, "converged": converged,
                     "theta_hat": 0.0, "residual": 0.0, "cov_trace": np.nan}

        P_meas = P + (self._rng.normal(0, self.noise_sigma) if self.noise_sigma > 0 else 0.0)
        theta_hat, resid, cov_trace = self.est.update(self.D, P_meas)

        raw_step = self.eta * theta_hat
        step = float(np.clip(raw_step, -self.step_cap, self.step_cap))
        self.D = clip_duty(self.D + step)

        # Returns a dict, not a positional tuple (refactored at M8 -- see
        # docs/decision_log.md D0.20). RLSEstimator.update already exposes
        # residual and covariance trace; M7's step_once was silently
        # discarding both, which M8's confidence metric needs. A growing
        # positional tuple would keep breaking every caller each time a new
        # field was needed (as it already did once here); a dict is stable
        # against future additions (M9 HOLD state, M10 SEARCH, etc.).
        return {"D": self.D, "V": V, "I": I, "P": P, "converged": converged,
                 "theta_hat": theta_hat, "residual": resid, "cov_trace": cov_trace}
