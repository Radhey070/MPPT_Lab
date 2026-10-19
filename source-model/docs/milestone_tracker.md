# MILESTONE TRACKER

Status legend: [ ] not started, [~] in progress, [x] complete, [!] blocked

| ID | Milestone | Status | Notes |
|----|-----------|--------|-------|
| M0 | Project initialization | [x] | repo, docs, parameter registry, trackers created |
| M1 | Literature and research-gap foundation | [x] | 15-entry survey across 9 categories, differentiation statement verified |
| M2 | PV mathematical model | [x] | 9/9 automated checks passed; see docs/decision_log.md D0.13 |
| M3 | Boost converter mathematical model | [x] | derived during outage (docs/boost_converter_derivation.md), implemented + 10/10 checks pass after fixing an underdamped-settling-time bug, see D0.14 |
| M4 | Baseline P&O | [x] | 5/5 checks pass after fixing an import collision and a controller-logic bug, see D0.16 |
| M5 | VSS-P&O | [x] | ablation stage B; 7/7 checks pass after fixing a gain-calibration bug, see D0.17 |
| M6 | Duty-space RLS estimator | [x] | 7/7 checks pass, standalone/synthetic per master prompt sec 18; see D0.18 |
| M7 | RLS-VSS controller | [x] | ablation stage C; 6/6 checks pass after fixing a sign issue (caught pre-emptively), an unfair-test bug, and a lambda/closed-loop mismatch; important trade-off finding motivating M9, see D0.19 |
| M8 | Confidence metric | [x] | 7/7 checks pass; found+fixed a real RLS-VSS windup bug along the way, see D0.20/D0.21 |
| M9 | HOLD/TRACK state machine | [x] | ablation stage D; 8/8 checks pass after fixing a premature-HOLD bug caught by inspecting the figure, see D0.22 |
| M10 | Bounded SEARCH | [x] | 8/8 checks pass, SEARCH gate learned from M9's lesson applied proactively, see D0.23 |
| M11 | Full controller | [x] | already satisfied by M10's full_controller.py -- SEARCH had to be built integrated with HOLD/TRACK, not standalone, see D0.23 |
| M12 | Ablation study A-E | [x] | central claim quantified: activity index 1.0 -> 0.104 (clean), graceful degradation to stage C under sustained noise; see D0.24 |
| M13 | Dynamic-condition experiments | [x] | E02/E03/E04/E15 across all 5 controllers; found a genuine, important limitation under rapid disturbances, see D0.25 |
| M14 | Partial-shading experiments | [x] | multi-peak model built and validated; found a fundamental architecture limitation (permanent local-peak trapping), see D0.26 |
| M15 | Monte Carlo validation | [x] | N=60 standard + N=25 shading; sharpened both known limitations with real statistics (52% shading trap rate!), see D0.27 |
| M16 | Parameter uncertainty | [x] | PV uncertainty negligible (>99.7% eff at +/-20%); boost L/C uncertainty scoped correctly to M3 only; see D0.28 |
| M17 | Visualization/dashboard | [x] | MP4+GIF animation and static storyboard fallback built, all 3 states visible, see D0.29 |
| M18 | Embedded implementation | [!] | blocked pending MCU choice + PCB specs |
| M19 | Hardware calibration | [!] | blocked pending M18 and safety checklist |
| M20 | Hardware experiments | [!] | blocked pending M19 |
| M21 | Simulation vs hardware | [!] | blocked pending M20 |
| M22 | Final statistical analysis | [x] | master_summary.csv + headline figure built by re-running each source milestone directly, see D0.30 |
| M23 | Paper | [~] | draft v1 written (11 sections, all numbers cross-verified against source tables), Hardware Validation section correctly left PENDING; see D0.31 |
| M24 | Final project report | [~] | draft v1 written (18 sections, reuses M23's verified numbers), hardware chapter descriptive-only (no fabricated results); see D0.32 |
| M25 | Presentation | [x] | 20-slide content written in chat (v2, supersedes pre-M12 outline), all numbers verified; see D0.33 |
| M26 | Competition/demo package | [x] | success-case + honest-limitation demo clips, presenter script, one-command deterministic rebuild; see D0.34 |
| M27 | Viva preparation | [x] | Q&A across 6 audit perspectives + quick-facts cheat sheet, all grounded in real project results; see D0.35 |
| M28 | Final audit | [x] | regression check (13 scripts, zero discrepancies) + 5 genuine gaps found and disclosed; see D0.36 |

Hardware milestones (M18-M21) are marked blocked, not skipped — they will be
unblocked as soon as MCU choice is confirmed and PCB specs are supplied. This
is intentional and follows the hardware safety rule: no wiring/power
recommendations before those inputs exist.
