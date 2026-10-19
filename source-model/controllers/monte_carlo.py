"""
controllers/monte_carlo.py

M15: Monte Carlo validation. Two parts:

PART A: N=60 randomized standard-condition scenarios (irradiance profile
with a random step, temperature, load, noise), all 5 controllers, reusing
the generic G_seq/T_seq/R_seq runner functions already built for M13
(dynamic_experiments.py). Reports mean +/- std per controller per metric.

PART B: N=25 randomized partial-shading patterns, Full controller only,
starting from a fixed "generic history" duty each time -- estimates the
EMPIRICAL RATE of the local-peak-trapping failure mode found at M14.

Scenario definitions are stored, not just aggregate statistics, per master
prompt section 12.
"""

import sys
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from coupling import T_STC, R_LOAD_TYPICAL, D_MIN_SIM, D_MAX_SIM, iv_curve, mpp_from_curve
from coupling_shaded import shaded_operating_point
from dynamic_experiments import (
    run_po, run_vss_po, run_rls_vss, run_hold_track, run_full, N as N_STEPS,
)
from full_controller import FullController

MASTER_SEED = 2026
N_SCENARIOS_A = 60
N_SCENARIOS_B = 25

CONTROLLERS = {
    "A: P&O": run_po, "B: VSS-P&O": run_vss_po, "C: RLS-VSS": run_rls_vss,
    "D: HOLD/TRACK": run_hold_track, "E: Full controller": run_full,
}


def generate_scenario_a(rng):
    G0 = rng.uniform(400, 1100)
    G1 = rng.uniform(400, 1100)
    step_at = rng.integers(150, 350)
    T_c = rng.uniform(15, 55)
    R_factor = rng.uniform(0.7, 1.3)
    noise_sigma = rng.uniform(0.0, 1.5)
    return {"G0": G0, "G1": G1, "step_at": int(step_at), "T_c": T_c,
            "R_factor": R_factor, "noise_sigma": noise_sigma}


def build_sequences(scenario):
    G_seq = np.array([scenario["G0"] if k < scenario["step_at"] else scenario["G1"]
                       for k in range(N_STEPS)])
    T_seq = np.full(N_STEPS, scenario["T_c"] + 273.15)
    R_seq = np.full(N_STEPS, R_LOAD_TYPICAL * scenario["R_factor"])
    return G_seq, T_seq, R_seq


_pmpp_cache = {}


def pmpp_true(G, T):
    key = (round(G, 2), round(T, 2))
    if key not in _pmpp_cache:
        _pmpp_cache[key] = mpp_from_curve(*iv_curve(G, T))[2]
    return _pmpp_cache[key]


def part_a():
    rng = np.random.default_rng(MASTER_SEED)
    scenarios = [generate_scenario_a(rng) for _ in range(N_SCENARIOS_A)]

    with open("../results/raw_data/monte_carlo_scenarios_A.json", "w") as f:
        json.dump(scenarios, f, indent=2)

    metrics = {c: {"eta_full": [], "activity": []} for c in CONTROLLERS}
    for i, sc in enumerate(scenarios):
        G_seq, T_seq, R_seq = build_sequences(sc)
        Pmpp_seq = np.array([pmpp_true(G_seq[k], T_seq[k]) for k in range(N_STEPS)])
        for cname, runner in CONTROLLERS.items():
            Ds, Ps, activity, states = runner(G_seq, T_seq, R_seq)
            eta_full = np.mean(Ps / Pmpp_seq)
            metrics[cname]["eta_full"].append(eta_full)
            metrics[cname]["activity"].append(np.mean(activity))
        if (i + 1) % 20 == 0:
            print(f"  Part A: {i+1}/{N_SCENARIOS_A} scenarios done")

    print("\n=== Part A: Monte Carlo, standard conditions (N=%d) ===" % N_SCENARIOS_A)
    summary = {}
    for cname in CONTROLLERS:
        eta_arr = np.array(metrics[cname]["eta_full"])
        act_arr = np.array(metrics[cname]["activity"])
        summary[cname] = {
            "eta_mean": float(np.mean(eta_arr)), "eta_std": float(np.std(eta_arr)),
            "act_mean": float(np.mean(act_arr)), "act_std": float(np.std(act_arr)),
        }
        print(f"{cname:22s} eta = {summary[cname]['eta_mean']:.4f} +- {summary[cname]['eta_std']:.4f}   "
              f"activity = {summary[cname]['act_mean']:.4f} +- {summary[cname]['act_std']:.4f}")

    return metrics, summary, scenarios


def part_b():
    rng = np.random.default_rng(MASTER_SEED + 1)
    scenarios = []
    trapped_count = 0
    D_generic_start = 0.40

    for i in range(N_SCENARIOS_B):
        G_list = [float(rng.uniform(300, 1000)) for _ in range(3)]
        scenarios.append({"G_list": G_list})

        Ds_curve = np.linspace(D_MIN_SIM, D_MAX_SIM, 200)
        Ps_curve = [shaded_operating_point(d, G_list, T_STC, R_LOAD_TYPICAL)[2] for d in Ds_curve]
        Ps_curve = np.array(Ps_curve)
        D_global = Ds_curve[np.argmax(Ps_curve)]
        P_global = Ps_curve.max()

        ctrl = FullController(D_init=D_generic_start, operating_point_fn=shaded_operating_point)
        D_final = D_generic_start
        for k in range(400):
            r = ctrl.step_once(G_list, T_STC, R_LOAD_TYPICAL)
            D_final = r["D"]

        _, _, P_final, ok = shaded_operating_point(D_final, G_list, T_STC, R_LOAD_TYPICAL)
        frac_of_global = P_final / P_global if P_global > 0 else np.nan
        trapped = frac_of_global < 0.95
        if trapped:
            trapped_count += 1
        scenarios[-1].update({"D_global": float(D_global), "P_global": float(P_global),
                               "D_final": float(D_final), "P_final": float(P_final),
                               "frac_of_global": float(frac_of_global), "trapped": bool(trapped)})

    with open("../results/raw_data/monte_carlo_scenarios_B_shading.json", "w") as f:
        json.dump(scenarios, f, indent=2)

    trap_rate = trapped_count / N_SCENARIOS_B
    print(f"\n=== Part B: shading local-trapping rate (N={N_SCENARIOS_B}) ===")
    print(f"Trapped in a local (non-global) peak: {trapped_count}/{N_SCENARIOS_B} "
          f"({100*trap_rate:.1f}%)")
    fracs = [s["frac_of_global"] for s in scenarios]
    print(f"Fraction-of-global-power distribution: mean={np.mean(fracs):.3f}, "
          f"min={np.min(fracs):.3f}, max={np.max(fracs):.3f}")

    return scenarios, trap_rate


def main():
    metrics_a, summary_a, scenarios_a = part_a()
    scenarios_b, trap_rate = part_b()

    results = []

    def check(name, passed, detail=""):
        results.append((name, passed, detail))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}  {detail}")

    check(
        "All 60 Part A scenarios produced finite results for every controller",
        all(np.all(np.isfinite(metrics_a[c]["eta_full"])) for c in CONTROLLERS),
        "",
    )
    check(
        "Mean tracking efficiency exceeds 80% for every controller across randomized conditions",
        all(summary_a[c]["eta_mean"] > 0.80 for c in CONTROLLERS),
        {c: round(summary_a[c]["eta_mean"], 3) for c in CONTROLLERS},
    )
    check(
        "Stages A-C show activity index std of exactly 0 (always 1.0, by construction)",
        all(summary_a[c]["act_std"] < 1e-9 for c in ["A: P&O", "B: VSS-P&O", "C: RLS-VSS"]),
        "",
    )
    check(
        "Part B shading trap rate is a genuine, non-trivial statistic (neither 0% nor 100%)",
        0.0 < trap_rate < 1.0,
        f"trap rate = {100*trap_rate:.1f}%",
    )

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    names = list(CONTROLLERS.keys())
    eta_data = [metrics_a[c]["eta_full"] for c in names]
    axes[0].boxplot(eta_data, labels=[n.split(":")[0] for n in names])
    axes[0].set_ylabel("Tracking efficiency (per scenario)")
    axes[0].set_title(f"Monte Carlo tracking efficiency distribution (N={N_SCENARIOS_A})")
    axes[0].grid(alpha=0.3, axis="y")

    act_data = [metrics_a[c]["activity"] for c in names]
    axes[1].boxplot(act_data, labels=[n.split(":")[0] for n in names])
    axes[1].set_ylabel("Activity index (per scenario)")
    axes[1].set_title(f"Monte Carlo activity index distribution (N={N_SCENARIOS_A})")
    axes[1].grid(alpha=0.3, axis="y")

    fracs = [s["frac_of_global"] for s in scenarios_b]
    axes[2].hist(fracs, bins=15, color="tab:red", alpha=0.7)
    axes[2].axvline(0.95, color="k", ls="--", label="trapped threshold (95%)")
    axes[2].set_xlabel("Final power / true global peak power")
    axes[2].set_ylabel("Count")
    axes[2].set_title(f"Shading: fraction of global peak reached (N={N_SCENARIOS_B})\n"
                       f"trap rate = {100*trap_rate:.1f}%")
    axes[2].legend(fontsize=8); axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("../results/figures/M15_monte_carlo.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        print("STOP: review failing checks before treating M15 results as final.")
        sys.exit(1)
    else:
        print("All M15 validation checks passed.")


if __name__ == "__main__":
    main()
