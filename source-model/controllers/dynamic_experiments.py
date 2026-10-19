"""
controllers/dynamic_experiments.py

M13: E02 (irradiance step), E03 (rapid multi-step irradiance), E04
(temperature step), E15 (load step) -- all 5 controllers, identical
profiles per experiment. Tracking efficiency is computed against the
TIME-VARYING true Pmpp (recomputed at each distinct (G,T) via pv_model,
not a single fixed reference -- required whenever conditions change
within a run, per docs/metrics_definitions.md's instantaneous-efficiency
generalization).
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from coupling import T_STC, R_LOAD_TYPICAL, iv_curve, mpp_from_curve
from po import POController
from vss_po import VSSPOController
from rls_vss import RLSVSSController
from hold_track import HoldTrackController
from full_controller import FullController

D_INIT = 0.20
N = 500
_pmpp_cache = {}


def pmpp_true(G, T):
    key = (round(G, 3), round(T, 3))
    if key not in _pmpp_cache:
        _pmpp_cache[key] = mpp_from_curve(*iv_curve(G, T))[2]
    return _pmpp_cache[key]


def run_po(G_seq, T_seq, R_seq):
    ctrl = POController(D_init=D_INIT, step=0.01)
    Ds, Ps = [], []
    for k in range(N):
        D, V, I, P, converged = ctrl.step_once(G_seq[k], T_seq[k], R_seq[k])
        Ds.append(D); Ps.append(P)
    return np.array(Ds), np.array(Ps), np.ones(N), None


def run_vss_po(G_seq, T_seq, R_seq):
    ctrl = VSSPOController(D_init=D_INIT, step_min=0.0008, step_max=0.02, N_gain=0.00025)
    Ds, Ps = [], []
    for k in range(N):
        D, V, I, P, converged, step = ctrl.step_once(G_seq[k], T_seq[k], R_seq[k])
        Ds.append(D); Ps.append(P)
    return np.array(Ds), np.array(Ps), np.ones(N), None


def run_rls_vss(G_seq, T_seq, R_seq):
    ctrl = RLSVSSController(D_init=D_INIT, eta=0.00008, lam=0.60, step_cap=0.02)
    Ds, Ps = [], []
    for k in range(N):
        r = ctrl.step_once(G_seq[k], T_seq[k], R_seq[k])
        Ds.append(r["D"]); Ps.append(r["P"])
    return np.array(Ds), np.array(Ps), np.ones(N), None


def run_hold_track(G_seq, T_seq, R_seq):
    ctrl = HoldTrackController(D_init=D_INIT)
    Ds, Ps, perturbed, states = [], [], [], []
    for k in range(N):
        r = ctrl.step_once(G_seq[k], T_seq[k], R_seq[k])
        Ds.append(r["D"]); Ps.append(r["P"]); perturbed.append(r["perturbed"]); states.append(r["state"])
    return np.array(Ds), np.array(Ps), np.array(perturbed, dtype=float), states


def run_full(G_seq, T_seq, R_seq):
    ctrl = FullController(D_init=D_INIT)
    Ds, Ps, perturbed, states = [], [], [], []
    for k in range(N):
        r = ctrl.step_once(G_seq[k], T_seq[k], R_seq[k])
        Ds.append(r["D"]); Ps.append(r["P"]); perturbed.append(r["perturbed"]); states.append(r["state"])
    return np.array(Ds), np.array(Ps), np.array(perturbed, dtype=float), states


CONTROLLERS = {
    "A: P&O": run_po, "B: VSS-P&O": run_vss_po, "C: RLS-VSS": run_rls_vss,
    "D: HOLD/TRACK": run_hold_track, "E: Full controller": run_full,
}


def eval_scenario(name, G_seq, T_seq, R_seq, step_indices=None):
    print(f"\n=== {name} ===")
    Pmpp_seq = np.array([pmpp_true(G_seq[k], T_seq[k]) for k in range(N)])
    scenario_results = {}
    for cname, runner in CONTROLLERS.items():
        Ds, Ps, activity, states = runner(G_seq, T_seq, R_seq)
        eta_instant = Ps / Pmpp_seq
        eta_full = np.mean(eta_instant)
        act_idx = np.mean(activity)
        recov = []
        if step_indices:
            for si in step_indices:
                post = eta_instant[si:]
                above = np.where(post > 0.99)[0]
                rec_k = None
                for i in range(len(above) - 4):
                    if above[i + 4] - above[i] == 4:
                        rec_k = above[i]
                        break
                recov.append(rec_k if rec_k is not None else -1)
        scenario_results[cname] = {"Ds": Ds, "Ps": Ps, "eta_instant": eta_instant,
                                     "eta_full": eta_full, "activity": act_idx,
                                     "recovery": recov, "states": states}
        print(f"{cname:22s} eta_full={eta_full:.4f} activity={act_idx:.3f} "
              f"recovery_iters={recov}")
    return scenario_results, Pmpp_seq


def main():
    results_all = {}
    checks = []

    def check(name, passed, detail=""):
        checks.append((name, passed, detail))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}  {detail}")

    G02 = np.array([1000.0 if k < 250 else 700.0 for k in range(N)])
    T02 = np.full(N, T_STC)
    R02 = np.full(N, R_LOAD_TYPICAL)
    res02, Pmpp02 = eval_scenario("E02: irradiance step (1000->700)", G02, T02, R02, step_indices=[250])
    results_all["E02"] = res02

    segs = [1000, 500, 800, 300, 900]
    G03 = np.array([segs[min(k // 100, len(segs) - 1)] for k in range(N)], dtype=float)
    T03 = np.full(N, T_STC)
    R03 = np.full(N, R_LOAD_TYPICAL)
    step_idx_03 = [100, 200, 300, 400]
    res03, Pmpp03 = eval_scenario("E03: rapid multi-step irradiance", G03, T03, R03, step_indices=step_idx_03)
    results_all["E03"] = res03

    G04 = np.full(N, 1000.0)
    T04 = np.array([T_STC if k < 250 else T_STC + 20.0 for k in range(N)])
    R04 = np.full(N, R_LOAD_TYPICAL)
    res04, Pmpp04 = eval_scenario("E04: temperature step (25C->45C)", G04, T04, R04, step_indices=[250])
    results_all["E04"] = res04

    G15 = np.full(N, 1000.0)
    T15 = np.full(N, T_STC)
    R15 = np.array([R_LOAD_TYPICAL if k < 250 else R_LOAD_TYPICAL * 0.7 for k in range(N)])
    res15, Pmpp15 = eval_scenario("E15: load step (R_load x0.7)", G15, T15, R15, step_indices=[250])
    results_all["E15"] = res15

    check(
        "E02: all controllers reach >90% overall tracking efficiency despite the step",
        all(res02[c]["eta_full"] > 0.90 for c in CONTROLLERS),
        {c: round(res02[c]["eta_full"], 3) for c in CONTROLLERS},
    )
    check(
        "E02: HOLD/TRACK and Full controller both recover after the step (no permanent stall)",
        res02["D: HOLD/TRACK"]["recovery"][0] != -1 and res02["E: Full controller"]["recovery"][0] != -1,
        f"D recovery={res02['D: HOLD/TRACK']['recovery']}, E recovery={res02['E: Full controller']['recovery']}",
    )
    check(
        "E03: all controllers maintain >80% overall efficiency under rapid multi-step irradiance",
        all(res03[c]["eta_full"] > 0.80 for c in CONTROLLERS),
        {c: round(res03[c]["eta_full"], 3) for c in CONTROLLERS},
    )
    check(
        "E03: HOLD/TRACK's activity index does not collapse to 1.0 even under rapid changes",
        res03["D: HOLD/TRACK"]["activity"] < 1.0,
        f"activity = {res03['D: HOLD/TRACK']['activity']:.3f}",
    )
    check(
        "E04: all controllers reach >90% overall tracking efficiency across the temperature step",
        all(res04[c]["eta_full"] > 0.90 for c in CONTROLLERS),
        {c: round(res04[c]["eta_full"], 3) for c in CONTROLLERS},
    )
    check(
        "E15: all controllers reach >90% overall tracking efficiency across the load step",
        all(res15[c]["eta_full"] > 0.90 for c in CONTROLLERS),
        {c: round(res15[c]["eta_full"], 3) for c in CONTROLLERS},
    )

    scenarios = [("E02", G02, res02, [250]), ("E03", G03, res03, step_idx_03),
                 ("E04", G04, res04, [250]), ("E15", G15, res15, [250])]
    fig, axes = plt.subplots(4, 1, figsize=(11, 16))
    for ax, (label, Gseq, res, steps) in zip(axes, scenarios):
        for cname in CONTROLLERS:
            ax.plot(res[cname]["eta_instant"], label=cname, lw=1)
        for s in steps:
            ax.axvline(s, color="r", ls="--", lw=0.8)
        ax.set_ylim(0, 1.1)
        ax.set_xlabel("iteration"); ax.set_ylabel("instantaneous eta")
        ax.set_title(label)
        ax.legend(fontsize=7, loc="lower right"); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("../results/figures/M13_dynamic_experiments.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in checks if not p)
    print(f"\n{len(checks)-n_fail}/{len(checks)} checks passed.")
    if n_fail > 0:
        print("STOP: review failing checks before treating M13 results as final.")
        sys.exit(1)
    else:
        print("All M13 validation checks passed.")

    return results_all


if __name__ == "__main__":
    main()
