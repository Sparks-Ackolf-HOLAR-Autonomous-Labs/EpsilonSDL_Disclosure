# Registered predictions: solid-state force field rung and kMC applicability

Registered 2026-10-10 about 21:10 UTC, before any force-field or kMC data existed.
Two tests are run: a force field suited to solids, and a kMC applicability test.

## Question

The training-centralization axis of the centralization surface is flat because job cost
in the DFT ladder is predicted almost entirely by public compound size (RESULTS section 7:
own information R^2 = 0.986). A new method only gives the shared logbook value if its job
cost depends on something compound size does not reveal. Both tests measure that.

## Test A: force field suited to the solids (MACE-MP-0, medium, on the DGX GPU)

Jobs per compound (30 CC0 MX2 prototypes): in-plane cell relaxation of the 1x1 cell,
then a 200-step NVT MD run on 2x2, 3x3 and 4x4 supercells.

- A1 (cost): R^2 of log(job wall time) on log(atom count) >= 0.95 for MD jobs.
  Prediction: PASS, so a force-field rung alone keeps the training axis flat.
- A2 (accuracy as a pre-screen rung): in-plane lattice constants within 3% of our PBE
  values (QE F2, outcomes.jsonl) for at least 25 of 29 compounds. Prediction: PASS.
- A3 (accuracy): sign of E(1T) - E(2H) per formula unit agrees with PBE for at least
  12 of 15 compositions. Prediction: PASS.

## Test B: kMC applicability

MACE-MP-0 nudged elastic band (NEB) barrier for an in-plane chalcogen-vacancy hop and the
adjacent divacancy binding energy, per compound (4x4 supercells). These feed a lattice
kMC (rejection-free, Bortz-Kalos-Lebowitz) of chalcogen-vacancy diffusion and clustering
on the chalcogen sublattice, run to a fixed simulated annealing time at 1000 K on lattice
sizes L = 24 and 48.

- B1 (barrier spread): hop barriers across the compounds span at least 0.3 eV.
  Prediction: PASS.
- B2 (the applicability test): R^2 of log(kMC cost to reach the target time) on public
  size descriptors (log lattice sites, log electrons per formula unit) is below 0.90.
  Prediction: PASS (size does not predict kMC cost), so a shared logbook carries
  information the research party does not have, and the training axis can get a slope.
- B3: adding the hop barrier as a descriptor raises R^2 above 0.90. Prediction: PASS.

## Reference (already measured, not a prediction)

R^2 of log(QE F2 wall time) on log(electrons) over the 29 measured 1x1 campaign
compounds (dft_campaign/results/outcomes.jsonl).

## Scope

Force-field numbers are MACE-MP-0 (a foundation model trained on Materials Project PBE
data), not DFT. kMC costs are measured wall times of our own kMC code on one DGX core.
Neither result changes any earlier verdict; they decide whether a kMC rung is worth
adding to the multi-party campaign.
