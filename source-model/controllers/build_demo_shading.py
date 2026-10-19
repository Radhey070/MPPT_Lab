"""
controllers/build_demo_shading.py

M26: second demo asset -- the "honest limitation" demo. Reuses M14's
scenario 2 (start near the local peak's basin under shading, D_init=0.65)
because it's the dramatic, memorable, and completely honest illustration
of the project's most significant limitation: the controller climbs to
the WRONG peak and gets stuck there permanently, with SEARCH never firing.

This is deliberately included in the demo package (not hidden) -- a demo
that only shows successes is weaker evidence of rigor than one that also
shows a real, understood limitation live.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from coupling import T_STC, R_LOAD_TYPICAL, D_MIN_SIM, D_MAX_SIM
from coupling_shaded import shaded_operating_point
from full_controller import FullController

T = T_STC
R_load = R_LOAD_TYPICAL
G_shaded = [1000.0, 600.0, 300.0]
N = 400
D_START = 0.65

STATE_COLORS = {"TRACK": "#3b82f6", "HOLD": "#22c55e", "SEARCH": "#ef4444"}


def run_scenario():
    ctrl = FullController(D_init=D_START, operating_point_fn=shaded_operating_point)
    Ds, Ps, Vs, confs, states = [], [], [], [], []
    for k in range(N):
        r = ctrl.step_once(G_shaded, T, R_load)
        Ds.append(r["D"]); Ps.append(r["P"]); Vs.append(r["V"])
        confs.append(r["confidence"]); states.append(r["state"])
    return np.array(Ds), np.array(Ps), np.array(Vs), np.array(confs), states


def main():
    Ds, Ps, Vs, confs, states = run_scenario()

    Ds_curve = np.linspace(D_MIN_SIM, D_MAX_SIM, 250)
    Ps_curve = np.array([shaded_operating_point(d, G_shaded, T, R_load)[2] for d in Ds_curve])
    Vs_curve = np.array([shaded_operating_point(d, G_shaded, T, R_load)[0] for d in Ds_curve])
    idx_sorted = np.argsort(Vs_curve)
    Vc, Pc = Vs_curve[idx_sorted], Ps_curve[idx_sorted]

    D_global = Ds_curve[np.argmax(Ps_curve)]
    P_global = Ps_curve.max()
    V_global = shaded_operating_point(D_global, G_shaded, T, R_load)[0]

    frame_idxs = list(range(1, N, 3))
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    def draw_frame(k):
        for ax in axes:
            ax.clear()
        axes[0].plot(Vc, Pc, color="gray", lw=1.5)
        axes[0].scatter([V_global], [P_global], color="k", marker="x", s=70,
                         label="TRUE global peak", zorder=5)
        axes[0].scatter([Vs[k]], [Ps[k]], color=STATE_COLORS[states[k]], s=110,
                         edgecolor="k", zorder=6, label="operating point")
        axes[0].set_xlim(0, 22); axes[0].set_ylim(0, 25)
        axes[0].set_xlabel("V (V)"); axes[0].set_ylabel("P (W)")
        pct = 100 * Ps[k] / P_global
        axes[0].set_title(f"Iteration {k} | State: {states[k]} | {pct:.0f}% of true global peak",
                           color=STATE_COLORS[states[k]], fontweight="bold")
        axes[0].legend(loc="upper left", fontsize=8)

        for i in range(1, k + 1):
            axes[1].plot([i - 1, i], [confs[i - 1], confs[i]], color=STATE_COLORS[states[i]], lw=1.2)
        axes[1].set_xlim(0, N); axes[1].set_ylim(0, 1.05)
        axes[1].set_xlabel("iteration"); axes[1].set_ylabel("Confidence")
        axes[1].set_title("Confidence stays high -> controller never doubts itself")
        fig.tight_layout()
        return []

    ani = animation.FuncAnimation(fig, draw_frame, frames=frame_idxs, blit=False)

    try:
        ani.save("../results/figures/M26_demo_shading_trap.mp4",
                 writer=animation.FFMpegWriter(fps=20, bitrate=1500), dpi=110)
        print("Saved shading-trap MP4.")
    except Exception as e:
        print(f"MP4 export failed ({e}), GIF fallback only.")
    ani.save("../results/figures/M26_demo_shading_trap.gif",
             writer=animation.PillowWriter(fps=20), dpi=90)
    print("Saved shading-trap GIF (fallback).")
    plt.close(fig)


if __name__ == "__main__":
    main()
