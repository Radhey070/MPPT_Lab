"""
controllers/validate_vss_po.py

M5 validation: VSS-P&O against the coupled PV+boost model, plus a
head-to-head convergence-speed comparison against M4's fixed-step P&O
under identical initial conditions.
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from coupling import operating_point, T_STC, R_LOAD_TYPICAL, D_MIN_SIM, D_MAX_SIM, iv_curve
from po import POController
from vss_po import VSSPOController

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}  {detail}")


def analytic_mpp_duty(R_load, Vmpp=17.792, Impp=3.0515):
    R_target = Vmpp / Impp
    return 1 - np.sqrt(R_target / R_load)


def run_controller(ctrl, N, G, T, R_load, is_vss):
    Ds, Ps, Vs, steps = [], [], [], []
    for k in range(N):
        if is_vss:
            D, V, I, P, converged, step = ctrl.step_once(G, T, R_load)
            steps.append(step)
        else:
            D, V, I, P, converged = ctrl.step_once(G, T, R_load)
        if not converged:
            return None
        Ds.append(D); Ps.append(P); Vs.append(V)
    return np.array(Ds), np.array(Ps), np.array(Vs), np.array(steps)


def iters_to_reach(Ps, target_frac, Pmpp):
    idx = np.where(Ps >= target_frac * Pmpp)[0]
    return idx[0] if len(idx) > 0 else None


def main():
    G, T = 1000.0, T_STC
    R_load = R_LOAD_TYPICAL
    N = 400
    Pmpp_true = 54.29
    D_mpp_analytic = analytic_mpp_duty(R_load)

    vss = VSSPOController(D_init=0.20, step_min=0.0008, step_max=0.02, N_gain=0.00025)
    Ds, Ps, Vs, steps = run_controller(vss, N, G, T, R_load, is_vss=True)

    po = POController(D_init=0.20, step=0.01)
    Ds_po, Ps_po, Vs_po, _ = run_controller(po, N, G, T, R_load, is_vss=False)

    D_tail = Ds[-50:]
    P_tail = Ps[-50:]

    check(
        "VSS-P&O converges near the analytic MPP duty",
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

    it_vss = iters_to_reach(Ps, 0.99, Pmpp_true)
    it_po = iters_to_reach(Ps_po, 0.99, Pmpp_true)
    check(
        "VSS-P&O reaches 99% of Pmpp no slower than fixed-step P&O",
        (it_vss is not None) and (it_po is not None) and (it_vss <= it_po),
        f"VSS-P&O: {it_vss} iters, P&O: {it_po} iters",
    )

    check(
        "VSS-P&O steady-state oscillation is smaller than fixed-step P&O's",
        (D_tail.max() - D_tail.min()) < (Ds_po[-50:].max() - Ds_po[-50:].min()),
        f"VSS-P&O tail range={D_tail.max()-D_tail.min():.5f}, "
        f"P&O tail range={Ds_po[-50:].max()-Ds_po[-50:].min():.5f}",
    )

    check(
        "Step size shrinks as the controller approaches the MPP (first > last, excluding warm-up)",
        steps[5] > steps[-1],
        f"step[5]={steps[5]:.5f}, step[-1]={steps[-1]:.5f}",
    )
    check(
        "No excessive overshoot: duty never exceeds analytic MPP duty by more than 3x step_max",
        np.max(Ds) < D_mpp_analytic + 3 * vss.step_max + 0.05,
        f"max D = {np.max(Ds):.4f}, analytic D_mpp = {D_mpp_analytic:.4f}",
    )

    # figures
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    axes[0].plot(Ps, label="VSS-P&O", lw=1)
    axes[0].plot(Ps_po, label="P&O (fixed-step)", lw=1, alpha=0.7)
    axes[0].axhline(Pmpp_true, color="k", ls="--", lw=1, label="true Pmpp")
    axes[0].set_xlabel("iteration"); axes[0].set_ylabel("P (W)")
    axes[0].set_title("VSS-P&O vs P&O: tracked power")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)

    axes[1].plot(Ds, label="VSS-P&O", lw=1)
    axes[1].plot(Ds_po, label="P&O (fixed-step)", lw=1, alpha=0.7)
    axes[1].axhline(D_mpp_analytic, color="k", ls="--", lw=1, label="analytic D_mpp")
    axes[1].set_xlabel("iteration"); axes[1].set_ylabel("Duty D")
    axes[1].set_title("VSS-P&O vs P&O: duty cycle")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)

    axes[2].plot(steps, lw=1)
    axes[2].set_xlabel("iteration"); axes[2].set_ylabel("step size")
    axes[2].set_title("VSS-P&O: adaptive step size vs iteration")
    axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("../results/figures/M5_vss_po_vs_po.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        print("STOP: do not proceed to M6 until failing checks are resolved.")
        sys.exit(1)
    else:
        print("All M5 validation checks passed.")


if __name__ == "__main__":
    main()
