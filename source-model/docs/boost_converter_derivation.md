# BOOST CONVERTER — ANALYTICAL DERIVATION (M3)

Derived analytically while the execution sandbox was unavailable, then
implemented and numerically checked once it returned. This file is the
paper-ready derivation; boost_model/*.py is the implementation of it.

## 1. Switching-state equations

Two subintervals per switching period T_sw = 1/f_sw.

**Switch ON, duration D*T_sw** (MOSFET conducting, D3 reverse-biased):

    L * diL/dt = Vin
    C_out * dVout/dt = -Vout/R_load

**Switch OFF, duration (1-D)*T_sw** (MOSFET off, D3 conducting):

    L * diL/dt = Vin - Vout
    C_out * dVout/dt = iL - Vout/R_load

These are the real, physical switched equations -- everything below is
derived from them.

## 2. CCM state-space averaged model

Weight each subinterval by its duty fraction and sum (standard state-space
averaging, valid only under the CCM assumption -- see section 4):

    L * diL/dt = Vin - (1-D)*Vout
    C_out * dVout/dt = (1-D)*iL - Vout/R_load

Nonlinear (D multiplies the states). This is a design/analysis tool for the
AVERAGE behavior over one switching period, not a claim that real inductor
current is smooth.

## 3. Steady-state relationship

Set diL/dt = 0, dVout/dt = 0:

    Vout/Vin = 1/(1-D)                    (ideal boost relation)
    IL = Vout / [(1-D)*R_load]

Lossless result, derived here from the averaged model rather than assumed.

## 4. CCM boundary condition

Peak-to-peak inductor ripple during the ON interval:

    dIL = Vin*D / (L*f_sw)

CCM requires IL_avg > dIL/2. Substituting the steady-state relations gives
the critical resistance:

    R_crit = 2*L*f_sw / [D*(1-D)]

R_load < R_crit -> CCM (averaged model in section 2 valid).
R_load > R_crit -> DCM (a different, unimplemented averaged model would be
needed; section 2's model does NOT apply).

## 5. Duty-cycle to operating-point relationship

Effective input resistance the converter presents to the PV source
(lossless steady state, Pin=Pout: Vin*Iin = Vout^2/R_load, substitute
Vout=Vin/(1-D)):

    R_in,effective(D) = (1-D)^2 * R_load

This is monotonically DECREASING in D (for fixed R_load, in CCM) -- proof
that duty-cycle control moves the PV operating point down its I-V curve in
a well-behaved, single-direction way. This is the formal justification for
decision D0.2 (regressing RLS directly in duty-space): P_pv(D) is
well-posed and single-peaked near the MPP for a fixed load precisely
because R_in,effective(D) is monotonic. This proof did not exist before
this derivation and should be cited in the report as the mathematical
grounding for D0.2, not just an implementation convenience.

## 6. Known vs. placeholder quantities

| Quantity | Status |
|---|---|
| L=220uH, C_out=671uF, C_in=320uF | REAL, from schematic (D0.9) |
| f_sw=45kHz | REAL design choice, sized in switching_frequency_sizing.md (D0.11) |
| Vout=Vin/(1-D), R_crit, R_in,effective formulas | DERIVED here, standard technique |
| R_L_ESR, R_C_ESR | UNKNOWN -- lossless model used as primary; loss-inclusive form written below for later, NOT used with a guessed value |
| R_load operating range | Not specified by user; using a representative range implied by the placeholder PV panel's Pmpp ~ 54W until a real load spec is given |

**Loss-inclusive form (ready for later, unused now):** adding R_L_ESR in
series with L: `L*diL/dt = Vin - (1-D)*Vout - iL*R_L_ESR`, changing the
steady-state relation to an efficiency-degraded form. Implemented as an
optional parameter in the code, defaulting to off (None) until real ESR is
known -- never silently defaulted to a guessed nonzero value.

## 7. Mathematical issues flagged before implementation (all now checked below)

1. CCM assumption must be checked numerically against the actual expected
   load, not just asserted.
2. Averaging validity requires f_sw >> LC corner frequency f_0 =
   1/(2*pi*sqrt(L*C_out)) -- must be computed, not estimated by hand.
3. R_in,effective's lossless derivation should carry a caveat that real
   (lossy) conditions add efficiency-dependent correction terms.
4. The R_crit derivation compresses an algebraic step (substituting the
   steady-state relation into the ripple condition) -- re-derived carefully
   in code comments (boost_model/averaged_model.py) rather than left as a
   hand-wave.

## 8. Validation checks (results in boost_model/validation.py output)

1. Steady-state check: averaged ODE converges to Vout=Vin/(1-D).
2. Power balance: Vin*IL == Vout^2/R_load at steady state (lossless, exact).
3. CCM boundary: R_crit(D) computed across D in [0.1, 0.8], confirm planned
   R_load stays inside CCM.
4. Averaging-validity: f_sw / f_0 ratio computed and reported.
5. Switched-model cross-check: raw switching-cycle simulation compared
   against averaged-model prediction; ripple visualized explicitly.
6. Duty-limit enforcement: D clipped to [D_MIN_SIM, D_MAX_SIM], D=1 never
   reached (singularity in Vout=Vin/(1-D)).
7. R_in,effective monotonicity: numerically confirmed decreasing in D.
