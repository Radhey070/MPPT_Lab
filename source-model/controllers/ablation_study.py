"""
controllers/ablation_study.py

M12: the payoff milestone. Runs all five ablation-stage controllers
(A: P&O, B: VSS-P&O, C: RLS-VSS, D: HOLD/TRACK, E: full controller) under
IDENTICAL conditions (same D_init, G, T, R_load, N) in two scenarios
(clean and noisy), and computes every metric defined in
docs/metrics_definitions.md.
"""

import sys
import numpy as np
import pandas as pd
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
G, T = 1000.0, T_STC
R_LOAD = R_LOAD_TYPICAL
N = 500
NOISE_SIGMA = 1.5
N_SEEDS = 8

_, _, Pmpp_true = mpp_from_curve(*iv_curve(G, T))


def run_po(noise_sigma, seed):
    ctrl = POController(D_init=D_INIT, step=0.01, noise_sigma=noise_sigma, seed=seed)
    Ds, Ps = [], []
    for k in range(N):
        D, V, I, P, converged = ctrl.step_once(G, T, R_LOAD)
        Ds.append(D); Ps.append(P)
    activity = np.ones(N)
    return np.array(Ds), np.array(Ps), activity


def run_vss_po(noise_sigma, seed):
    ctrl = VSSPOController(D_init=D_INIT, step_min=0.0008, step_max=0.02, N_gain=0.00025,
                            noise_sigma=noise_sigma, seed=seed)
    Ds, Ps = [], []
    for k in range(N):
        D, V, I, P, converged, step = ctrl.step_once(G, T, R_LOAD)
        Ds.append(D); Ps.append(P)
    activity = np.ones(N)
    return np.array(Ds), np.array(Ps), activity


def run_rls_vss(noise_sigma, seed):
    ctrl = RLSVSSController(D_init=D_INIT, eta=0.00008, lam=0.60, step_cap=0.02,
                             noise_sigma=noise_sigma, seed=seed)
    Ds, Ps = [], []
    for k in range(N):
        r = ctrl.step_once(G, T, R_LOAD)
        Ds.append(r["D"]); Ps.append(r["P"])
    activity = np.ones(N)
    return np.array(Ds), np.array(Ps), activity


def run_hold_track(noise_sigma, seed):
    ctrl = HoldTrackController(D_init=D_INIT, noise_sigma=noise_sigma, seed=seed)
    Ds, Ps, perturbed = [], [], []
    for k in range(N):
        r = ctrl.step_once(G, T, R_LOAD)
        Ds.append(r["D"]); Ps.append(r["P"]); perturbed.append(r["perturbed"])
    return np.array(Ds), np.array(Ps), np.array(perturbed, dtype=float)


def run_full(noise_sigma, seed):
    ctrl = FullController(D_init=D_INIT, noise_sigma=noise_sigma, seed=seed)
    Ds, Ps, perturbed = [], [], []
    for k in range(N):
        r = ctrl.step_once(G, T, R_LOAD)
        Ds.append(r["D"]); Ps.append(r["P"]); perturbed.append(r["perturbed"])
    return np.array(Ds), np.array(Ps), np.array(perturbed, dtype=float)


CONTROLLERS = {
    "A: P&O": run_po,
    "B: VSS-P&O": run_vss_po,
    "C: RLS-VSS": run_rls_vss,
    "D: HOLD/TRACK": run_hold_track,
    "E: Full controller": run_full,
}


def compute_metrics(Ds, Ps, activity):
    eta_full = np.mean(Ps) / Pmpp_true
    eta_ss = np.mean(Ps[-50:]) / Pmpp_true
    E = np.sum(Ps)
    A = np.mean(activity)
    osc = Ds[-50:].max() - Ds[-50:].min()
    return {"eta_full": eta_full, "eta_ss": eta_ss, "E": E, "activity_index": A, "osc": osc}


def main():
    rows = []
    traces_clean = {}

    print("=== Clean (no noise) ===")
    for name, runner in CONTROLLERS.items():
        Ds, Ps, activity = runner(0.0, seed=0)
        traces_clean[name] = (Ds, Ps)
        m = compute_metrics(Ds, Ps, activity)
        row = {"controller": name, "scenario": "clean"}
        row.update(m)
        rows.append(row)
        print(f"{name:22s} eta_full={m['eta_full']:.4f} eta_ss={m['eta_ss']:.4f} "
              f"E={m['E']:.1f} activity={m['activity_index']:.3f} osc={m['osc']:.5f}")

    print("\n=== Noisy (sigma=1.5 W, averaged over 8 seeds) ===")
    for name, runner in CONTROLLERS.items():
        metrics_over_seeds = []
        for s in range(N_SEEDS):
            Ds, Ps, activity = runner(NOISE_SIGMA, seed=s)
            metrics_over_seeds.append(compute_metrics(Ds, Ps, activity))
        m_mean = {k: float(np.mean([m[k] for m in metrics_over_seeds])) for k in metrics_over_seeds[0]}
        m_std = {k: float(np.std([m[k] for m in metrics_over_seeds])) for k in metrics_over_seeds[0]}
        row = {"controller": name, "scenario": "noisy"}
        row.update(m_mean)
        row.update({f"{k}_std": v for k, v in m_std.items()})
        rows.append(row)
        print(f"{name:22s} eta_full={m_mean['eta_full']:.4f}+-{m_std['eta_full']:.4f} "
              f"activity={m_mean['activity_index']:.3f} osc={m_mean['osc']:.5f}+-{m_std['osc']:.5f}")

    df = pd.DataFrame(rows)
    df.to_csv("../results/tables/ablation_summary.csv", index=False)
    print("\nTable saved to results/tables/ablation_summary.csv")

    results = []

    def check(name, passed, detail=""):
        results.append((name, passed, detail))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}  {detail}")

    df_clean = df[df.scenario == "clean"].set_index("controller")
    check(
        "All controllers reach at least 90% tracking efficiency (clean conditions)",
        (df_clean["eta_full"] > 0.90).all(),
        f"min = {df_clean['eta_full'].min():.4f}",
    )
    check(
        "Activity index strictly decreases from stage C to D (the central claim)",
        df_clean.loc["C: RLS-VSS", "activity_index"] > df_clean.loc["D: HOLD/TRACK", "activity_index"],
        f"C={df_clean.loc['C: RLS-VSS','activity_index']:.3f}, "
        f"D={df_clean.loc['D: HOLD/TRACK','activity_index']:.3f}, "
        f"E={df_clean.loc['E: Full controller','activity_index']:.3f}",
    )
    check(
        "Stages A-C have activity index exactly 1.0 (no HOLD capability, by construction)",
        np.allclose(df_clean.loc[["A: P&O", "B: VSS-P&O", "C: RLS-VSS"], "activity_index"], 1.0),
        "",
    )
    check(
        "Stage D's steady-state efficiency is comparable to stage C's (activity reduction "
        "doesn't come at a meaningful efficiency cost)",
        abs(df_clean.loc["D: HOLD/TRACK", "eta_ss"] - df_clean.loc["C: RLS-VSS", "eta_ss"]) < 0.01,
        f"C eta_ss={df_clean.loc['C: RLS-VSS','eta_ss']:.4f}, "
        f"D eta_ss={df_clean.loc['D: HOLD/TRACK','eta_ss']:.4f}",
    )

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    for name, (Ds, Ps) in traces_clean.items():
        axes[0, 0].plot(Ps, label=name, lw=1)
    axes[0, 0].axhline(Pmpp_true, color="k", ls="--", lw=1, label="true Pmpp")
    axes[0, 0].set_xlabel("iteration"); axes[0, 0].set_ylabel("P (W)")
    axes[0, 0].set_title("Tracked power, all 5 controllers (clean)")
    axes[0, 0].legend(fontsize=7); axes[0, 0].grid(alpha=0.3)

    names = list(CONTROLLERS.keys())
    activity_clean = [df_clean.loc[n, "activity_index"] for n in names]
    axes[0, 1].bar(range(len(names)), activity_clean, color="tab:blue")
    axes[0, 1].set_xticks(range(len(names))); axes[0, 1].set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    axes[0, 1].set_ylabel("Activity index")
    axes[0, 1].set_title("Activity index by controller (clean)")
    axes[0, 1].grid(alpha=0.3, axis="y")

    df_noisy = df[df.scenario == "noisy"].set_index("controller")
    eta_noisy = [df_noisy.loc[n, "eta_full"] for n in names]
    eta_noisy_std = [df_noisy.loc[n, "eta_full_std"] for n in names]
    axes[1, 0].bar(range(len(names)), eta_noisy, yerr=eta_noisy_std, color="tab:orange", capsize=4)
    axes[1, 0].set_xticks(range(len(names))); axes[1, 0].set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    axes[1, 0].set_ylabel("Tracking efficiency (full run)")
    axes[1, 0].set_title(f"Tracking efficiency under noise (sigma={NOISE_SIGMA}W, {N_SEEDS} seeds)")
    axes[1, 0].grid(alpha=0.3, axis="y")

    osc_clean = [df_clean.loc[n, "osc"] for n in names]
    osc_noisy = [df_noisy.loc[n, "osc"] for n in names]
    x = np.arange(len(names))
    width = 0.35
    axes[1, 1].bar(x - width/2, osc_clean, width, label="clean", color="tab:green")
    axes[1, 1].bar(x + width/2, osc_noisy, width, label="noisy", color="tab:red")
    axes[1, 1].set_xticks(x); axes[1, 1].set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    axes[1, 1].set_ylabel("Steady-state duty oscillation")
    axes[1, 1].set_title("Oscillation: clean vs noisy")
    axes[1, 1].legend(fontsize=8); axes[1, 1].grid(alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig("../results/figures/M12_ablation_study.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        print("STOP: review failing checks before treating the ablation results as final.")
        sys.exit(1)
    else:
        print("All M12 sanity checks passed.")

    return df


if __name__ == "__main__":
    main()
