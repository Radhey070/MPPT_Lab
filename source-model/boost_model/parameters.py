"""
boost_model/parameters.py

Real values extracted from the PCB schematic images (docs/decision_log.md
D0.9, docs/parameter_registry.md). ESR and component part numbers remain
UNKNOWN and are NOT fabricated -- the averaged model defaults to lossless,
with an explicit optional loss term reserved for later.
"""

# from schematic, SOURCE: SCHEMATIC, D0.9
L = 220e-6              # H, main boost inductor L1
C_IN = 320e-6            # F, input capacitor C3
C_OUT = 671e-6            # F, output caps C11+C12+C13+C14 in parallel

R_SHUNT_IN = 0.006         # ohm, effective (R3 || R4, two 0.012 ohm resistors)
R_SHUNT_OUT = 0.006        # ohm, effective (R14 || R15)
K_V_SENSE = 0.0196          # voltage divider ratio, both input and output sense chains

# design choice, sized in docs/switching_frequency_sizing.md (D0.11)
F_SW = 45e3               # Hz, switching frequency (externally set via PWM)

# still UNKNOWN, NOT fabricated -- code must treat None as "no loss model"
R_L_ESR = None              # inductor ESR
R_C_ESR = None              # capacitor ESR

# simulation-only software duty limits, distinct from a hardware-verified
# safe D_min/D_max (open item for M18/M19)
D_MIN_SIM = 0.10
D_MAX_SIM = 0.80

# representative load range for CCM/validation checks, implied by the
# placeholder PV panel's Pmpp ~= 54 W (see pv_model/parameters.py) and a
# target ~30V bus (docs/switching_frequency_sizing.md), NOT a real spec
R_LOAD_TYPICAL = 30.0 ** 2 / 54.29   # ohm, R = Vout^2 / P at the target point
