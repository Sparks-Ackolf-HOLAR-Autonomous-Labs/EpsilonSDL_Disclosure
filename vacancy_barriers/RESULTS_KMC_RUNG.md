# kMC rung: barrier disclosure, timing leakage, and the training axis

Run 2026-10-10, 22:05 to 22:20 UTC. All barriers are
MACE-MP-0 values (`results/vacancy_neb.jsonl`); the DFT NEB check in `dft_neb/` decides
whether these conclusions hold at DFT level. Campaign numbers from the twin are simulated
units; the disclosure probe uses the 60 measured kMC runs.

## 1. What a disclosed barrier is worth, and what it gives away (measured kMC runs)

`disclosure_probe.py`, results in `results/disclosure_probe.json`. Value is the
leave-one-compound-out R^2 of log kMC cost (the 1000 K, 1 s vacancy anneal), so it measures
how well a party predicts the cost of a compound it has not yet run. Leakage is the
exact-compound identification accuracy of an attacker holding the public table of disclosed
values; the study limit is 1/30 + 0.05 = 0.083.

| What crosses the boundary | Cost prediction R^2 | Compound identified | Within limit |
| --- | ---: | ---: | --- |
| size only (no disclosure) | 0.21 | 0.033 | yes |
| one bit: barrier above or below the median | 0.69 | 0.067 | yes |
| barrier tercile (rank only) | 0.75 | 0.100 | no |
| barrier rounded to 0.1 eV | 0.88 | 0.37 | no |
| exact barrier and divacancy binding | 0.90 | 1.00 | no |
| kMC job duration, as observed | | 0.68 | no |
| job duration rounded up to 600 s | | 0.68 | no |
| job duration rounded to a whole decade | | 0.19 | no |

- **One bit carries most of the value.** Telling the process modeller only whether a
  compound's vacancy barrier is above or below the median lifts cost prediction from 0.21
  to 0.69, and stays inside the identification limit. Finer disclosure adds little value
  (0.75 to 0.90) and breaks the limit.
- **The kMC clock gives the compound away.** kMC cost spans six decades between compounds,
  so the job duration alone identifies the compound 68% of the time. The 600 s rounding
  clause from comparison No. 2 does nothing here, and even rounding to whole decades leaves
  0.19. A kMC rung needs a stronger timing clause than DFT did: report completions in
  batches, or pad every kMC job to a fixed reserved time.

## 2. The kMC rung in the twin (simulated units)

`twin_kmc/kmc_rung.py`. The F3 rung becomes "F3 plus the vacancy anneal": its cost is the
base F3 cost times a compound factor taken from the measured kMC costs, bounded to one
decade either way (0.5 and 1.5 decades as sensitivity). The P2 classes become size bin x
barrier bit. 120 worlds, 21 points along the training axis tau at execution centralization
eps = 0, 0.5 and 1. Results in `twin_kmc/results/`.

| | Base twin | kMC rung (1 decade) |
| --- | ---: | ---: |
| Cost variance explained by the research party's own size law | 0.99 | 0.68 |
| Cost variance a size x barrier-bit logbook can explain | 0.98 | 0.94 |
| Throughput gain along tau at eps = 0 (tau 0 to 1) | +2.4% | +1.5% |
| Discovery win rate against no sharing, tau = 1, eps = 0 | 0.35 | 0.38 |
| Throughput gain along tau at eps = 0.5 and 1 | +1.2%, +0.3% | +0.3%, +0.3% |
| Win-win probability anywhere on the three transects | at most 0.07 | 0 |

- **The information condition is now met.** In the base twin the shared logbook knew less
  than the research party already knew from compound size (0.98 against 0.99). With the kMC
  rung the order reverses: size explains 0.68 of the cost and the logbook 0.94. The 0.5 and
  1.5 decade bounds give the same picture (own 0.78 and 0.66, logbook 0.97 and 0.91).
- **The training axis still barely slopes.** Sharing the logbook moves throughput by at
  most 1.5% and the discovery win rate by 0.03. The reason is in the campaign objective:
  the research party picks the next compound by its chance of landing in the 1.0 to 2.0 eV
  gap window. Knowing in advance that a compound's anneal is ten times dearer changes few of
  those picks, so the information has little decision value even though it has content.
- **The logbook still costs the identification limit.** With size x barrier-bit classes the
  identification accuracy reaches 0.144 by tau = 0.5. The barrier bit alone passes the
  static identification test (0.070), but in the twin its logbook explains only 0.24 of the
  cost, adds no throughput, and the membership attack still breaks the limit by tau = 0.5.
- An option to make the logbook learn only the part of the cost that size does not explain
  (`surface.SURR_SIZE_ADJ`, default off, all earlier results unchanged and the corner checks
  in `validate_continuity.py` still exact) removes the throughput loss of the barrier-bit
  logbook but adds no gain.

## Reading for materials work

The kMC rung answers the question it was built for: a process-modelling step whose cost is
set by the rate catalogue, not by cell size, is exactly where a performance logbook knows
something the materials group does not. Whether that knowledge is worth sharing depends on
the decision it feeds. In a band-gap screen the anneal cost hardly changes which compound is
run next, so the training axis stays nearly flat. The case where it should matter is a
campaign whose deliverable is the processing result (for example, picking anneal conditions
for vacancy healing across a set of compounds under a fixed compute budget), where the kMC
step is most of the spend. That case is not yet in the twin.

## Limitations

- MACE barriers are about 2.5 times too low against published PBE for MoS2 2H; the DFT NEB
  check (`dft_neb/`, predictions N1 to N5) is pending. If the spread between compounds
  shrinks at DFT level (N4 fails), section 2's kMC factors are withdrawn.
- The kMC factor bound (one decade) is a modelling choice made so a single compound cannot
  take the whole budget; it is a cold-start default that a calibrated campaign would set
  from its own budget share.
- The disclosure probe has 30 compounds and one kMC seed per lattice size; the timing
  attack assumes 0.05 decades of run-to-run scatter.
