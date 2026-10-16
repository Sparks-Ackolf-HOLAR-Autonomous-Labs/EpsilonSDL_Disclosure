# Solid-state force field rung and kMC applicability: results

Run 2026-10-10, 21:05 to 21:30 UTC, on the DGX (MACE-MP-0 medium on the GB10 GPU; kMC on
one core). Predictions were registered before any data (PREDICTION.md).
Numbers: `results/analysis.json`. Figure: `results/fig_cost_vs_size.png`.

## Question

The training-centralization axis of the centralization surface is flat because the cost
of a DFT job is predicted mostly by the public size of the compound, which the research
party already knows. A new rung gives a shared performance logbook value only if its job
cost depends on something compound size does not reveal.

## Graded predictions

| Prediction | Measured | Verdict |
| --- | --- | --- |
| A1: size explains MACE MD cost, R^2 >= 0.95 | R^2 = 0.65 (90 jobs) | fail, see note |
| A2: MACE lattice constant within 3% of our PBE, >= 25 of 29 | 28 of 29 (mean 0.7%, max 3.2%) | pass |
| A3: sign of E(1T) - E(2H) agrees with PBE, >= 12 of 15 | 14 of 14 (HfSe2 2H has no PBE value) | pass |
| B1: vacancy hop barriers span >= 0.3 eV | 0.00 to 1.01 eV | pass |
| B2: size explains kMC cost, R^2 < 0.90 | R^2 = 0.19 (60 runs); 0.66 without 1T Mo/W | pass |
| B3: size + barriers explain kMC cost, R^2 > 0.90 | R^2 = 0.95; 0.99997 without 1T Mo/W | pass (partly by construction) |

Reference, measured QE F2 wall time on the 1x1 campaign cells against electron count:
R^2 = 0.86, cost spread x8.9, of which x2.8 is left after size.

## Test A: force field suited to the solids

- **As a pre-screen rung, MACE-MP-0 is accurate enough.** In-plane lattice constants match
  our PBE values to 0.7% on average, and the 1T versus 2H preference has the right sign for
  every composition (group-IV metals prefer 1T, Mo and W prefer 2H). The energy differences
  are 1.4 to 50 times smaller than PBE (ZrTe2 is almost degenerate in MACE), so the force field ranks phases correctly
  but should not be used to report phase energies.
- **A1 fails, but not in the way that matters.** A 200-step MD run costs 2.2 to 5.9 s
  for 12 to 96 atoms: at this size the GPU cost is set mostly by fixed per-step overhead,
  so the total spread is only x2.7. Of the scatter left after size, 25% follows the
  compound and 75% is run-to-run noise; the compound-specific part is about 8% of cost.
  A shared logbook of force-field MD costs would therefore carry almost nothing.
- **Relaxations are the one compound-specific cost.** The number of relaxation steps runs
  from 22 to 68 (2H bilayers need more), which size explains poorly (R^2 = 0.23, spread
  x4.9). The absolute cost is under 2 s per compound, so this information has no value
  worth disclosing.
- Conclusion for the multi-party question: a force-field rung adds a useful low-cost
  pre-screen but does not give the training axis a slope.

## Test B: kMC applicability

Chain: MACE-MP-0 nudged elastic band (NEB) barrier for an in-plane chalcogen-vacancy hop
and the adjacent divacancy binding energy (4x4 supercells, 30 compounds, all NEBs
converged) feeding our rejection-free kMC (`vac_kmc.c`) of 2% chalcogen vacancies annealed
at 1000 K for 1 s, on 24x24 and 48x48 lattices. Runs stopped at 200,000 events and the
cost to reach 1 s was projected linearly.

- **Cost of the same physical task spans six decades across compounds** (x1.8 million),
  while doubling the lattice edge raises cost by only x14. Size explains 19% of the cost
  variation; adding the hop barrier and binding energy explains 95%.
- **Robustness:** the 1T phases of Mo and W are dynamically unstable (they distort to 1T'),
  and their near-zero barriers (WTe2 1T: 0.00 eV) reflect an unstable host. Without them,
  size still explains only 66% and leaves x212 unexplained; barriers explain the rest.
- **What this means for the parties.** In kMC, two compounds of the same size can differ in
  cost by orders of magnitude, and the reason (the rate catalogue) is held by whoever
  computed the barriers. A shared performance logbook then carries information the
  research party does not have, which is the condition for the training axis to get a
  slope. It also supports splitting the work among a barrier supplier, a process modeller
  and the computing centre, with barriers disclosed at graded resolution.
- **Science output (screening level only):** divacancy binding is repulsive (positive) in
  most compounds; it is attractive only in 1T MoS2, MoSe2 and WSe2, where vacancies
  cluster fully in the kMC runs.

## Limitations

- **The barriers are force-field barriers, and they are too low.** MACE-MP-0 gives 0.90 eV
  for the S-vacancy hop in 2H MoS2, while published PBE calculations report about 2.3 eV
  (for example Komsa et al., Phys. Rev. Lett. 109, 035503, 2012, doi:10.1103/PhysRevLett.109.035503).
  Foundation potentials are known to soften energy surfaces. The applicability verdict
  needs only the spread between compounds, but absolute kMC times are not physical, and a
  DFT NEB check on a few compounds (CHPC guest partition, not the DGX) is needed before
  any kMC result is reported as science.
- **B3 is close to an identity.** The kMC cost to a fixed simulated time is set by the
  total event rate, which is a function of the barriers. The empirical content of test B
  is B1 (how far barriers spread between compounds) plus the measured cost per event.
- The 2H cells are the campaign's AA' bilayers (6 atoms), not single layers; the vacancy
  sits on the outer chalcogen plane.
- The kMC code updates rates locally but selects events by a linear scan, so the cost per
  event grows with the number of vacancies. Production codes (SPPARKS) use a tree search;
  this would reduce the size term and strengthen B2.
- Single seed per kMC run; the cost projection assumes steady event rates after 200,000
  events.

## Possible extensions

1. DFT NEB (QE) for the hop barrier in about 6 compounds that span the MACE range, on a
   CHPC guest partition, to check whether the spread between compounds survives.
2. If it does: add a kMC rung after F2 in the twin and re-run the centralization surface
   with kMC job costs, which is where the training axis should gain a slope.
3. Three-party contract design (barrier supplier, process modeller, computing centre) with
   barriers disclosed at 0.1 eV or rank-only resolution, and a timing-leakage audit,
   because kMC wall time points to the compound even more strongly than DFT wall time.
