"""
pv_model/validation.py

Automated validation per master prompt section 18. Run directly:
    python3 validation.py
Exits non-zero (and prints FAIL lines) if any check fails, so this can gate
progress to the next milestone rather than being a decorative script.
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from parameters import PANEL, G_STC, T_STC
from pv_model import iv_curve, mpp_from_curve

TOL_REL = 0.02  # 2% tolerance for STC reproduction checks

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}  {detail}")


def main():
    # --- STC reproduction checks ---
    V, I, P = iv_curve(G_STC, T_STC)
    voc_model = V[np.where(I <= 1e-4)[0][0]] if np.any(I <= 1e-4) else V[-1]
    isc_model = I[0]
    vmpp_model, impp_model, pmpp_model = mpp_from_curve(V, I, P)

    check(
        "Voc reproduction",
        abs(voc_model - PANEL["Voc"]) / PANEL["Voc"] < TOL_REL,
        f"model={voc_model:.3f} V, datasheet={PANEL['Voc']:.3f} V",
    )
    check(
        "Isc reproduction",
        abs(isc_model - PANEL["Isc"]) / PANEL["Isc"] < TOL_REL,
        f"model={isc_model:.3f} A, datasheet={PANEL['Isc']:.3f} A",
    )
    check(
        "Vmpp within expected range",
        abs(vmpp_model - PANEL["Vmpp"]) / PANEL["Vmpp"] < TOL_REL,
        f"model={vmpp_model:.3f} V, datasheet={PANEL['Vmpp']:.3f} V",
    )
    check(
        "Impp within expected range",
        abs(impp_model - PANEL["Impp"]) / PANEL["Impp"] < TOL_REL,
        f"model={impp_model:.3f} A, datasheet={PANEL['Impp']:.3f} A",
    )
    check(
        "Pmpp within expected range",
        abs(pmpp_model - PANEL["Pmpp"]) / PANEL["Pmpp"] < TOL_REL,
        f"model={pmpp_model:.3f} W, datasheet={PANEL['Pmpp']:.3f} W",
    )

    # --- monotonicity / physical sanity checks ---
    check("No NaN in STC current curve", not np.any(np.isnan(I)))
    check("Current is non-increasing with voltage (diode physics)",
          np.all(np.diff(I) <= 1e-6))

    # --- irradiance scaling sanity: Pmpp should scale roughly with G ---
    _, _, P_half = iv_curve(G_STC * 0.5, T_STC)
    _, Ih, Ph = mpp_from_curve(*iv_curve(G_STC * 0.5, T_STC))
    pmpp_half = Ph
    ratio = pmpp_half / pmpp_model
    check(
        "Pmpp roughly halves at half irradiance (within 15%, some nonlinearity expected)",
        0.35 < ratio < 0.65,
        f"ratio={ratio:.3f}",
    )

    # --- temperature scaling sanity: Voc should DECREASE as T increases ---
    V_hot, I_hot, P_hot = iv_curve(G_STC, T_STC + 25)
    voc_hot = V_hot[np.where(I_hot <= 1e-4)[0][0]] if np.any(I_hot <= 1e-4) else V_hot[-1]
    check(
        "Voc decreases with +25C temperature rise (correct sign)",
        voc_hot < voc_model,
        f"Voc(T_stc)={voc_model:.3f} V, Voc(T_stc+25C)={voc_hot:.3f} V",
    )

    # --- figures ---
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for G in [1000, 800, 600, 400, 200]:
        Vg, Ig, Pg = iv_curve(G, T_STC)
        axes[0].plot(Vg, Ig, label=f"{G} W/m2")
        axes[1].plot(Vg, Pg, label=f"{G} W/m2")
    axes[0].set_xlabel("V (V)"); axes[0].set_ylabel("I (A)")
    axes[0].set_title("I-V curves, varying irradiance, T=25C (PLACEHOLDER panel)")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
    axes[1].set_xlabel("V (V)"); axes[1].set_ylabel("P (W)")
    axes[1].set_title("P-V curves, varying irradiance, T=25C (PLACEHOLDER panel)")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("../results/figures/M2_pv_iv_pv_curves_irradiance.png", dpi=150)

    fig2, axes2 = plt.subplots(1, 2, figsize=(11, 4.5))
    for T_c in [0, 25, 45, 65]:
        Vt_, It_, Pt_ = iv_curve(G_STC, T_c + 273.15)
        axes2[0].plot(Vt_, It_, label=f"{T_c} C")
        axes2[1].plot(Vt_, Pt_, label=f"{T_c} C")
    axes2[0].set_xlabel("V (V)"); axes2[0].set_ylabel("I (A)")
    axes2[0].set_title("I-V curves, varying temperature, G=1000 (PLACEHOLDER panel)")
    axes2[0].legend(fontsize=8); axes2[0].grid(alpha=0.3)
    axes2[1].set_xlabel("V (V)"); axes2[1].set_ylabel("P (W)")
    axes2[1].set_title("P-V curves, varying temperature, G=1000 (PLACEHOLDER panel)")
    axes2[1].legend(fontsize=8); axes2[1].grid(alpha=0.3)
    fig2.tight_layout()
    fig2.savefig("../results/figures/M2_pv_iv_pv_curves_temperature.png", dpi=150)

    print("\nFigures saved to results/figures/")

    n_fail = sum(1 for _, p, _ in results if not p)
    print(f"\n{len(results)-n_fail}/{len(results)} checks passed.")
    if n_fail > 0:
        print("STOP: do not proceed to M3 until failing checks are resolved "
              "(master prompt section 18).")
        sys.exit(1)
    else:
        print("All M2 validation checks passed.")


if __name__ == "__main__":
    main()
