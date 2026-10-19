# ASSUMPTIONS REGISTER

Assumptions made in the absence of supplied information. Each will be
revisited when real data arrives.

1. **PV module**: no synopsis file or datasheet was supplied in this
   conversation. A generic 36-cell mono-Si module profile is used as a
   PLACEHOLDER (see parameter_registry.md) purely to keep the pipeline
   exercisable. All resulting numbers are illustrative until replaced.
2. **Boost converter**: existing PCB is assumed to operate in continuous
   conduction mode (CCM) for the tested load range, per the original project
   description. L, C, ESR, switching frequency are UNKNOWN and not
   fabricated — generic representative values will be used only for
   simulation-only figures, clearly captioned, and never used for hardware
   decisions.
3. **MCU choice**: not yet made between STM32 and ESP32. Will ask before
   M18 unless a clear technical reason emerges earlier (e.g. if firmware
   design reveals one is clearly better suited to the sampling-rate/ADC
   requirements).
4. **Load model**: simple resistive load assumed for initial simulations
   unless told otherwise (e.g. battery charging profile).
5. **Ambient conditions for Monte Carlo**: irradiance range 200-1100 W/m^2,
   temperature range 15-55 C, chosen as representative outdoor operating
   bounds — to be revisited if the actual test environment differs.
6. **"Meaningful duty-cycle update"** (for the Activity Index metric) is
   provisionally defined as any commanded |delta D| above the minimum
   representable step size given the MCU's PWM timer resolution (exact
   value pending MCU choice) — refined at M18, using a simulation-only
   proxy (e.g. 0.1% duty) until then.

These are logged, not hidden, per the project's research-claim-discipline
rule.
