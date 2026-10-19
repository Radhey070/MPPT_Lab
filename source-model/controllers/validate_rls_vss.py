"""
controllers/validate_rls_vss.py

M7 validation: RLS-VSS convergence/bounds checks (matching stages A/B),
plus the first real test of RLS-VSS's claimed advantage -- a head-to-head
noise-robustness comparison against VSS-P&O under injected measurement
noise on P, using the SAME coupled PV+boost simulation (not the synthetic
tests from M6).
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from coupling import T_STC, R_LOAD_TYPICAL, D_MIN_SIM, D_MAX_SIM
from vss_po import VSSPOController
from rls_vss import RLSVSSController

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}  {detail}")


def analytic_mpp_duty(R_load, Vmpp=17.792, Impp=3.0515):
    R_target = Vmpp / Impp
    return 1 - np.sqrt(R_target / R_load)


def run_rls_vss(ctrl, N, G, T, R_load):
    Ds, Ps, thetas = [], [], []
    for k in range(N):
        r = ctrl.step_once(G, T, R_load)
        if not r["converged"]:
            return None
        Ds.append(r["D"]); Ps.append(r["P"]); thetas.append(r["theta_hat"])
    return np.array(Ds), np.array(Ps), np.array(thetas)


def run_vss_po(ctrl, N, G, T, R_load):
    Ds, Ps = [], []
    for k in range(N):
        D, V, I, P, converged, step = ctrl.step_once(G, T, R_load)
        if not converged:
            return None
        Ds.append(D); Ps.append(P)
    return np.array(Ds), np.array(Ps)


def main():
    G, T = 1000.0, T_STC
    R_load = R_LOAD_TYPICAL
    N = 400
    Pmpp_true = 54.29
    D_mpp_analytic = analytic_mpp_duty(R_load)

    # --- baseline behavior, no noise ---
    rls = RLSVSSController(D_init=0.20, eta=0.00008, lam=0.60, step_cap=0.02)
    Ds, Ps, thetas = run_rls_vss(rls, N, G, T, R_load)

    D_tail = Ds[-50:]
    P_tail = Ps[-50:]

    check(
        "RLS-VSS converges near the analytic MPP duty",
        abs(np.mean(D_tail) - D_mpp_analytic) < 0.03,
        f"mean D (last 50) = {np.mean(D_tail):.4f}, analytic D_mpp = {D_mpp_analytic:.4f}",
    )
    check(
        "Tracked power reaches within 1% of true Pmpp",
        np.max(P_tail) > 0.99 * Pmpp_true,
        f"max P (last 50 iters) = {np.max(P_tail):.4f} W",
    )
    check(
        "Duty stays within [D_MIN_SIM, D_MAX_SIM] at all times",
        np.all(Ds >= D_MIN_SIM - 1e-9) and np.all(Ds <= D_MAX_SIM + 1e-9),
        f"D range observed = [{Ds.min():.4f}, {Ds.max():.4f}]",
    )
    check(
        "Sign check: theta_hat is positive while approaching from below D_mpp (first 5 iters)",
        np.mean(thetas[:5]) > 0,
        f"mean theta_hat (first 5) = {np.mean(thetas[:5]):.4f}",
    )

    # --- head-to-head noise robustness vs VSS-P&O, THE central M7 test ---
    noise_sigma = 1.5  # W, injected measurement noise on P
    n_seeds = 10
    N_noise = 300

    rls_final_errs, vss_final_errs = [], []
    rls_osc, vss_osc = [], []
    for s in range(n_seeds):
        rls_n = RLSVSSController(D_init=0.20, eta=0.00008, lam=0.60, step_cap=0.02,
                                  noise_sigma=noise_sigma, seed=s)
        Ds_r, Ps_r, _ = run_rls_vss(rls_n, N_noise, G, T, R_load)
        rls_final_errs.append(abs(np.mean(Ds_r[-50:]) - D_mpp_analytic))
        rls_osc.append(Ds_r[-50:].max() - Ds_r[-50:].min())

        # same noise_sigma AND same seed as RLS-VSS above, for a fair
        # paired comparison (fixed after catching an unfair-comparison bug
        # before this even ran, see D0.19 -- VSS-P&O now supports noise
        # injection identically to RLS-VSS)
        vss_n = VSSPOController(D_init=0.20, step_min=0.0008, step_max=0.02, N_gain=0.00025,
                                 noise_sigma=noise_sigma, seed=s)
        Ds_v, Ps_v = run_vss_po(vss_n, N_noise, G, T, R_load)
        vss_final_errs.append(abs(np.mean(Ds_v[-50:]) - D_mpp_analytic))
        vss_osc.append(Ds_v[-50:].max() - Ds_v[-50:].min())

    mean_rls_err = np.mean(rls_final_errs)
    mean_vss_err = np.mean(vss_final_errs)
    mean_rls_osc = np.mean(rls_osc)
    mean_vss_osc = np.mean(vss_osc)

    print(f"\nHead-to-head under injected noise (sigma={noise_sigma} W, {n_seeds} seeds):")
    print(f"  RLS-VSS: mean |D_final - D_mpp| = {mean_rls_err:.5f}, mean tail oscillation = {mean_rls_osc:.5f}")
    print(f"  VSS-P&O: mean |D_final - D_mpp| = {mean_vss_err:.5f}, mean tail oscillation = {mean_vss_osc:.5f}")

    check(
        "Under injected noise, RLS-VSS's final duty error stays within a reasonable "
        "absolute bound (0.05) -- NOT required to beat VSS-P&O's accuracy here, see finding below",
        mean_rls_err < 0.05,
        f"RLS-VSS err={mean_rls_err:.5f}, VSS-P&O err={mean_vss_err:.5f} "
        f"(VSS-P&O is more accurate here -- see docs/decision_log.md D0.19 for why, "
        f"and why this motivates the confidence-gated HOLD state at M9)",
    )
    check(
        "Under injected noise, RLS-VSS's steady-state oscillation is smaller than VSS-P&O's "
        "(the actual claimed advantage of this stage)",
        mean_rls_osc < mean_vss_osc,
        f"RLS-VSS osc={mean_rls_osc:.5f}, VSS-P&O osc={mean_vss_osc:.5f}",
    )

    # figures
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    axes[0].plot(Ps, lw=1)
    axes[0].axhline(Pmpp_true, color="k", ls="--", lw=1, label="true Pmpp")
    axes[0].set_xlabel("iteration"); axes[0].set_ylabel("P (W)")
    axes[0].set_title("RLS-VSS: tracked power (no noise)")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)

    axes[1].plot(Ds, lw=1)
    axes[1].axhline(D_mpp_analytic, color="k", ls="--", lw=1, label="analytic D_mpp")
    axes[1].set_xlabel("iteration"); axes[1].set_ylabel("Duty D")
    axes[1].set_title("RLS-VSS: duty cycle (no noise)")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)

    # one representative noisy run of each, side by side
    rls_demo = RLSVSSController(D_init=0.20, eta=0.00008, lam=0.60, step_cap=0.02,
                                 noise_sigma=noise_sigma, seed=0)
    Ds_rls_demo, _, _ = run_rls_vss(rls_demo, N_noise, G, T, R_load)
    vss_demo = VSSPOController(D_init=0.20, step_min=0.0008, step_max=0.02, N_gain=0.00025,
                                noise_sigma=noise_sigma, seed=0)
    Ds_vss_demo, _ = run_vss_po(vss_demo, N_noise, G, T, R_load)
    axes[2].plot(Ds_rls_demo, label="RLS-VSS (noisy P)", lw=1)
    axes[2].plot(Ds_vss_demo, label="VSS-P&O (same noisy P, same seed)", lw=1, alpha=0.7)
    axes[2].axhline(D_mpp_analytic, color="k", ls="--", lw=1, label="analytic D_mpp")
    axes[2].set_xlabel("iteration"); axes[2].set_ylabel("Duty D")
    axes[2].set_title(f"Duty trace under noise (sigma={noise_sigma} W), seed=0")
    axes[2].legend(fontsize=7); axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("../results/figures/M7_rls_vss.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        print("STOP: do not proceed to M8 until failing checks are resolved.")
        sys.exit(1)
    else:
        print("All M7 validation checks passed.")


if __name__ == "__main__":
    main()
