# METRIC DEFINITIONS (M12)

Every metric used in the ablation study and beyond, defined precisely
before use, per master prompt section 10/section 18.

## Tracking efficiency (eta_MPPT)

    eta_MPPT = ( (1/N) * sum_{k=1..N} P(k) ) / P_mpp_true

Mean tracked power over the full run (including startup transient, which
is common to all controllers and therefore a fair basis for comparison),
divided by the true maximum power point power for the prevailing
irradiance/temperature (computed independently via pv_model.py, M2).
Reported separately as a STEADY-STATE variant using only the final 50
samples, to separate "how fast/well did it get there" from "how well does
it hold once there."

## Energy harvested (E)

    E = sum_{k=1..N} P(k)   [units: W per control cycle -- see note]

NOTE: no real control-loop sampling period has been fixed yet (that is an
M18 embedded-implementation decision). E is reported in these
"power-cycle units" and used ONLY for RATIO comparisons between
controllers under identical N and identical conditions, never as an
absolute joule figure. This is scientifically valid (energy differences
scale linearly with whatever real Δt is eventually chosen) but must be
stated as a caveat wherever E appears in the report.

## Activity index (A)

    A = ( number of control cycles where duty was actually perturbed ) / N

"Perturbed" means the controller's own step_once explicitly changed D that
cycle (returned via the `perturbed` field for stage D/E controllers; for
stages A-C, which have no HOLD capability, every cycle perturbs by
construction, so A=1.0 exactly, not measured).

## Steady-state oscillation

    osc = max(D[-50:]) - min(D[-50:])

Peak-to-peak duty range over the final 50 samples of a run.

## Search energy loss (stage E only, where SEARCH occurs)

    E_search_loss = sum over SEARCH-state cycles of (P_mpp_true - P(k))

Power foregone during SEARCH sweeps relative to ideal tracking, summed
over the run. Zero for stages A-D (no SEARCH mechanism).

## Noise robustness

Each metric above is also reported under an injected measurement-noise
condition (Gaussian, sigma=1.5 W on the P measurement each controller
uses for its own decision-making -- matching the level established at
M7/M8), averaged over multiple random seeds where variance matters
(matching the multi-seed methodology already used at M7).
