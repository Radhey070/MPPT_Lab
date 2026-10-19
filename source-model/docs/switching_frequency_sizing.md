# SWITCHING FREQUENCY SIZING

Since the PCB's gate driver (UCC27517A) takes PWM externally via J3, f_sw is
a controller design choice, not a fixed hardware parameter. Sized here from
the real L and C_out values extracted from the schematic (see
parameter_registry.md), not assumed.

## Method

Standard boost-converter design equations, ideal (lossless) approximation:

- Steady-state: D = 1 - Vin/Vout
- Inductor ripple: dIL = Vin * D / (L * fsw)
- Output voltage ripple (capacitive component only, ESR unknown so this is a
  lower bound, not the full ripple): dVout = Iout * D / (C_out * fsw)

Design target: inductor ripple current at 25% of typical input current
(standard boost design guideline, trades core loss / EMI against inductor
size — since L is fixed by the existing PCB at 220uH, this sets fsw).

## Inputs used

- L = 220 uH, C_out = 671 uF (from schematic, D0.9)
- Vin = Vmpp = 17.8 V, Iin = Impp = 3.05 A (placeholder PV panel, D0.10 —
  will be recomputed automatically once a real panel is supplied, since this
  script is parametrized)

## Result (three candidate output bus voltages)

| Vout (V) | Duty D | fsw (kHz) | IL ripple (A) | IL ripple (%) | Vout ripple, cap-only (mV) |
|---|---|---|---|---|---|
| 24 | 0.258 | 27.4 | 0.76 | 25.0 | 31.8 |
| 30 | 0.407 | 43.2 | 0.76 | 25.0 | 25.4 |
| 36 | 0.506 | 53.6 | 0.76 | 25.0 | 21.2 |

## Recommendation

Target Vout = 30 V (mid-range candidate, plausible small-battery/bus
voltage), f_sw ≈ 45 kHz, giving D ≈ 0.41 at the assumed MPP operating point.
UCC27517A (rated for multi-MHz switching) has enormous margin at this
frequency — driver capability is not a constraint here.

This is a STARTING POINT, not final: once ESR values are known (pending
inductor/capacitor part numbers) this ripple estimate should be redone
including ESR's contribution to output ripple, which is often larger than
the pure-capacitive term at these frequencies. Flagged in
parameter_registry.md as an open item.

Duty range implied by the three candidates (0.26-0.51) is a reasonable
planning range, but the PCB's actual safe D_min/D_max (component voltage
ratings, core saturation limits) is still unverified and must be established
empirically at low power before any full-power hardware test (M18-M19
hardware safety rule).
