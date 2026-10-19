# PROJECT STATE

Last updated: M28 complete (final audit) -- all 28 milestones now addressed; M18-M21 remain blocked on hardware inputs

## Project identity

**Title (working):** Confidence-Aware Adaptive MPPT — A Model-Based Design and
Hardware-Validated Study of Online Duty-Space Estimation for Solar PV Boost
Converters

**Type:** Model-based design project (Model -> Simulate -> Design -> Validate ->
Implement -> Compare). The controller is one component of this pipeline, not
the entire project identity.

**Research question:**
Can an online confidence estimate of the local PV operating point allow an
MPPT controller to reduce unnecessary control activity and search-induced
energy loss without sacrificing tracking accuracy, compared with conventional
and adaptive MPPT baselines, and does this remain valid on real embedded
hardware?

## Completed milestones

- [x] M0 — Project initialization (repo, docs, parameter registry, trackers)
- [x] M0.5 — Real hardware data incorporated (schematic images: L, C_in,
      C_out, current shunts, voltage divider ratios, gate driver
      identified as UCC27517A with externally-set f_sw; f_sw sized at
      ~45kHz from real L/C values, see switching_frequency_sizing.md)
- [x] M1 — Literature and research-gap foundation (15-entry survey across
      9 categories; differentiation statement checked against survey, not
      assumed)
- [x] M2 — PV mathematical model. Single-diode model implemented
      (pv_model/pv_model.py) with parameters numerically extracted
      (pv_model/parameter_extraction.py: Rs=0.1587 ohm, Rsh=187.6 ohm,
      Iph=3.353 A, I0=5.11e-8 A, all fsolve-converged, not guessed). 9/9
      automated validation checks passed: Voc/Isc/Vmpp/Impp/Pmpp reproduce
      the placeholder datasheet within 2%, current is monotonic in voltage,
      Pmpp scales correctly with irradiance, Voc has correct sign with
      temperature. Figures saved to results/figures/.
- [x] M3 — Boost converter mathematical model. Derived analytically during
      a sandbox outage (docs/boost_converter_derivation.md: switching-state
      equations, averaged CCM model, steady-state Vout=Vin/(1-D), CCM
      boundary R_crit(D), and a new proof that R_in,effective(D)=(1-D)^2*R
      is monotonic -- formal justification for D0.2's duty-space RLS
      choice). Implemented using REAL L=220uH, C_out=671uF, C_in=320uF.
      First validation run failed 4/10 checks; root cause diagnosed
      (lossless model is underdamped, zeta~0.029, needs ~150-200ms/~7000
      cycles to settle, not the 50ms/300 cycles first tried) and fixed
      properly, not by loosening tolerances -- see D0.14. Retested: 10/10
      checks pass. Genuine finding logged: real hardware's unknown inductor
      ESR will damp the true transient response much faster than this
      lossless model shows.
- [x] M4 — Baseline P&O (ablation stage A). Implemented quasi-static
      PV-boost coupling (controllers/coupling.py, explicit modeling
      simplification logged as D0.15) and fixed-step duty-cycle P&O
      (controllers/po.py). Two real bugs found and fixed during
      validation, not hidden -- see D0.16 (a module-name import collision,
      and a controller-logic bug where the first two iterations didn't
      perturb correctly). 5/5 checks pass: converges to within 0.3% of the
      analytic MPP duty, reaches 99.97% of true Pmpp, duty stays in bounds,
      oscillation amplitude matches expected P&O behavior.
- [x] M5 — VSS-P&O (ablation stage B). Finite-difference slope-scaled
      adaptive step. First attempt failed 2/7 checks (step never shrank,
      pinned at step_max; oscillation was WORSE than plain P&O) due to a
      gain-calibration bug -- N_gain=0.5 was far too high given the actual
      curvature-dominated secant slope near the MPP (~3-9 W/duty at
      dD=0.02, not near-zero). Recalibrated N_gain from measured slope data
      (not guessed) to N_gain=0.00025. Retested: 7/7 pass. VSS-P&O reaches
      99% of Pmpp in 10 iterations vs P&O's 19, and settles to 12.5x
      tighter steady-state oscillation (0.0016 vs 0.02 duty range) --
      demonstrated head-to-head under identical conditions, not asserted.
- [x] M6 — Duty-space RLS estimator. Implemented and validated
      STANDALONE with synthetic data, independent of the PV/boost model
      (master prompt section 18). Includes periodic covariance-reset
      windup protection, demonstrated (not just designed): trace(P) grows
      ~15x over 3000 iterations under non-persistent excitation without
      reset, stays bounded within [1000,2000] with reset. Lambda
      sensitivity study across 5 values (10-seed noise averaging) shows
      noise rejection improves monotonically with lambda (5.14 -> 0.58 in
      theta units from lambda=0.90 to 0.995); convergence speed on clean
      synthetic data was flat (~4 iterations) across all tested lambda, so
      noise rejection is the real differentiator here. Recommended
      lambda=0.995, with an explicit caveat logged: this only tested a
      STATIC true slope, not tracking speed after a slope change (e.g. an
      irradiance step) -- that's properly E02/E03's job, and lambda should
      be revisited once those results exist. One test-design bug found and
      fixed during validation (not an estimator bug) -- see D0.18.
- [x] M7 — RLS-VSS controller (ablation stage C). Three issues caught and
      documented, not hidden: (1) sign of the gradient law verified
      numerically BEFORE coding, per master prompt section 5 -- the naive
      D(k+1)=D(k)-eta*theta_hat would have diverged; corrected to gradient
      ASCENT. (2) An unfair noise comparison caught before running (RLS-VSS
      would have gotten noisy P, VSS-P&O clean P) -- fixed by adding
      matching noise injection to VSS-P&O too. (3) M6's noise-optimal
      lambda=0.995 caused severe closed-loop overshoot (converged near
      D=0.48-0.54 instead of 0.4069) because RLS was fitting a stale global
      model instead of the local, moving slope target -- recalibrated to
      lambda=0.60, eta=0.00008 empirically. IMPORTANT FINDING: under noise,
      lambda=0.60 gives up most of RLS's noise-rejection advantage (theta_hat
      swings +-100+ sample to sample) -- RLS-VSS beats VSS-P&O on
      oscillation (0.035 vs 0.091 duty range) but is LESS accurate
      (error 0.023 vs 0.010), a genuine structural trade-off (can't
      simultaneously track a moving target AND reject noise with one fixed
      lambda) that directly motivates the confidence-gated HOLD state at
      M9. 6/6 checks pass with this trade-off stated explicitly.
- [x] M8 — Confidence metric. Deterministic C in [0,1] from RLS residual
      RMS + theta_hat std (D0.5, no ML classifier). Validated against REAL
      controller streams (stable/noisy/transient regimes), not synthetic
      data. Found and fixed a genuine covariance-windup bug in
      RLSVSSController itself along the way (D0.20): after an irradiance
      step the closed loop could enter an exact 2-value duty limit cycle,
      starving RLS of persistent excitation and producing absurd theta_hat
      (-4529). Fixed by defaulting reset_interval=50; verified the fix
      against an independent numerical MPP search (converges to D=0.293 at
      G=700 W/m^2, exactly correct). This also revised M7's noise-accuracy
      finding: RLS-VSS's accuracy under noise is now ~equal to VSS-P&O's
      (was reported as meaningfully worse due to the windup artifact).
      Final: clean regime separation (C=0.9997 stable vs 0.2333 noisy),
      textbook dip-and-recovery at an irradiance step (0.997 -> 0.114 ->
      0.993), threshold sensitivity study recommends ~0.70 as a starting
      point for M9. 7/7 checks pass.
- [x] M9 — HOLD/TRACK state machine (ablation stage D). Confidence-gated
      HOLD/TRACK with hysteresis + persistence (C_enter=0.70, C_exit=0.40,
      persistence=5). First run passed all 8 numeric checks but a visual
      inspection of the figure caught a real bug the checks missed:
      premature HOLD entry at D=0.288 (15% power loss vs true Pmpp) because
      confidence alone (residual/variance consistency) doesn't imply
      proximity to the MPP -- a smooth climb far from the peak also looks
      "confident." Fixed by adding a second, independent gate:
      |theta_hat| < 5.0 required alongside confidence for HOLD entry.
      Retested: HOLD now correctly enters at D=0.4178 (99.7% of Pmpp).
      Activity index = 0.182 vs always-tracking RLS-VSS's 1.0 (a real, now-
      honest reduction in unnecessary perturbation), 3 total state
      transitions over 500 iterations (no chattering), correctly detects
      and recovers from an irradiance step. 8/8 checks pass.
- [x] M10/M11 — Bounded SEARCH / Full controller (ablation stage E,
      collapsed into one deliverable -- SEARCH had to be built integrated
      with the existing HOLD/TRACK state machine, not standalone, so M11's
      literal scope ("full controller, ablation stage E") was already
      satisfied by finishing M10 properly). Applied M9's lesson proactively
      this time: added an _ever_held gate so SEARCH can only trigger after
      HOLD has been reached once, preventing a spurious trigger during
      normal startup. Validated in three parts: standalone sweep-mechanics
      unit test (bounded at exactly 15 steps, lands within one sample-
      spacing of the true MPP); regression check confirming SEARCH does
      NOT spuriously fire under M9's ordinary scenario; and a genuine
      SEARCH-triggering scenario (sustained high-noise burst after HOLD)
      that correctly triggers SEARCH 3 times (bounded, not runaway) and
      recovers to within 0.015 of the true MPP duty once the burst clears.
      Figure inspected per M9's lesson -- this time confirmed correctness
      rather than finding a new bug. 8/8 checks pass. This is now the
      complete, final proposed controller (all five ablation stages A-E
      exist and are individually validated).
- [x] M12 — Ablation study A-E. Ran all five controllers under IDENTICAL
      conditions (clean and noisy, 8-seed average), computing every metric
      defined in the new docs/metrics_definitions.md. Fixed a real fairness
      gap first: POController had no noise-injection support (same class
      of bug as M7's D0.19), added it, re-verified M4 still passes.
      CENTRAL RESULT: activity index drops from 1.000 (stages A-C, no HOLD
      capability) to 0.104 (stages D/E) under clean conditions -- the
      project's core claim, now measured, not asserted -- at a steady-
      state efficiency cost of only 0.29 percentage points. FINDING under
      noise, verified by tracing a raw run (not just eyeballed): stages D
      and E behave IDENTICALLY to stage C under sustained noise (0 HOLD
      entries over 500 iterations), because mean confidence under that
      noise level (0.233, per M8) never reaches C_enter (0.70) -- the
      architecture correctly refuses to freeze when it can't trust its own
      estimate, gracefully degrading rather than risking a bad freeze. This
      makes the activity-index benefit specifically a STEADY-CONDITIONS
      benefit, an important precise scope statement for the paper, not a
      weakness to hide. 4/4 sanity checks pass, figure confirms all
      findings with no new anomalies.
- [x] M13 — Dynamic-condition experiments (E02/E03/E04/E15). Single,
      well-separated step changes (irradiance, temperature, load): all
      controllers recover cleanly, D/E reach 97.7-98.4% overall efficiency
      (slightly below always-tracking controllers, expected). RAPID,
      closely-spaced irradiance changes (E03): a genuinely important find
      -- D/E's overall efficiency (0.802) drops BELOW even RLS-VSS's
      (0.848) and clearly below classical always-tracking controllers
      (0.925-0.928). Traced the exact mechanism: HOLD can re-enter before
      the controller has fully reconverged to a new MPP when disturbances
      arrive closely spaced, freezing at an under-converged point through
      the NEXT disturbance too. Same failure class as M9's premature-HOLD
      bug (D0.22), different trigger condition (rapid spacing, not just
      a smooth climb). Confirmed visually -- E03's panel shows the
      Full controller plateauing at ~0.80 then ~0.65 instead of recovering.
      This REFINES M12's scope statement: the activity benefit holds under
      steady conditions and isolated disturbances, but the fixed-threshold
      HOLD mechanism can actively hurt tracking under rapid, closely-spaced
      disturbances. Logged as a genuine limitation with a concrete future-
      work fix (adaptive persistence / minimum-time-since-disturbance
      gate), not softened. 6/6 sanity checks pass (deliberately achievable
      bars, not blind to the finding).
- [x] M14 — Partial-shading experiments. Built pv_model/partial_shading.py
      (3 series bypass-diode substrings). First version had a real
      calibration bug (independent per-substring re-extraction reproduced
      only 89% of the original panel's Pmpp under uniform irradiance) --
      fixed via analytic parameter scaling instead, now matches to 0.00%
      error. Confirmed genuine multi-peak generation under asymmetric
      shading. Made FullController's coupling pluggable
      (operating_point_fn) to test the same controller against the shaded
      model without duplicating logic; verified no regression (M10, M12
      re-run clean). TWO scenarios tested: (1) shading onset from a
      converged uniform state -- controller finds the TRUE GLOBAL peak
      (99.9% of its power) WITHOUT SEARCH ever triggering, because the
      pre-shading duty already sat in the global peak's basin -- a real
      but lucky-starting-position result, not evidence SEARCH works. (2)
      Starting directly near the LOCAL peak's basin -- the genuine test --
      TRACK confidently converges to the local peak and enters HOLD there
      permanently; SEARCH NEVER triggers over 600 iterations, since
      confidence measures local-model fit quality, not global optimality,
      and a converged local peak looks exactly as "confident" as the true
      one. Result: permanently stuck at 64.3% of true global peak power.
      FUNDAMENTAL LIMITATION, not a tuning bug: this controller has no
      mechanism to detect or escape local-maximum convergence under
      partial shading. Added as Known Limitation #0 (most significant
      found so far) with a concrete future-work fix identified. 4/5 checks
      pass -- the "failure" is the intended, honest confirmation of the
      limitation.
- [x] M15 — Monte Carlo validation. N=60 randomized standard-condition
      scenarios (all 5 controllers, definitions stored to
      results/raw_data/) + N=25 randomized shading patterns (Full
      controller). Part A confirms M13's finding with real statistical
      breadth: stages D/E show the lowest AND most variable efficiency of
      all five controllers (0.969 +/- 0.055), with outlier scenarios as
      low as 0.68-0.69 -- not a one-off. Activity index for D/E averaged
      0.191 +/- 0.101 across randomized conditions, confirming the benefit
      is real and general, just more variable than the single steady-
      condition figure. Part B substantially sharpens M14's finding:
      TRAP RATE = 52.0% (13/25) -- close to a coin flip, not a rare edge
      case -- mean fraction of true global peak power reached 86.2%, real
      cases as low as 57.7%. One quick bug fixed before running (return-
      value unpacking mismatch with dynamic_experiments.py's 4-tuple).
      Both Known Limitations below updated with this statistical backing.
      4/4 checks pass.
- [x] M16 — Parameter uncertainty (+/-5/10/20%). Part A (PV parameters,
      all 5 controllers): reassuring, expected result -- all controllers
      are closed-loop and never consult the PV model online, so tracking
      efficiency stays >99.7% even at +/-20% combined Rs/Rsh/I0/Iph
      uncertainty (measured against the ACTUAL perturbed panel's true
      MPP, not the nominal one). Part B (converter L/C, boost-level
      metrics only -- explicitly scoped out of controller-level testing
      since the quasi-static coupling, D0.15, has no L/C dependence): CCM
      margin stays above 3.95x even at -20% L, comfortably clear of the
      boundary. One test-calibration bug fixed: settling time is exactly
      linear in C, so an arbitrary "<1.5x" bound was always going to
      collide with the exact 1.2/0.8=1.5x answer at +/-20% -- fixed to
      assert the correct theoretical value instead. 2/2 and 3/3 checks
      pass respectively.
- [x] M17 — Visualization/dashboard. Built controllers/build_demo_animation.py
      reusing M10's already-validated SEARCH-triggering scenario (steady
      -> noise burst -> recovery) rather than a fresh, untested one. Three
      artifacts: MP4 (primary), GIF (fallback, no ffmpeg dependency), and
      a static 6-frame storyboard PNG (print/slide fallback). Dashboard
      shows P-D curve with live operating point + true MPP, duty-cycle
      strip, power strip, and state-colored confidence strip together per
      frame. Caught and fixed one gap before finalizing: the first
      storyboard frame selection missed the SEARCH state entirely (short,
      bounded 15-step sweeps are easy to miss with arbitrary indices) --
      checked the actual state trace programmatically and picked a frame
      that deliberately lands inside a real SEARCH episode, since the
      master prompt explicitly wants HOLD->TRACK->SEARCH->TRACK visible.
- [x] M22 — Final statistical analysis (jumped ahead of blocked M18-M21
      per this doc's own prior note). Built controllers/final_summary.py,
      which imports and re-runs each source milestone's own validated
      functions (M12, M13, M15) directly rather than hand-transcribing
      numbers -- guarantees consistency with the original computations.
      Output: results/tables/master_summary.csv (81 rows) and a single
      3-panel headline figure telling the whole project's story (benefit,
      honest limitation, most significant limitation) in one image.
      3/3 checks pass -- one initial failure was the CHECK's own arithmetic
      bug (wrong expected row count formula), caught because two other
      independent checks against the same data both passed, confirming
      the underlying data was correct and only the check's expected value
      was wrong; fixed and re-verified.

## In progress

- [x] M28 — Final audit. Performed an actual regression check (not just
      narrative review): re-ran 13 validation/experiment scripts,
      zero discrepancies found. Wrote report/final_audit_m28.md: a
      genuinely critical six-perspective audit that found 5 real,
      previously undocumented gaps (no formal stability proof, no
      fixed-point arithmetic testing, no cross-check against the known
      ~95% measured hardware efficiency, literature statement needs one
      more re-check, no confidence interval on the 52% trap-rate
      estimate). None block M18 or current reporting; all disclosed as
      remaining-time work or future-work items. VERDICT: simulation phase
      substantively complete and internally consistent, not yet
      "finished."
- [x] M27 — Viva preparation. report/viva_preparation.md: Q&A organized
      by six audit perspectives (control-systems, embedded, power-
      electronics, research reviewer, skeptical examiner, project
      evaluator) plus a competition-judge pitch and a quick-facts cheat
      sheet. Every answer grounded in real project derivations/results,
      not generic talking points. NOTE: sandbox environment reset
      between M26 and M27 (working directory wiped); no data lost since
      the persistent outputs copy was intact and restored before
      continuing -- confirms the sync-after-every-milestone discipline
      does its job.
- [x] M26 — Competition/demo package. Two animation assets: M17's
      success-case dashboard, and a new honest-limitation clip
      (controllers/build_demo_shading.py, reproduces M14's exact finding:
      D=0.698, P=13.85W, confidence=1.0, permanently trapped). Deliberately
      showing both, not just the success case. report/demo_script.md maps
      both to the master prompt's 10-point demo checklist with an explicit
      fallback plan (every visual exists as a static file). One-command
      deterministic rebuild (controllers/rebuild_demo_package.py) tested
      end-to-end -- reproduces identical numbers to every original run.
- [x] M25 — Presentation content (v2). 20-slide text + diagram
      instructions given directly in chat, per the user's stated
      preference for external-tool-ready text rather than a generated
      deck. Supersedes the pre-M12 first-review outline -- now built
      around the actual completed results (5-stage ablation, 89.6%
      activity reduction, both honestly-quantified limitations as
      dedicated slides). Reference copy: report/presentation_outline_v2.md.
- [~] M24 — Final project report v1 written (report/final_report_v1.md,
      18 sections). Reuses M23's already-verified numbers rather than a
      second transcription pass. Includes a dedicated Hardware
      Architecture chapter (descriptive, from real schematic data) kept
      strictly separate from hardware RESULTS, which remain pending.
      Section 12 catalogs all real bugs found and fixed across the
      project as a deliberate rigor signal.
- [~] M23 — Paper draft v1 written (paper/draft_v1.md). All numbers
      cross-verified against results/tables/master_summary.csv and
      ablation_summary.csv before writing, not transcribed from memory.
      Hardware Validation section correctly left PENDING (no fabricated
      placeholder numbers), per master prompt section 24. Remaining for
      v2: formatted IEEE references, architecture diagram embedded as an
      actual figure (not just described), and a pass once M18-M21
      hardware results exist.
- [ ] M18 — Embedded implementation (blocked, see below)

## Known limitations (living list, updated as found -- see decision log for full context)

0. **[MOST SIGNIFICANT] No mechanism to detect or escape a local (non-
   global) maximum under partial shading** (M14 D0.26, sharpened with
   statistics at M15 D0.27): once TRACK converges to ANY local peak, the
   local model fits cleanly and confidence is legitimately high by its own
   definition -- SEARCH, which only triggers on LOW confidence, never
   fires. QUANTIFIED across 25 randomized shading patterns (M15): trap
   rate = 52.0% (13/25) -- this is close to a coin flip, not a rare edge
   case. Mean fraction of true global peak power reached: 86.2%, with real
   cases as low as 57.7%. This is a well-known, fundamental challenge for
   local-search MPPT generally, not unique to this design, but must be
   stated plainly and with this severity as a limit on what this
   controller's SEARCH mechanism actually guarantees (it helps recover
   from instability/uncertainty, not from confident convergence to the
   wrong point). Future-work fix identified, not implemented: periodic
   mandatory coarse re-scans regardless of confidence, or a wider-context
   signal tracking whether nearby duty values were ever explored during
   the current convergence episode.

1. **Rapid, closely-spaced disturbances degrade the HOLD mechanism's
   benefit into a cost** (M13 D0.25, sharpened with statistics at M15
   D0.27): fixed persistence/threshold values tuned for isolated single
   transitions (M9) don't leave enough time to fully reconverge when
   disturbances arrive faster than roughly persistence + typical
   convergence time. Concrete single-scenario evidence (M13): E03 overall
   efficiency for stages D/E (0.802) is below stage C's (0.848) and well
   below stages A/B's (0.925-0.928). QUANTIFIED across 60 randomized
   scenarios (M15): stages D/E show the lowest AND most variable mean
   efficiency of all five controllers (0.969 +/- 0.055, vs stage C's
   0.971 +/- 0.039 and stages A/B's 0.991-0.994 +/- 0.008), with real
   outlier scenarios dropping as low as 0.68-0.69 -- confirming this is a
   recurring failure mode across randomized conditions, not a one-off.
   Future-work fix identified, not implemented: adaptive persistence or a
   minimum-time-since-last-disturbance gate before allowing a new HOLD
   entry.
2. **The activity-index benefit is scoped to steady conditions, not noisy
   ones** (M12, D0.24): under sustained measurement noise (sigma=1.5W),
   HOLD never triggers at all (mean confidence stays below C_enter), so
   stages D/E degrade gracefully to match stage C exactly -- correct
   behavior, but means the headline activity-index number (0.104) should
   never be quoted without this noise-dependency caveat. M15 confirms the
   activity benefit IS real and general across randomized conditions
   (mean 0.191 +/- 0.101 activity index for D/E vs 1.0 for A/B/C), just
   smaller and more variable than the single steady-condition figure.
3. **PV panel remains a placeholder** (D0.10): no real datasheet has been
   supplied; all numeric results are only as good as this assumption until
   replaced.
4. **Boost converter ESR, MOSFET/diode part numbers, gate driver supply
   voltage, and safe D_min/D_max remain unknown** (D0.9): blocks M18-M19
   hardware work specifically, not simulation.

## Current best results

M22's master_summary.csv and headline figure are now the project's single
consolidated evidence base, built directly from M12/M13/M15 with no
hand-transcription. Headline numbers: activity index 1.0 -> ~0.10 (steady
conditions), efficiency variability cost under randomized conditions
(D/E std 0.055 vs A/B's 0.008), 52.0% local-peak trap rate under random
shading. M16's reassuring counterpoint remains valid too: PV parameter
uncertainty (+/-20%) barely affects any controller (>99.7% efficiency
throughout), since all controllers are closed-loop and never rely on the
model online. This picture (real benefit, two quantified limitations, one
reassurance on robustness to model mismatch) should anchor the report's
Results AND Discussion sections together.

## Known issues / open items (blocking or tracked)

1. **Not blocking, tracked:** No real PV panel datasheet. User has
   confirmed proceeding with the generic placeholder profile (D0.10);
   pv_model will be built parametrized so a real datasheet is a one-file
   swap later.
2. **BLOCKING for M18-M19 only (hardware power-up), not for simulation:**
   inductor/capacitor ESR, MOSFET/diode part numbers, gate driver Vdd
   voltage, exact current-sense amplifier part number/gain, and safe
   duty-cycle range (D_min/D_max) remain unknown from the schematic images
   supplied. None of these block M2-M17 simulation work, which now uses
   real L, C_in, C_out, shunt, and divider values.
3. Confidence-function thresholds are placeholders pending M8 sensitivity
   study — not yet justified experimentally.
4. RLS forgetting factor lambda is not yet chosen — pending M6 sensitivity
   study, not hardcoded to 0.98 per project instructions.

## Next milestone

All 28 milestones (M0-M28) have now been addressed at least once. What
remains, in priority order:

1. **M18-M21 (hardware)** — still BLOCKED pending MCU choice and the
   remaining hardware items (inductor/capacitor ESR, MOSFET/diode part
   numbers, gate driver supply voltage, safe D_min/D_max). This is the
   single biggest remaining piece of real work.
2. **The five gaps found at M28** (D0.36) — none urgent, but worth
   addressing if time allows before final submission: a stability-proof
   discussion, an embedded-arithmetic sensitivity note, a quick
   cross-check against the known ~95% hardware efficiency, one more
   literature re-check, and a confidence interval on the 52% trap rate.
3. **Finalize paper/draft_v1.md and report/final_report_v1.md** into v2
   once M18-M21 results exist, replacing the "PENDING" hardware sections
   with real data.

Awaiting user input (MCU choice / hardware part numbers) to proceed with
M18, or direction on which of the M28 gaps to prioritize in the meantime.
