# PARAMETER REGISTRY

Every parameter used anywhere in this project must be traceable to one of:
`DATASHEET`, `MEASURED`, `LITERATURE`, or `PLACEHOLDER (needs replacement)`.
No parameter may silently change source category without a note in the
decision log.

## PV module (single-diode model)

| Parameter | Symbol | Value | Source | Notes |
|---|---|---|---|---|
| Open-circuit voltage | Voc | 21.6 V | PLACEHOLDER | generic 36-cell mono-Si profile; replace with datasheet |
| Short-circuit current | Isc | 3.35 A | PLACEHOLDER | replace with datasheet |
| Voltage at MPP | Vmpp | 17.8 V | PLACEHOLDER | replace with datasheet |
| Current at MPP | Impp | 3.05 A | PLACEHOLDER | replace with datasheet |
| Number of series cells | Ns | 36 | PLACEHOLDER | replace with datasheet |
| Temp coeff of Voc | beta_Voc | -0.36 %/C | LITERATURE (typical mono-Si) | replace with datasheet if available |
| Temp coeff of Isc | alpha_Isc | +0.05 %/C | LITERATURE (typical mono-Si) | replace with datasheet if available |
| Series resistance | Rs | 0.34 ohm | derived at init via standard iterative fit | recompute once real Voc/Isc/Vmpp/Impp known |
| Shunt resistance | Rsh | 415 ohm | derived at init via standard iterative fit | recompute once real Voc/Isc/Vmpp/Impp known |
| Diode ideality factor | n | 1.3 | LITERATURE (typical range 1.0-1.5) | may be refined by curve fit against real I-V data |
| STC irradiance | G_stc | 1000 W/m^2 | STANDARD | |
| STC temperature | T_stc | 25 C | STANDARD | |

**User-confirmed assumption [M0.5]:** no physical panel is available yet.
Proceeding with the generic profile above as the assumed panel for all
simulation work, chosen to be broadly representative of a ~55-60 W, ~18-22V
Vmpp module (a common size for boost-converter MPPT demonstration rigs).
This choice is not arbitrary re: the hardware — it keeps V_pv comfortably
inside the boost converter's input range implied by C_in=320uF and the
sensing chain, while staying low enough that a bench PV simulator or a
small real panel purchased later can plausibly match it without redesigning
the sensing/divider chain. The PV model code is fully parametrized
(pv_model/parameters.py, once written at M2), so swapping in a real
datasheet later is a one-file change, not a rework.

## Boost converter (existing PCB) — updated from schematic images, [M0.5]

| Parameter | Symbol | Value | Source | Notes |
|---|---|---|---|---|
| Inductance | L | 220 uH | SCHEMATIC (L1) | confirmed from main circuit schematic |
| Output capacitance | C_out | 671 uF (10+330+330+1 uF, parallel) | SCHEMATIC (C11-C14) | four caps in parallel |
| Input capacitance | C_in | 320 uF | SCHEMATIC (C3) | |
| Inductor ESR | R_L | UNKNOWN | MISSING | inductor part number not legible on schematic; needed for loss modeling |
| Capacitor ESR | - | UNKNOWN | MISSING | capacitor part numbers not legible; needed for ripple/loss modeling |
| Switching frequency | f_sw | NOT FIXED BY PCB | DESIGN CHOICE | PWM is driven externally via J3 into gate driver U2 (UCC27517A); f_sw is a controller design decision, to be set from L/C ripple sizing at M3, not a hardware constraint |
| Gate driver | - | UCC27517A | SCHEMATIC (U2) | non-inverting, single channel; input logic-level compatibility with 3.3V MCU PWM to be confirmed against datasheet before hardware power-up |
| Gate drive supply (Vdd) | - | UNKNOWN | MISSING | supplied externally via J8; voltage not shown on schematic |
| Gate turn-on resistor | R7 | 10 ohm | SCHEMATIC | |
| Gate turn-off path | R6, D1 | 4.7 ohm + diode | SCHEMATIC | asymmetric turn-on/turn-off network |
| Gate pulldown | RB | 10 kohm | SCHEMATIC | |
| Output diode snubber | R9, C8 | 10 ohm, 470 pF | SCHEMATIC | across D3 |
| Switch-node snubber/clamp | R10, C7, D2 | 1 kohm, 470 pF | SCHEMATIC | |
| Input current shunt (effective) | R_sh_in | 0.006 ohm (R3 || R4, 0.012 ohm each) | SCHEMATIC | |
| Output current shunt (effective) | R_sh_out | 0.006 ohm (R14 || R15, 0.012 ohm each) | SCHEMATIC | |
| Voltage sense divider ratio (in and out) | k_v | 0.0196 (2k / (100k+2k)) | SCHEMATIC | identical topology both sides; unity-gain buffered, RC filtered |
| Current sense amplifier | IC1, IC2 | likely TI INA1xx family (SOT23-8, pinout matches) | INFERRED from pinout, NOT CONFIRMED | exact part marking not legible; gain unknown, treat as open item |
| Measured efficiency | eta_meas | ~95% | MEASURED (per user, prior work) | condition (load, Vin, Vout) not yet specified |
| MOSFET/diode part numbers | - | UNKNOWN | MISSING | not legible on schematic; needed for loss modeling |
| Duty cycle range (safe) | D_min, D_max | UNKNOWN | MISSING | must still be established empirically at low power before any full-power hardware run |

**Still required from user before hardware power-up (M18-M19):** exact
inductor/capacitor part numbers or datasheets (for ESR), MOSFET/diode part
numbers (for loss modeling), gate driver Vdd voltage, and confirmation of
current-sense amplifier part number/gain. None of these block simulation
work (M2-M17), which now uses the REAL L, C_out, C_in, and shunt/divider
values above instead of generic placeholders.

## Controller / estimator parameters (all pending their own milestones)

| Parameter | Symbol | Status |
|---|---|---|
| RLS forgetting factor | lambda | PENDING M6 sensitivity study |
| RLS initial covariance | P(0) | PENDING M6, standard large-value initialization to be justified |
| Gradient step gain | eta | PENDING M7 |
| Confidence thresholds | C_hold, C_search | PENDING M8 sensitivity study |
| Persistence count | M | PENDING M9, chattering-avoidance study |
| Search sweep resolution | N_steps | PENDING M10, trades search time vs. localization accuracy |

## Embedded hardware target

| Item | Value | Status |
|---|---|---|
| MCU family | STM32 or ESP32 | Not yet chosen between the two — will ask before M18 |
| Specific part | UNKNOWN | pending MCU choice |

This registry is a living document. Every time a placeholder is replaced with
a real value, log the change in `docs/decision_log.md` with the date/context.
