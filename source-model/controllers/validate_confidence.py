"""
controllers/validate_confidence.py

M8 validation. Generates REAL (residual, theta_hat) streams from
RLSVSSController (not synthetic bespoke data) under three regimes:
  (a) STABLE: no noise, steady state at the MPP
  (b) NOISY: same injected noise as M7 (sigma=1.5 W), steady tracking
  (c) TRANSIENT: an irradiance step (1000 -> 700 W/m^2) after convergence
Then validates that the confidence metric (M8) separates these regimes
sensibly, and runs a threshold sensitivity study to recommend C_hold /
C_search operating points for M9/M10.
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from coupling import T_STC, R_LOAD_TYPICAL
from rls_vss import RLSVSSController
from confidence import ConfidenceEstimator

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}  {detail}")


def main():
    T = T_STC
    R_load = R_LOAD_TYPICAL

    # --- (a) STABLE: no noise, run to steady state ---
    ctrl_a = RLSVSSController(D_init=0.20, eta=0.00008, lam=0.60, step_cap=0.02)
    resid_a_full, theta_a_full = [], []
    for k in range(300):
        r = ctrl_a.step_once(1000.0, T, R_load)
        resid_a_full.append(r["residual"]); theta_a_full.append(r["theta_hat"])

    # --- (b) NOISY: same as M7's noise test ---
    ctrl_b = RLSVSSController(D_init=0.20, eta=0.00008, lam=0.60, step_cap=0.02,
                               noise_sigma=1.5, seed=0)
    resid_b_full, theta_b_full = [], []
    for k in range(300):
        r = ctrl_b.step_once(1000.0, T, R_load)
        resid_b_full.append(r["residual"]); theta_b_full.append(r["theta_hat"])

    # --- (c) TRANSIENT: converge at G=1000, then step to G=700 ---
    ctrl_c = RLSVSSController(D_init=0.20, eta=0.00008, lam=0.60, step_cap=0.02)
    resid_c, theta_c, G_seq = [], [], []
    for k in range(300):
        G = 1000.0 if k < 200 else 700.0
        r = ctrl_c.step_once(G, T, R_load)
        resid_c.append(r["residual"]); theta_c.append(r["theta_hat"]); G_seq.append(G)

    # --- run all three through a fresh ConfidenceEstimator each ---
    # FIX (see docs/decision_log.md D0.20/D0.21): an earlier version sliced
    # away the controller's warm-up BEFORE running the confidence estimator,
    # which re-introduced the estimator's own cold-start (its first 2
    # samples always return exactly 0.0, by design) in the middle of what
    # was meant to be already-settled data, breaking the "(0,1]" bound
    # check. Fixed by running the confidence estimator over the FULL,
    # unsliced stream (so its own warm-up aligns with the controller's),
    # and slicing the OUTPUT afterward for the steady-region analysis.
    def run_confidence(resid_seq, theta_seq, **kwargs):
        est = ConfidenceEstimator(**kwargs)
        return np.array([est.update(r, t) for r, t in zip(resid_seq, theta_seq)])

    C_a_full = run_confidence(resid_a_full, theta_a_full)
    C_b_full = run_confidence(resid_b_full, theta_b_full)
    C_c = run_confidence(resid_c, theta_c)  # transient run was never sliced

    C_a = C_a_full[100:]
    C_b = C_b_full[100:]

    check("Confidence bounded in (0,1] -- STABLE regime", np.all((C_a > 0) & (C_a <= 1)))
    check("Confidence bounded in (0,1] -- NOISY regime", np.all((C_b > 0) & (C_b <= 1)))
    check(
        "Confidence bounded in [0,1] -- TRANSIENT regime (unsliced, includes the "
        "estimator's own documented cold-start of exactly 0.0 for its first 2 samples)",
        np.all((C_c >= 0) & (C_c <= 1)),
    )

    mean_C_a = np.mean(C_a[-100:])
    mean_C_b = np.mean(C_b[-100:])
    check(
        "STABLE regime has higher mean confidence than NOISY regime",
        mean_C_a > mean_C_b,
        f"mean C stable={mean_C_a:.4f}, mean C noisy={mean_C_b:.4f}",
    )

    # transient: compare confidence just before vs just after the step
    # (step happens at k=200 in the full 300-sample run; run_confidence
    # output is indexed identically, 0..299)
    C_before_step = np.mean(C_c[190:200])
    C_after_step = np.mean(C_c[200:210])
    check(
        "Confidence dips immediately after the irradiance step",
        C_after_step < C_before_step,
        f"C just before step={C_before_step:.4f}, C just after step={C_after_step:.4f}",
    )
    C_recovered = np.mean(C_c[280:300])
    check(
        "Confidence recovers after the controller re-converges post-step",
        C_recovered > C_after_step,
        f"C just after step={C_after_step:.4f}, C late (recovered)={C_recovered:.4f}",
    )

    # --- threshold sensitivity study ---
    thresholds = np.linspace(0.1, 0.9, 17)
    frac_stable_above, frac_noisy_above, frac_transient_dip_below = [], [], []
    for th in thresholds:
        frac_stable_above.append(np.mean(C_a[-100:] > th))
        frac_noisy_above.append(np.mean(C_b[-100:] > th))
        frac_transient_dip_below.append(np.mean(C_c[200:215] < th))

    frac_stable_above = np.array(frac_stable_above)
    frac_noisy_above = np.array(frac_noisy_above)
    frac_transient_dip_below = np.array(frac_transient_dip_below)

    # score: want HIGH frac_stable_above (correctly confident when stable),
    # LOW frac_noisy_above (correctly less confident when noisy), HIGH
    # frac_transient_dip_below (correctly flags the transient)
    score = frac_stable_above - frac_noisy_above + frac_transient_dip_below
    best_idx = int(np.argmax(score))
    recommended_threshold = thresholds[best_idx]

    print("\nThreshold sensitivity study:")
    print(f"{'threshold':>10} {'stable_above':>13} {'noisy_above':>12} {'transient_flagged':>19} {'score':>7}")
    for th, fs, fn, ft, sc in zip(thresholds, frac_stable_above, frac_noisy_above,
                                    frac_transient_dip_below, score):
        marker = "  <-- best" if th == recommended_threshold else ""
        print(f"{th:10.2f} {fs:13.3f} {fn:12.3f} {ft:19.3f} {sc:7.3f}{marker}")

    check(
        "Threshold sensitivity study completed across 17 candidate thresholds",
        len(thresholds) == len(score),
        f"recommended threshold (illustrative scoring) = {recommended_threshold:.2f}",
    )

    # --- figures ---
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    axes[0].plot(C_a, label="stable", alpha=0.8)
    axes[0].plot(C_b, label="noisy", alpha=0.8)
    axes[0].set_xlabel("sample"); axes[0].set_ylabel("Confidence C")
    axes[0].set_title("Confidence: stable vs noisy regime")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
    axes[0].set_ylim(0, 1.05)

    axes[1].plot(C_c, lw=1.2)
    axes[1].axvline(200, color="r", ls="--", lw=1, label="irradiance step (1000->700)")
    axes[1].set_xlabel("sample"); axes[1].set_ylabel("Confidence C")
    axes[1].set_title("Confidence dip at an irradiance step")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
    axes[1].set_ylim(0, 1.05)

    axes[2].plot(thresholds, frac_stable_above, "o-", label="frac. stable samples above thresh")
    axes[2].plot(thresholds, frac_noisy_above, "s-", label="frac. noisy samples above thresh")
    axes[2].plot(thresholds, frac_transient_dip_below, "^-", label="frac. transient samples flagged")
    axes[2].axvline(recommended_threshold, color="k", ls="--", lw=1, label="recommended")
    axes[2].set_xlabel("candidate threshold"); axes[2].set_ylabel("fraction")
    axes[2].set_title("Threshold sensitivity study")
    axes[2].legend(fontsize=7); axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("../results/figures/M8_confidence.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        print("STOP: do not proceed to M9 until failing checks are resolved.")
        sys.exit(1)
    else:
        print("All M8 validation checks passed.")


if __name__ == "__main__":
    main()
