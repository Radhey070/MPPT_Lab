"""
pv_model/parameters.py

Panel parameters. STATUS: PLACEHOLDER panel per docs/decision_log.md D0.10
(user confirmed proceeding without a physical panel). Every value here is
either from the placeholder datasheet-style profile in
docs/parameter_registry.md, a physical constant, or derived by
parameter_extraction.py. Swap PANEL dict contents for a real datasheet and
everything downstream recomputes automatically -- nothing else in this
project should hardcode panel numbers.
"""

# --- physical constants ---
Q = 1.602176634e-19        # elementary charge, C
K_B = 1.380649e-23         # Boltzmann constant, J/K
EG_REF = 1.12               # silicon bandgap at 298K, eV (used in I0(T) scaling)

# --- STC reference conditions ---
G_STC = 1000.0              # W/m^2
T_STC_C = 25.0               # deg C
T_STC = T_STC_C + 273.15     # K

# --- placeholder panel datasheet-style parameters (SOURCE: PLACEHOLDER, see
#     docs/parameter_registry.md and decision_log.md D0.10) ---
PANEL = {
    "name": "PLACEHOLDER_generic_36cell_monoSi",
    "Ns": 36,                # series cells
    "Voc": 21.6,              # V, at STC
    "Isc": 3.35,               # A, at STC
    "Vmpp": 17.8,             # V, at STC
    "Impp": 3.05,              # A, at STC
    "n": 1.3,                  # diode ideality factor, assumed (LITERATURE typical range)
    "alpha_Isc": 0.0005,       # 1/K, temp coeff of Isc (+0.05 %/C typical mono-Si)
    "beta_Voc": -0.0036,       # 1/K, temp coeff of Voc (-0.36 %/C typical mono-Si)
}

PANEL["Pmpp"] = PANEL["Vmpp"] * PANEL["Impp"]


def thermal_voltage(T_kelvin, Ns=PANEL["Ns"], n=PANEL["n"]):
    """Module thermal voltage n*Ns*k*T/q, in volts."""
    return n * Ns * K_B * T_kelvin / Q
