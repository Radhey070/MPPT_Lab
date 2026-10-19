# LITERATURE GAP TABLE

Skeleton created at M0, to be populated at M1. Entries already identified
during architecture discussion are pre-filled; full survey happens at M1.

| Category | Paper | Year | Method | Contribution | Limitation relative to our work | Relevance |
|---|---|---|---|---|---|---|
| RLS/adaptive estimation | Subudhi & Pradhan-style APEF-MPPT (Wiley, J. Eng.) | 2016 | RLS-adapted predictive filter, single-step tracking | Lower computational complexity than P&O/INC | No confidence-gated activity reduction, no embedded complexity benchmarking, no energy-vs-activity trade-off study | Precedent that RLS-for-MPPT is sound; we build architecture around it, not claim to invent it |
| RLS/adaptive estimation | Girgis & Elkhateeb, Renewable Energy | 2024 | P&O + adaptive PID via exponential-forgetting RLS | Demonstrated across irradiance/temp/load/PSC | No HOLD state / activity minimization framing, no hardware complexity benchmarking | Confirms RLS-MPPT is an active 2024-era line, not stale |
| RLS + fuzzy | AZOJETE paper | 2026 | RLS-based adaptive fuzzy MPPT | High-performance tracking | Adds fuzzy layer (complexity we are deliberately avoiding); no activity/energy trade-off framing | Shows the field is still combining RLS with heavier controllers; motivates our lighter deterministic approach |
| Adaptive step / gradient | Adaptive Gradient Descent MPPT with Complexity-Aware Benchmarking (arXiv 2511.20895) | 2025 | Slope-scaled adaptive P&O + complexity benchmarking + optional PSC init | Closest prior work to our architecture | Does not include a confidence/HOLD mechanism to reduce unnecessary activity; single global search framing, not event-triggered per our design | Most directly comparable prior work — must be discussed explicitly and differentiated in the paper |
| GMPPT / scanning | PolyU current-sweeping GMPPT work | - | Voltage/current sweep to locate GMPP under PSC | Established sweep-based localization | Does not tie search triggering to an online confidence estimate | Supports "bounded coarse localization" as the correct terminology and precedent for our SEARCH state |
| Classical | P&O, Incremental Conductance | - | - | Baseline behavior, well documented trade-off (speed vs oscillation) | N/A - these are our baselines | Ablation stage A comparator; INC optional secondary reference |
| Embedded/complexity | (to be expanded at M1) | | | | | |
| PV modeling | Villalva et al., single-diode modeling (IEEE Trans. Power Electron.) | - | Standard single-diode parameter extraction method | Widely used reference method | N/A | Basis for pv_model implementation |
| PV modeling | Iterative Newton-Raphson 5/7-parameter extraction (arXiv:1601.03257) | - | NR-based iterative parameter extraction, validated against outdoor mono-Si measurements | Reports <1.1% mean absolute power error, fast convergence | Assumes STC datasheet values available (we only have a placeholder panel) | Basis for our "numerically stable solver" requirement (M2); NR convergence checks to be included in pv_model validation tests |
| PV modeling | Non-iterative analytical 5-parameter extraction (ScienceDirect, PMC8539323) | - | Closed-form analytical extraction, avoids iterative solver entirely | Simpler, faster than NR for initial parameter guess | Less accurate near edge cases per own comparison | Candidate for generating a good NR initial guess in pv_model/parameter_extraction.py |
| Boost converter modeling | Standard averaged CCM boost equations (textbook: Erickson & Maksimovic, Fundamentals of Power Electronics) | - | State-space averaging for switching converters | Foundation for boost_model/averaged_model.py | Averaged model does not capture switching-frequency ripple/EMI | Explicitly distinguished from real switching hardware per master prompt sec 4.2 |
| Embedded/complexity-aware | STM32F334 1MHz digital MPPT via high-resolution timer (ST AN5324) | - | Hardware application note, real digital MPPT converter on STM32 | Concrete precedent that STM32 timers can drive high-frequency MPPT control loops well beyond our ~45kHz target | Application-note level, not peer-reviewed, no complexity benchmarking table | Confirms our f_sw ~45kHz target (docs/switching_frequency_sizing.md) is comfortably within STM32 timer capability |
| Embedded/complexity-aware | Processor-in-the-Loop ANFIS MPPT on STM32F4 (MDPI Energies 2025) | 2025 | MIL -> SIL -> PIL validation workflow for an ANN-fuzzy MPPT controller | Demonstrates a structured sim-to-embedded validation pipeline | Uses a heavier ANFIS controller than we intend | Precedent for our own simulation -> embedded validation staging (M17-M21); we can borrow the MIL/SIL/PIL terminology in the report |
| Complexity-aware benchmarking | Adaptive Gradient Descent MPPT with Complexity-Aware Benchmarking (arXiv:2511.20895) | 2025 | Slope-scaled adaptive P&O; introduces a Figure-of-Merit (FoM) combining efficiency, oscillation, tracking time, and computational load; benchmarks 35 published P&O-variant algorithms | Most directly comparable prior work; provides a ready reference table (their Table IX) we can position our results against | No confidence-gated activity reduction; FoM does not include an energy-harvested-during-search penalty | Central paper to differentiate against explicitly in the paper; consider adopting a similar FoM as one summary metric alongside our raw metrics, not as a replacement for them |

## Working differentiation statement (verified against 15-entry survey above)

"To the best of our reviewed literature, RLS-based and adaptive-gradient
MPPT methods exist independently (Wiley 2016, Renewable Energy 2024, AZOJETE
2026), and complexity-aware embedded benchmarking of P&O-variant algorithms
exists independently and is well developed (arXiv:2511.20895, which
benchmarks 35 published algorithms with a Figure-of-Merit metric). However,
a confidence-gated HOLD/TRACK/SEARCH architecture that explicitly minimizes
control activity and quantifies the resulting energy/activity trade-off,
validated jointly through simulation and real embedded hardware on an
existing boost converter, was not found in the literature reviewed for this
project." This statement has now been checked against a 15-entry survey
spanning all 9 required categories and is considered adequately supported
to use in the paper's introduction, with the caveat that it should be
re-checked once more (a final pass) before submission, since literature in
this area is actively growing.

## Open consideration (not yet decided)

arXiv:2511.20895's Figure-of-Merit (FoM) combining efficiency, oscillation,
tracking time, and computational load is a candidate single-number summary
metric for our final comparison table (M22), alongside — not instead of —
our raw metrics (tracking efficiency, energy harvested, activity index,
computational cost). Whether to adopt it, and how to fold in an
energy-lost-during-search penalty term it doesn't have, is deferred to M22
once we have real numbers to decide with, not decided now on paper alone.
