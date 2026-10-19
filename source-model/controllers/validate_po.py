"""
controllers/validate_po.py

M4 validation: fixed-step P&O against the coupled PV+boost model.
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from coupling import operating_point, T_STC, R_LOAD_TYPICAL, D_MIN_SIM, D_MAX_SIM
from po import POController

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}  {detail}")


def analytic_mpp_duty(R_load, Vmpp=17.792, Impp=3.0515):
    """From the M3/M4 cross-check already done manually: R_in,eff(D)=(1-D)^2*R
    should equal Vmpp/Impp at the true MPP. Solve D from that."""
    R_target = Vmpp / Impp
    D = 1 - np.sqrt(R_target / R_load)
    return D


def main():
    G, T = 1000.0, T_STC
    R_load = R_LOAD_TYPICAL
    N = 400

    ctrl = POController(D_init=0.20, step=0.01)
    Ds, Vs, Is, Ps = [], [], [], []
    for k in range(N):
        D, V, I, P, converged = ctrl.step_once(G, T, R_load)
        if not converged:
            check(f"operating_point converged at iteration {k}", False)
            sys.exit(1)
        Ds.append(D); Vs.append(V); Is.append(I); Ps.append(P)

    Ds, Vs, Is, Ps = map(np.array, (Ds, Vs, Is, Ps))

    D_mpp_analytic = analytic_mpp_duty(R_load)
    D_tail = Ds[-50:]
    P_tail = Ps[-50:]

    check(
        "P&O converges near the analytic MPP duty",
        abs(np.mean(D_tail) - D_mpp_analytic) < 0.03,
        f"mean D (last 50) = {np.mean(D_tail):.4f}, analytic D_mpp = {D_mpp_analytic:.4f}",
    )
    check(
        "Tracked power reaches within 1% of true Pmpp (54.29 W)",
        np.max(P_tail) > 0.99 * 54.29,
        f"max P (last 50 iters) = {np.max(P_tail):.4f} W",
    )
    check(
        "Duty stays within [D_MIN_SIM, D_MAX_SIM] at all times",
        np.all(Ds >= D_MIN_SIM - 1e-9) and np.all(Ds <= D_MAX_SIM + 1e-9),
        f"D range observed = [{Ds.min():.4f}, {Ds.max():.4f}]",
    )
    check(
        "Steady-state oscillation amplitude is bounded by ~2x step size (classic P&O behavior)",
        (D_tail.max() - D_tail.min()) <= 2.5 * ctrl.step,
        f"tail D range = {D_tail.max()-D_tail.min():.4f}, step = {ctrl.step}",
    )
    check(
        "V_pv(D) is monotonically decreasing near the MPP (sanity check on coupling)",
        operating_point(0.30, G, T, R_load)[0] > operating_point(0.50, G, T, R_load)[0],
        "",
    )

    # figures
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    axes[0].plot(Ps, lw=1)
    axes[0].axhline(54.29, color="k", ls="--", lw=1, label="true Pmpp")
    axes[0].set_xlabel("iteration"); axes[0].set_ylabel("P (W)")
    axes[0].set_title("P&O: tracked power vs iteration")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)

    axes[1].plot(Ds, lw=1)
    axes[1].axhline(D_mpp_analytic, color="k", ls="--", lw=1, label="analytic D_mpp")
    axes[1].set_xlabel("iteration"); axes[1].set_ylabel("Duty D")
    axes[1].set_title("P&O: duty cycle vs iteration")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)

    # P-V trajectory overlay on the true P-V curve
    from coupling import iv_curve as pv_iv_curve  # reuse coupling's isolated loader,
    # avoids the parameters/parameters name collision a fresh sys.path import hit here
    Vc, Ic, Pc = pv_iv_curve(G, T)
    axes[2].plot(Vc, Pc, color="gray", lw=1, label="true P-V curve")
    axes[2].plot(Vs, Ps, "o", ms=2, alpha=0.5, label="P&O trajectory")
    axes[2].set_xlabel("V_pv (V)"); axes[2].set_ylabel("P (W)")
    axes[2].set_title("Operating-point trajectory on P-V curve")
    axes[2].legend(fontsize=8); axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("../results/figures/M4_po_baseline.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        print("STOP: do not proceed to M5 until failing checks are resolved.")
        sys.exit(1)
    else:
        print("All M4 validation checks passed.")


if __name__ == "__main__":
    main()
