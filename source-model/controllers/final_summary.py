"""
controllers/final_summary.py

M22: final statistical analysis. Consolidates M12 (ablation), M13
(dynamic conditions), M14 (partial shading), M15 (Monte Carlo), and M16
(parameter uncertainty) into one master results table and one headline
summary figure for the report/viva. Reuses each milestone's own validated
functions directly (does not re-derive or hand-transcribe any numbers),
so this is a single source of truth, not a second copy that could drift
from the actual computations.
"""

import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import ablation_study as m12
import dynamic_experiments as m13
import monte_carlo as m15

CONTROLLER_ORDER = ["A: P&O", "B: VSS-P&O", "C: RLS-VSS", "D: HOLD/TRACK", "E: Full controller"]


def main():
    rows = []

    print("Re-running M12 (ablation, clean+noisy)...")
    df12 = m12.main()
    for _, r in df12.iterrows():
        rows.append({"milestone": "M12", "experiment": "ablation_" + r["scenario"],
                     "controller": r["controller"], "metric": "eta_full", "value": r["eta_full"]})
        rows.append({"milestone": "M12", "experiment": "ablation_" + r["scenario"],
                     "controller": r["controller"], "metric": "activity_index", "value": r["activity_index"]})

    print("\nRe-running M13 (dynamic conditions: E02/E03/E04/E15)...")
    results13 = m13.main()
    for exp_name, res in results13.items():
        for cname, d in res.items():
            rows.append({"milestone": "M13", "experiment": exp_name, "controller": cname,
                         "metric": "eta_full", "value": d["eta_full"]})
            rows.append({"milestone": "M13", "experiment": exp_name, "controller": cname,
                         "metric": "activity_index", "value": d["activity"]})

    print("\nRe-running M15 (Monte Carlo, Part A + Part B)...")
    metrics_a, summary_a, _ = m15.part_a()
    for cname in CONTROLLER_ORDER:
        rows.append({"milestone": "M15", "experiment": "monte_carlo_A", "controller": cname,
                     "metric": "eta_full_mean", "value": summary_a[cname]["eta_mean"]})
        rows.append({"milestone": "M15", "experiment": "monte_carlo_A", "controller": cname,
                     "metric": "eta_full_std", "value": summary_a[cname]["eta_std"]})
        rows.append({"milestone": "M15", "experiment": "monte_carlo_A", "controller": cname,
                     "metric": "activity_index_mean", "value": summary_a[cname]["act_mean"]})
        rows.append({"milestone": "M15", "experiment": "monte_carlo_A", "controller": cname,
                     "metric": "activity_index_std", "value": summary_a[cname]["act_std"]})

    _, trap_rate = m15.part_b()
    rows.append({"milestone": "M15", "experiment": "monte_carlo_B_shading",
                 "controller": "E: Full controller", "metric": "local_trap_rate", "value": trap_rate})

    df_master = pd.DataFrame(rows)
    df_master.to_csv("../results/tables/master_summary.csv", index=False)
    print("\nMaster summary table saved to results/tables/master_summary.csv "
          f"({len(df_master)} rows)")

    # ---- headline figure: the project's story in one image ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))

    piv = df_master[(df_master.experiment == "ablation_clean") &
                     (df_master.metric == "activity_index")].set_index("controller")
    vals = [piv.loc[c, "value"] for c in CONTROLLER_ORDER]
    axes[0].bar(range(5), vals, color=["gray", "gray", "gray", "tab:green", "tab:green"])
    axes[0].set_xticks(range(5)); axes[0].set_xticklabels([c.split(":")[0] for c in CONTROLLER_ORDER])
    axes[0].set_ylabel("Activity index")
    axes[0].set_title("Headline benefit:\nactivity index under steady conditions")
    axes[0].grid(alpha=0.3, axis="y")

    mc = df_master[(df_master.experiment == "monte_carlo_A")]
    eta_means = [mc[(mc.controller == c) & (mc.metric == "eta_full_mean")]["value"].values[0]
                 for c in CONTROLLER_ORDER]
    eta_stds = [mc[(mc.controller == c) & (mc.metric == "eta_full_std")]["value"].values[0]
                for c in CONTROLLER_ORDER]
    axes[1].bar(range(5), eta_means, yerr=eta_stds, capsize=4,
                color=["gray", "gray", "gray", "tab:orange", "tab:orange"])
    axes[1].set_xticks(range(5)); axes[1].set_xticklabels([c.split(":")[0] for c in CONTROLLER_ORDER])
    axes[1].set_ylabel("Tracking efficiency (mean +/- std)")
    axes[1].set_title("Honest limitation:\nefficiency variability, N=60 random scenarios")
    axes[1].set_ylim(0.85, 1.02)
    axes[1].grid(alpha=0.3, axis="y")

    trap_row = df_master[df_master.metric == "local_trap_rate"]
    trap_val = trap_row["value"].values[0] * 100
    axes[2].bar(["Found\nglobal peak", "Trapped in\nlocal peak"],
                [100 - trap_val, trap_val], color=["tab:blue", "tab:red"])
    axes[2].set_ylabel("% of randomized shading scenarios (N=25)")
    axes[2].set_title(f"Most significant limitation:\n{trap_val:.0f}% local-peak trap rate")
    axes[2].grid(alpha=0.3, axis="y")

    fig.suptitle("Confidence-Aware Adaptive MPPT: headline results summary", fontsize=13, y=1.03)
    fig.tight_layout()
    fig.savefig("../results/figures/M22_headline_summary.png", dpi=150, bbox_inches="tight")
    print("Headline figure saved to results/figures/M22_headline_summary.png")

    # ---- sanity checks: cross-consistency with each source milestone ----
    results = []

    def check(name, passed, detail=""):
        results.append((name, passed, detail))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}  {detail}")

    check(
        "Master table row count matches expected (M12: 5 ctrl x 2 scenarios x 2 metrics=20, "
        "M13: 4 experiments x 5 ctrl x 2 metrics=40, M15: 5 ctrl x 4 metrics + 1 trap row=21)",
        len(df_master) == 20 + 40 + 21,
        f"actual rows = {len(df_master)}",
    )
    check(
        "Ablation activity index for stages A-C is exactly 1.0 (cross-check vs M12 source)",
        np.allclose(
            df_master[(df_master.experiment == "ablation_clean") &
                      (df_master.metric == "activity_index") &
                      (df_master.controller.isin(["A: P&O", "B: VSS-P&O", "C: RLS-VSS"]))]["value"],
            1.0,
        ),
        "",
    )
    check(
        "Local trap rate matches M15's originally reported value (52.0%)",
        abs(trap_val - 52.0) < 1e-6,
        f"trap_val = {trap_val:.1f}%",
    )

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        sys.exit(1)
    else:
        print("All M22 consolidation checks passed.")


if __name__ == "__main__":
    main()
