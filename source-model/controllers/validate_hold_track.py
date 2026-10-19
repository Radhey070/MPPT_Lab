"""
controllers/validate_hold_track.py

M9 validation: confidence-gated HOLD/TRACK (ablation stage D). Scenario:
converge at G=1000, hold steady long enough to enter HOLD, step irradiance
to 700 at k=250, verify recovery back to TRACK and re-convergence, verify
low chattering, and measure the activity-index reduction vs always-tracking
RLS-VSS (M7) -- the actual claimed benefit of this stage.
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from coupling import T_STC, R_LOAD_TYPICAL, D_MIN_SIM, D_MAX_SIM
from hold_track import HoldTrackController
from rls_vss import RLSVSSController

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}  {detail}")


def analytic_mpp_duty(R_load, Vmpp, Impp):
    R_target = Vmpp / Impp
    return 1 - np.sqrt(R_target / R_load)


def main():
    T = T_STC
    R_load = R_LOAD_TYPICAL
    D_mpp_1000 = analytic_mpp_duty(R_load, 17.792, 3.0515)  # 0.4069
    N = 500
    step_at = 250

    ctrl = HoldTrackController(D_init=0.20, C_enter=0.70, C_exit=0.40, persistence=5)
    Ds, Ps, states, confs, perturbed = [], [], [], [], []
    for k in range(N):
        G = 1000.0 if k < step_at else 700.0
        r = ctrl.step_once(G, T, R_load)
        if not r["converged"]:
            check(f"operating_point converged at iteration {k}", False)
            sys.exit(1)
        Ds.append(r["D"]); Ps.append(r["P"]); states.append(r["state"])
        confs.append(r["confidence"]); perturbed.append(r["perturbed"])
    Ds, Ps, confs = map(np.array, (Ds, Ps, confs))
    perturbed = np.array(perturbed)

    check(
        "Controller enters HOLD at some point during steady pre-step operation",
        "HOLD" in states[:step_at],
        f"first HOLD entry at iteration "
        f"{states[:step_at].index('HOLD') if 'HOLD' in states[:step_at] else 'never'}",
    )

    hold_idx = [i for i in range(step_at) if states[i] == "HOLD"]
    if hold_idx:
        D_during_hold = Ds[hold_idx]
        check(
            "Duty is exactly frozen while in HOLD (pre-step)",
            np.all(D_during_hold == D_during_hold[0]) if len(set(np.round(D_during_hold, 10))) == 1 else False,
            f"unique duty values during pre-step HOLD: {len(set(np.round(D_during_hold, 8)))}",
        )

    check(
        "Controller returns to TRACK after the irradiance step",
        "TRACK" in states[step_at:step_at + 50],
        "",
    )

    D_tail = Ds[-30:]
    check(
        "Controller re-converges near the new MPP duty after the step (G=700)",
        abs(np.mean(D_tail) - 0.293) < 0.03,
        f"mean D (last 30) = {np.mean(D_tail):.4f}, expected ~0.293 (M8-verified numerically)",
    )

    n_transitions = len(ctrl.transition_log)
    check(
        "Chattering is bounded: total state transitions stay small over 500 iterations",
        n_transitions < 15,
        f"{n_transitions} transitions: {ctrl.transition_log}",
    )

    check(
        "Duty stays within [D_MIN_SIM, D_MAX_SIM] throughout",
        np.all(Ds >= D_MIN_SIM - 1e-9) and np.all(Ds <= D_MAX_SIM + 1e-9),
        f"D range = [{Ds.min():.4f}, {Ds.max():.4f}]",
    )

    # --- activity index comparison vs always-tracking RLS-VSS (M7) ---
    activity_index_holdtrack = np.mean(perturbed)

    ctrl_rls = RLSVSSController(D_init=0.20, eta=0.00008, lam=0.60, step_cap=0.02)
    Ds_rls = []
    for k in range(N):
        G = 1000.0 if k < step_at else 700.0
        r = ctrl_rls.step_once(G, T, R_load)
        Ds_rls.append(r["D"])
    Ds_rls = np.array(Ds_rls)
    # RLS-VSS (stage C) always perturbs, by construction -- activity index = 1.0
    activity_index_rls = 1.0

    check(
        "HOLD/TRACK's activity index is substantially lower than always-tracking RLS-VSS's",
        activity_index_holdtrack < 0.8 * activity_index_rls,
        f"HOLD/TRACK activity index = {activity_index_holdtrack:.3f}, "
        f"RLS-VSS (always tracks) = {activity_index_rls:.3f}",
    )

    D_tail_rls = Ds_rls[-30:]
    check(
        "Both controllers reach comparable final tracking accuracy despite the activity difference",
        abs(np.mean(D_tail) - np.mean(D_tail_rls)) < 0.02,
        f"HOLD/TRACK mean D={np.mean(D_tail):.4f}, RLS-VSS mean D={np.mean(D_tail_rls):.4f}",
    )

    # --- figures ---
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    state_num = np.array([0 if s == "TRACK" else 1 for s in states])
    axes[0].plot(Ds, lw=1, label="HOLD/TRACK duty")
    axes[0].plot(Ds_rls, lw=1, alpha=0.6, label="RLS-VSS duty (always tracking)")
    axes[0].axvline(step_at, color="r", ls="--", lw=1, label="irradiance step")
    axes[0].axhline(D_mpp_1000, color="k", ls=":", lw=1, label="D_mpp @ G=1000")
    axes[0].set_xlabel("iteration"); axes[0].set_ylabel("Duty D")
    axes[0].set_title("Duty: HOLD/TRACK vs always-tracking RLS-VSS")
    axes[0].legend(fontsize=7); axes[0].grid(alpha=0.3)

    ax2 = axes[1]
    ax2.fill_between(range(N), 0, 1, where=(state_num == 1), alpha=0.3, color="tab:green",
                      label="HOLD", step="post")
    ax2.plot(confs, lw=1, color="tab:blue", label="confidence")
    ax2.axhline(ctrl.C_enter, color="g", ls="--", lw=0.8, label="C_enter")
    ax2.axhline(ctrl.C_exit, color="orange", ls="--", lw=0.8, label="C_exit")
    ax2.axvline(step_at, color="r", ls="--", lw=1)
    ax2.set_xlabel("iteration"); ax2.set_ylabel("Confidence / state")
    ax2.set_title("Confidence and HOLD/TRACK state over time")
    ax2.legend(fontsize=7); ax2.grid(alpha=0.3)

    axes[2].plot(np.cumsum(perturbed) / (np.arange(N) + 1), label="HOLD/TRACK cumulative activity index")
    axes[2].axhline(1.0, color="tab:orange", ls="--", label="RLS-VSS (always 1.0)")
    axes[2].axvline(step_at, color="r", ls="--", lw=1)
    axes[2].set_xlabel("iteration"); axes[2].set_ylabel("Cumulative activity index")
    axes[2].set_title("Activity index: HOLD/TRACK vs always-tracking")
    axes[2].legend(fontsize=8); axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("../results/figures/M9_hold_track.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        print("STOP: do not proceed to M10 until failing checks are resolved.")
        sys.exit(1)
    else:
        print("All M9 validation checks passed.")


if __name__ == "__main__":
    main()
