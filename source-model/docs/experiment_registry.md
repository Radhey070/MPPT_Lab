# EXPERIMENT REGISTRY

Every experiment gets an ID, objective, controllers involved, parameters,
status, result summary, and conclusion. Populated as experiments run;
entries below are registered but NOT YET RUN (status: PENDING) as of M0.

| ID | Objective | Controllers | Depends on | Status |
|----|-----------|-------------|------------|--------|
| E01 | Baseline P&O under constant irradiance — sanity check | A | M2, M3, M4 | PENDING |
| E02 | Irradiance step response | A, B, C, E | M4-M11 | PENDING |
| E03 | Rapid multi-step irradiance variation | A, B, C, E | M4-M11 | PENDING |
| E04 | Temperature variation | A, B, C, E | M4-M11 | PENDING |
| E05 | Measurement noise: finite-difference slope vs RLS slope | B, C | M5, M6 | PENDING |
| E06 | Converter transient effect on RLS slope validity | C | M6, M7 | PENDING |
| E07 | PV/converter parameter uncertainty (+/-5/10/20%) | A-E | M11 | PENDING |
| E08 | Partial shading, multi-peak P-V curve (simulation) | A-E | M11 | PENDING |
| E09 | Event-triggered search — confirm no periodic scanning in E | E | M10, M11 | PENDING |
| E15 | Load step variation (added at M13 to match the milestone's stated "irradiance, temperature, load, noise" scope -- no E-number existed for this before) | A, B, C, D, E | M4-M11 | PENDING |
| E10 | Energy harvested E = integral P dt, identical profiles | A-E | M11 | PENDING |
| E11 | Monte Carlo, N=50-100 randomized scenarios | A-E | M11 | PENDING |
| E12 | Embedded execution time / RAM / flash | B, C, E (min. set) | M18 | PENDING (hardware-blocked) |
| E13 | Hardware validation vs simulation | A, E (min. set) | M18-M20 | PENDING (hardware-blocked) |
| E14 (ablation) | A vs B vs C vs D vs E, identical conditions | A-E | M12 | PENDING |

Each entry will be expanded into its own file under `experiments/experiment_XX/`
containing: objective, exact parameters/seed, controller config, raw results,
figures, and a written conclusion, once run.

Metrics to be computed per experiment (defined formally in
`docs/metrics_definitions.md`, to be written before E01 runs):
tracking efficiency, settling/convergence time, power ripple, energy
harvested, activity index, search energy loss (where applicable),
computational cost (E12 only).
