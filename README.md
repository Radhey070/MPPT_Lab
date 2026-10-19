# MPPT Lab

An interactive website for the supplied Confidence-Aware Adaptive MPPT project.

## Run locally

From this folder: `python -m http.server 8000 --directory dist`
Open `http://localhost:8000`. Use a web server rather than opening index.html directly: the simulator loads a module worker and JSON reference data.
No build step, package download, or external API is required. The hosted site runs the simulation in your browser.

## What is preserved

- Original project figures and CSVs under `dist/data` are unchanged.
- Original Python controller, PV and boost source is retained in `source-model`.
- The report baseline uses traces reproduced by running that Python code.
- User-modified conditions recompute using a JavaScript translation of the same single-diode PV equations, algebraic boost coupling, five algorithms and state machine.
- Seeded standard-normal arrays are exported from NumPy for repeatable browser noise runs. Long noisy RLS trajectories can diverge slightly due to floating-point evaluation; the original 8-seed report table remains authoritative.
- Browser partial-shading comparisons apply the project's shaded plant to all five algorithms. The supplied M14 validation exercises the full controller specifically.

## Model boundaries

These MPPT experiments use quasi-static, ideal-lossless CCM boost coupling, not switched transients. Circuit ON/OFF selection illustrates the conduction topology; displayed numbers are cycle averages. There is no invented switching ripple, loss estimate or hardware verification. Cin=320 µF, L=220 µH, Cout=671 µF, fPWM=45 kHz are original project values. ESR is unknown. The fitted panel is the project's placeholder 36-cell mono-Si profile.

The circuit uses applied duty D(k), while the duty-command graph follows the original controllers' returned D(k+1). Partial shading includes three series substrings and bypass clamps in the PV model. In SEARCH, the actual probe duty is used for circuit measurements, including the last probe before reseeding to the best duty.

## Verification

`node scripts/validate.mjs`

Checks 25 Python operating points, ideal power balance, five clean baseline metrics, dynamic boundedness, 15-probe SEARCH termination, and the known local-peak trap. Baseline reference data can be regenerated with `python scripts/export_reference.py` using NumPy and SciPy. Source figures/tables are not overwritten by this export.

Original report metrics are always available in Report results. The noisy table is an average over 8 seeds; an interactive noisy run represents the displayed single seed. The original M10 noise-burst figure is nondeterministic because its source script supplies no seed.

## Files

- `dist/model.js`: PV plant, RLS, confidence, controllers, metrics.
- `dist/worker.js`: simulation off the UI thread and reference preset selection.
- `dist/app.js`: interactive plots, parameters, cursor, circuit readings, CSV export.
- `dist/index.html`, `dist/style.css`: responsive light laboratory interface.

## V2: engineering evidence

- Validation runs a fixed, explicitly specified 100-run / six-scenario benchmark in a separate worker. Noisy experiments use NumPy seeds 0–7 and display population SD, not confidence intervals. Full SEARCH retains the original noiseless-probe behavior, disclosed in the interface.
- Converter lab integrates the original lossless averaged ODE under a constant voltage source using RK4. It starts from equilibrium and steps duty at 50 ms. It is separate from the original quasi-static controller comparisons. A zero/negative current flags the CCM model's physical limitation. Two-state 1% settling is measured over the remaining 250 ms window.
- Live comparisons display ≥99% acquisition for five consecutive samples, efficiency/activity trade-offs, and finite-value, duty-limit, ideal-power-balance and steady-state CCM checks.
- Guided viva presets and validated JSON save/load support repeatable demonstrations. JSON records contain settings and metrics, never private application data.
- Existing figures, reference traces, original controller implementations, and report CSVs are unchanged.

Additional validation: `node scripts/validate-upgrade.mjs`.
The default converter transient was also checked against independent SciPy solve_ivp integration at rtol=1e-10, with maximum state deviation 7.4e-9 or less. Step halving gives agreement better than 1e-10. Numerical and source checks were completed; interactive browser visual QA was unavailable in this environment.
