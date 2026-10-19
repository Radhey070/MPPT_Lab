"""
controllers/build_demo_animation.py

M17: live/pseudo-real-time demonstration (master prompt sections 19-20).
Reuses M10's proven SEARCH-triggering scenario (steady -> noise burst ->
recovery) so the demo is built on already-validated behavior, not a new
untested run. Renders a multi-panel dashboard animation:
  - P-D curve with the live operating point and true MPP marked
  - Duty cycle vs iteration
  - Tracked power vs iteration
  - Confidence vs iteration, background-shaded by controller state
  - A state badge (HOLD/TRACK/SEARCH) with distinct colors

Saves both an MP4 (primary) and a GIF (fallback, per master prompt section
27 -- "the demo should remain functional even if a live component fails,
always maintain a simulation fallback"; here that principle is applied to
playback format itself: MP4 needs ffmpeg, GIF does not).

Also saves a static 6-frame storyboard figure as a print-friendly fallback
for slides/report where video isn't usable.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from coupling import T_STC, R_LOAD_TYPICAL, D_MIN_SIM, D_MAX_SIM, iv_curve, mpp_from_curve
from full_controller import FullController

G, T = 1000.0, T_STC
R_load = R_LOAD_TYPICAL
N = 600
burst_start, burst_end = 150, 400

STATE_COLORS = {"TRACK": "#3b82f6", "HOLD": "#22c55e", "SEARCH": "#ef4444"}


def run_scenario():
    ctrl = FullController(D_init=0.20)
    Ds, Ps, Vs, confs, states = [], [], [], [], []
    for k in range(N):
        ctrl.noise_sigma = 8.0 if burst_start <= k < burst_end else 0.0
        r = ctrl.step_once(G, T, R_load)
        Ds.append(r["D"]); Ps.append(r["P"]); Vs.append(r["V"])
        confs.append(r["confidence"]); states.append(r["state"])
    return (np.array(Ds), np.array(Ps), np.array(Vs), np.array(confs), states)


def main():
    Ds, Ps, Vs, confs, states = run_scenario()

    Vc, Ic, Pc = iv_curve(G, T)
    Vmpp, Impp, Pmpp = mpp_from_curve(Vc, Ic, Pc)
    Ds_curve = np.linspace(D_MIN_SIM, D_MAX_SIM, 200)

    # ---------------- animation ----------------
    frame_stride = 4
    frame_idxs = list(range(1, N, frame_stride))

    fig = plt.figure(figsize=(12, 7))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.1, 1], height_ratios=[1, 1, 1])
    ax_pv = fig.add_subplot(gs[:, 0])
    ax_d = fig.add_subplot(gs[0, 1])
    ax_p = fig.add_subplot(gs[1, 1])
    ax_c = fig.add_subplot(gs[2, 1])

    def draw_frame(k):
        for ax in (ax_pv, ax_d, ax_p, ax_c):
            ax.clear()

        ax_pv.plot(Vc, Pc, color="gray", lw=1.5, label="P-V curve")
        ax_pv.scatter([Vmpp], [Pmpp], color="k", marker="x", s=60, label="true MPP", zorder=5)
        ax_pv.scatter([Vs[k]], [Ps[k]], color=STATE_COLORS[states[k]], s=110, zorder=6,
                      edgecolor="k", label="operating point")
        ax_pv.set_xlim(0, 24); ax_pv.set_ylim(0, 60)
        ax_pv.set_xlabel("V (V)"); ax_pv.set_ylabel("P (W)")
        ax_pv.set_title(f"Iteration {k}   |   State: {states[k]}   |   "
                         f"{'NOISE BURST ACTIVE' if burst_start <= k < burst_end else 'clean'}",
                         color=STATE_COLORS[states[k]], fontweight="bold")
        ax_pv.legend(loc="lower right", fontsize=8)

        ax_d.plot(Ds[:k+1], color="black", lw=1)
        ax_d.axvspan(burst_start, min(k, burst_end), color="red", alpha=0.08)
        ax_d.set_xlim(0, N); ax_d.set_ylim(D_MIN_SIM, D_MAX_SIM)
        ax_d.set_ylabel("Duty D"); ax_d.set_title("Duty cycle")

        ax_p.plot(Ps[:k+1], color="black", lw=1)
        ax_p.axhline(Pmpp, color="gray", ls="--", lw=0.8)
        ax_p.axvspan(burst_start, min(k, burst_end), color="red", alpha=0.08)
        ax_p.set_xlim(0, N); ax_p.set_ylim(0, 60)
        ax_p.set_ylabel("P (W)"); ax_p.set_title("Tracked power")

        for i in range(1, k + 1):
            ax_c.plot([i - 1, i], [confs[i - 1], confs[i]], color=STATE_COLORS[states[i]], lw=1.2)
        ax_c.axvspan(burst_start, min(k, burst_end), color="red", alpha=0.08)
        ax_c.set_xlim(0, N); ax_c.set_ylim(0, 1.05)
        ax_c.set_xlabel("iteration"); ax_c.set_ylabel("Confidence")
        ax_c.set_title("Confidence (color = state: blue=TRACK, green=HOLD, red=SEARCH)")

        fig.tight_layout()
        return []

    ani = animation.FuncAnimation(fig, draw_frame, frames=frame_idxs, blit=False)

    try:
        writer_mp4 = animation.FFMpegWriter(fps=20, bitrate=1800)
        ani.save("../results/figures/M17_demo_dashboard.mp4", writer=writer_mp4, dpi=110)
        print("Saved MP4 demo animation.")
    except Exception as e:
        print(f"MP4 export failed ({e}), continuing with GIF fallback only.")

    writer_gif = animation.PillowWriter(fps=20)
    ani.save("../results/figures/M17_demo_dashboard.gif", writer=writer_gif, dpi=90)
    print("Saved GIF demo animation (fallback format, no ffmpeg dependency).")

    plt.close(fig)

    # ---------------- static storyboard fallback ----------------
    story_idxs = [5, 60, 220, 250, 405, 595]  # k=220 explicitly lands inside a
    # SEARCH episode (verified: SEARCH occurs at k=214-228 and 289-293 in this
    # run) -- master prompt sections 19-20 specifically want the SEARCH
    # transition visible, so this is chosen deliberately, not left to chance.
    story_idxs = [i for i in story_idxs if i < N]
    fig2, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, k in zip(axes.flat, story_idxs):
        ax.plot(Vc, Pc, color="gray", lw=1.2)
        ax.scatter([Vmpp], [Pmpp], color="k", marker="x", s=50)
        ax.scatter([Vs[k]], [Ps[k]], color=STATE_COLORS[states[k]], s=90,
                   edgecolor="k", zorder=5)
        ax.set_xlim(0, 24); ax.set_ylim(0, 60)
        ax.set_title(f"k={k}, state={states[k]}", color=STATE_COLORS[states[k]], fontweight="bold")
        ax.set_xlabel("V (V)"); ax.set_ylabel("P (W)")
    fig2.suptitle("Demo storyboard fallback (static, no video needed)", fontsize=13)
    fig2.tight_layout()
    fig2.savefig("../results/figures/M17_demo_storyboard.png", dpi=150)
    print("Saved static storyboard fallback.")


if __name__ == "__main__":
    main()
