"""
controllers/parameter_uncertainty.py

M16: parameter uncertainty (+/-5/10/20%).

SCOPING NOTE (see docs/decision_log.md D0.28): all controller-level results
(M4-M15) use the quasi-static coupling (D0.15), where R_in,effective(D) =
(1-D)^2 * R_load has NO dependence on L or C. So inductor/capacitor
uncertainty cannot affect any controller comparison result already
produced -- it only matters for M3's boost-converter-level analysis
(settling time, ripple, CCM margin). This milestone therefore splits into:

PART A: PV parameter uncertainty (Rs, Rsh, I0, Iph) x all 5 controllers.
  Tests whether closed-loop controllers -- which never see the model
  directly, only measured P -- still find the ACTUAL (perturbed) panel's
  true MPP despite our modeling assumptions being off by up to +/-20%.

PART B: Converter parameter uncertainty (L, C) x M3's boost-level metrics
  only (settling time, CCM margin, switching ripple) -- NOT the controller
  comparison, for the reason above.
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from coupling import T_STC, R_LOAD_TYPICAL, D_MIN_SIM, D_MAX_SIM
from coupling_uncertain import operating_point_uncertain, true_mpp_uncertain
from po import POController
from vss_po import VSSPOController
from rls_vss import RLSVSSController
from hold_track import HoldTrackController
from full_controller import FullController

sys.path.insert(0, "../boost_model")
import averaged_model as bm  # noqa: E402
import parameters as bp  # noqa: E402

N = 400
LEVELS = [-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20]


def run_generic(ctrl_kind, mult, G, T, R_load):
    """Run one controller kind against the uncertain-PV coupling by
    monkey-patching each controller's imported `operating_point` reference
    -- avoids duplicating 5 controller classes just to swap the coupling
    function; each controller already imports `operating_point` by name
    from `coupling`, so we patch that name in the controller's own module
    namespace for the duration of the run."""
    import coupling as _coupling_mod

    def patched_op(D, G_, T_, R_):
        return operating_point_uncertain(D, G_, T_, R_, rs_mult=mult["rs"],
                                          rsh_mult=mult["rsh"], i0_mult=mult["i0"],
                                          iph_mult=mult["iph"])

    if ctrl_kind == "po":
        import po as mod
        orig = mod.operating_point
        mod.operating_point = patched_op
        ctrl = POController(D_init=0.20, step=0.01)
        Ds, Ps = [], []
        for k in range(N):
            D, V, I, P, ok = ctrl.step_once(G, T, R_load)
            Ds.append(D); Ps.append(P)
        mod.operating_point = orig
    elif ctrl_kind == "vss_po":
        import vss_po as mod
        orig = mod.operating_point
        mod.operating_point = patched_op
        ctrl = VSSPOController(D_init=0.20, step_min=0.0008, step_max=0.02, N_gain=0.00025)
        Ds, Ps = [], []
        for k in range(N):
            D, V, I, P, ok, step = ctrl.step_once(G, T, R_load)
            Ds.append(D); Ps.append(P)
        mod.operating_point = orig
    elif ctrl_kind == "rls_vss":
        import rls_vss as mod
        orig = mod.operating_point
        mod.operating_point = patched_op
        ctrl = RLSVSSController(D_init=0.20, eta=0.00008, lam=0.60, step_cap=0.02)
        Ds, Ps = [], []
        for k in range(N):
            r = ctrl.step_once(G, T, R_load)
            Ds.append(r["D"]); Ps.append(r["P"])
        mod.operating_point = orig
    elif ctrl_kind == "hold_track":
        import hold_track as mod
        orig = mod.operating_point
        mod.operating_point = patched_op
        ctrl = HoldTrackController(D_init=0.20)
        Ds, Ps = [], []
        for k in range(N):
            r = ctrl.step_once(G, T, R_load)
            Ds.append(r["D"]); Ps.append(r["P"])
        mod.operating_point = orig
    elif ctrl_kind == "full":
        ctrl = FullController(D_init=0.20, operating_point_fn=patched_op)
        Ds, Ps = [], []
        for k in range(N):
            r = ctrl.step_once(G, T, R_load)
            Ds.append(r["D"]); Ps.append(r["P"])
    else:
        raise ValueError(ctrl_kind)

    return np.array(Ds), np.array(Ps)


CONTROLLER_KINDS = {
    "A: P&O": "po", "B: VSS-P&O": "vss_po", "C: RLS-VSS": "rls_vss",
    "D: HOLD/TRACK": "hold_track", "E: Full controller": "full",
}


def part_a():
    print("=== Part A: PV parameter uncertainty (Rs, Rsh, I0, Iph) ===")
    G, T, R_load = 1000.0, T_STC, R_LOAD_TYPICAL
    results = {c: [] for c in CONTROLLER_KINDS}

    # perturb each parameter independently across all levels; report the
    # WORST-CASE efficiency across all 4 parameters at each level, since
    # that's the meaningful robustness bound
    for level in LEVELS:
        worst_eta = {c: np.inf for c in CONTROLLER_KINDS}
        for param in ["rs", "rsh", "i0", "iph"]:
            mult = {"rs": 1.0, "rsh": 1.0, "i0": 1.0, "iph": 1.0}
            mult[param] = 1.0 + level
            mpp_true = true_mpp_uncertain(G, T, rs_mult=mult["rs"], rsh_mult=mult["rsh"],
                                           i0_mult=mult["i0"], iph_mult=mult["iph"])
            for cname, kind in CONTROLLER_KINDS.items():
                Ds, Ps = run_generic(kind, mult, G, T, R_load)
                eta = np.mean(Ps[-50:]) / mpp_true
                worst_eta[cname] = min(worst_eta[cname], eta)
        for cname in CONTROLLER_KINDS:
            results[cname].append(worst_eta[cname])
        print(f"  level={level:+.0%}  " +
              "  ".join(f"{c.split(':')[0]}={results[c][-1]:.4f}" for c in CONTROLLER_KINDS))

    return results


def part_b():
    print("\n=== Part B: converter parameter uncertainty (L, C) -- boost-level metrics only ===")
    D, R_load = 0.41, R_LOAD_TYPICAL
    Vin = 17.8
    base_L, base_C = bp.L, bp.C_OUT

    rows = []
    for level in LEVELS:
        L = base_L * (1 + level)
        C = base_C * (1 + level)
        # settling time (scales with C via zeta*wn = 1/(2*R*C))
        zeta_wn = 0.5 / (R_load * C)
        t_settle = np.log(1000) / zeta_wn
        # CCM margin: R_crit(D) = 2*L*f_sw / (D*(1-D))
        R_crit = 2 * L * bp.F_SW / (D * (1 - D))
        margin = R_crit / R_load
        # inductor ripple at this L
        dIL = Vin * D / (L * bp.F_SW)
        rows.append({"level": level, "L": L, "C": C, "t_settle_ms": t_settle * 1e3,
                     "R_crit": R_crit, "CCM_margin_x": margin, "dIL_A": dIL})
        print(f"  level={level:+.0%}  L={L*1e6:.1f}uH  C={C*1e6:.0f}uF  "
              f"t_settle={t_settle*1e3:.1f}ms  CCM_margin={margin:.2f}x  dIL={dIL:.3f}A")

    return rows


def main():
    results_a = part_a()
    rows_b = part_b()

    checks = []

    def check(name, passed, detail=""):
        checks.append((name, passed, detail))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}  {detail}")

    check(
        "PART A: all controllers maintain >85% worst-case efficiency even at +/-20% PV parameter uncertainty",
        all(results_a[c][0] > 0.85 and results_a[c][-1] > 0.85 for c in CONTROLLER_KINDS),
        {c: (round(results_a[c][0], 3), round(results_a[c][-1], 3)) for c in CONTROLLER_KINDS},
    )
    check(
        "PART B: CCM margin stays above 2x across all L,C uncertainty levels (design stays safely in CCM)",
        all(r["CCM_margin_x"] > 2.0 for r in rows_b),
        f"min margin = {min(r['CCM_margin_x'] for r in rows_b):.2f}x",
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for cname in CONTROLLER_KINDS:
        axes[0].plot([l * 100 for l in LEVELS], results_a[cname], "o-", label=cname, lw=1)
    axes[0].set_xlabel("Parameter perturbation (%)"); axes[0].set_ylabel("Worst-case tracking efficiency")
    axes[0].set_title("PV parameter uncertainty: worst-case efficiency vs perturbation")
    axes[0].legend(fontsize=7); axes[0].grid(alpha=0.3)
    axes[0].set_ylim(0.8, 1.02)

    levels_pct = [r["level"] * 100 for r in rows_b]
    axes[1].plot(levels_pct, [r["t_settle_ms"] for r in rows_b], "o-", label="settling time (ms)")
    ax2 = axes[1].twinx()
    ax2.plot(levels_pct, [r["CCM_margin_x"] for r in rows_b], "s-", color="tab:orange", label="CCM margin (x)")
    axes[1].set_xlabel("L, C perturbation (%)"); axes[1].set_ylabel("Settling time (ms)")
    ax2.set_ylabel("CCM margin (x R_load)")
    axes[1].set_title("Converter (L,C) uncertainty: boost-level sensitivity")
    lines1, labels1 = axes[1].get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    axes[1].legend(lines1 + lines2, labels1 + labels2, fontsize=8)
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("../results/figures/M16_parameter_uncertainty.png", dpi=150)
    print("\nFigure saved to results/figures/")

    n_fail = sum(1 for _, p, _ in checks if not p)
    print(f"\n{len(checks)-n_fail}/{len(checks)} checks passed.")
    if n_fail > 0:
        sys.exit(1)
    else:
        print("All M16 validation checks passed.")


if __name__ == "__main__":
    main()
