# Minimal reciprocal disclosure in shared semiconductor screening depends on memory pressure, billing, timing masking and division of work

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23413480.svg)](https://doi.org/10.5281/zenodo.23413480)

Code and data for the article "Minimal reciprocal disclosure in shared semiconductor screening depends on memory pressure, billing, timing masking and division of work" (prepared for AI for Science (IOP Publishing)).

A research group screening two-dimensional semiconductors by density functional theory and the computing centre that runs its jobs could each gain by telling the other something, yet each guards its knowledge (the candidate list; the node settings). The article tests how little each party must disclose for both to gain, in 1,000 simulated scenarios and four preregistered measured comparisons of Quantum ESPRESSO screens of 29 MX2 layers. A gain for both parties needs jobs that fill much of node memory, billing for reserved memory, masked completion times and paired grading; under these conditions one disclosed memory bit per job raised the centre's valid results per unit charge 1.13-fold. The article also simulates research groups that exchange computed gaps and vacancy barriers, and groups that share growth and deposition stations.

The repository holds what the article reports and what is needed to rebuild
it: inputs, campaign drivers, registered predictions, raw records, result
summaries and the figure generator. Results are labelled **measured** (runs
on hardware) or **simulated** (the campaign simulator; simulated node-hours
are simulated units, not measured cost).

## Quick start

```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cd papers/paperA_disclosure_theory/figures && python3 make_figures.py
```

The figure generator regenerates every figure of the article from the
records in this repository; the manuscript and the rendered figures are not
included. `figure_test.json` records a run of the generator from a copy of
this repository with no access to anything else.

## Contents

- `papers/paperA_disclosure_theory/figures/make_figures.py`: the figure generator.
- One folder per experiment:

| folder | content |
|---|---|
| `billing_regrade/` | measured comparison No. 1 re-graded under whole-node and per-core charging |
| `ceiling_diagnosis/` | simulated: how much of the preregistered speed-up margin any agreement can reach |
| `centralization_surface/` | simulated: gain for both parties over training and execution centralization, task scale, number of research parties and schedules |
| `cofit_probe/` | measured: two 6x6 jobs run side by side versus one after another |
| `contention_transfer_bench/` | measured: co-tenant contention and defect and heterostructure cost probes |
| `decision_maker_leakage/` | simulated: leakage under five query policies |
| `dft_campaign/` | measured: Quantum ESPRESSO screen of the 30 MX2 candidates (fidelity stages F1 to F4, spin-orbit finalists) |
| `fast_path/` | replay of recorded run times and the per-candidate run-time library |
| `governance_regrade/` | simulated: re-grades under relaxed margins and acceptance thresholds (drawn by a ceiling_diagnosis script) |
| `hybrid_arms/` | simulated: hybrid, negotiation-only and collusion arms |
| `memory_band_probe/` | measured: 5x5 to 8x8 supercells, configuration cost and memory |
| `metric_redesign/` | simulated: paired win-rate metric study and validation on fresh scenarios |
| `multinode_bench/` | measured: 1, 2 and 4 node scaling |
| `paired_comparison_1/` | measured: comparison No. 1, 3x3 supercells, 480 QE calls |
| `paired_comparison_2/` | measured: comparison No. 2, 8x8 supercells, job packing and timing masking, band-structure repair pass |
| `paired_comparison_3/` | measured: comparison No. 3 on guest nodes (DTDE, CEDT, half-routed mixture and CTDE), timing attack |
| `paired_comparison_3b/` | measured: comparison No. 3b, single-layer 2H cells at 8x8 |
| `pilot/` | measured: randomized 81-job pilot |
| `prior_predictive/` | campaign simulator, prior specifications, the 30 candidate structures and the 1,000-scenario simulated grid |
| `rescreen_3x3/` | measured: 3x3 rescreen on guest nodes |
| `result_sharing/` | simulated on measured inputs: research groups exchanging computed gaps and vacancy barriers, or dividing the work through a booking broker with decoy refusals |
| `scale_validation/` | measured: supercell, layer and strain cost series |
| `shared_stations/` | simulated: growth and deposition stations sharing controller logs |
| `sociability_map/` | simulated: value and leakage of sharing against task scale (drawn by a ceiling_diagnosis script) |
| `stacking_study/` | measured: 2H single layers and DFT-D3 bilayers (AA' and 3R), with relaxation, spin-orbit and phonon follow-up |
| `stage2_twin_fit/` | fit of the cost model to the measured QE calls |
| `timing_masking/` | measured completion times re-attacked under masking clauses |
| `vacancy_barriers/` | measured: DFT nudged elastic band vacancy barriers (7 compounds) and Janus-layer barriers, MACE-MP-0 estimates, kinetic Monte Carlo costs; simulated vacancy-lifetime objective |

- `prior_predictive/candidates/`: the 30 idealized MX2 structures and their
  metadata (CC0-1.0).
- `case_manifest.yaml`: the case definition (budgets, thresholds, leakage
  limits, fidelity ladder F0 to F4), fixed before the measured campaigns.
- Dated preregistration and results records use "frozen" for "fixed before
  the data were collected". They are kept as written, because their dates
  and content are what the preregistration states.

The folders `fast_path/`, `governance_regrade/`, `contention_transfer_bench/`, `rescreen_3x3/`, `multinode_bench/`, `scale_validation/`, `sociability_map/`, `stacking_study/` are included because scripts in the reported folders read their files or stage them for a rerun.


Files the figure generator reads (`traced_inputs.json`):

- `billing_regrade/billing_regrade.json`
- `ceiling_diagnosis/results/ceiling_diagnosis.json`
- `centralization_surface/results/scaling.json`
- `centralization_surface/results/schedules.json`
- `centralization_surface/results/surface_P1.json`
- `centralization_surface/results/surface_P2.json`
- `centralization_surface/results/surface_P3.json`
- `centralization_surface/results/surface_P4.json`
- `centralization_surface/results/surface_scale.json`
- `paired_comparison_1/results/campaigns.jsonl`
- `paired_comparison_2/f3_repair/results/repair_graded.json`
- `paired_comparison_2/results/wire_attack_results.json`
- `metric_redesign/metric_study.json`
- `result_sharing/results/broker_decoy.json`
- `result_sharing/results/broker_exchange.json`
- `result_sharing/results/peer_exchange.json`
- `timing_masking/mask_results.json`

## Reproducing the results

`REPRODUCE.md` gives the software versions, the commands that regenerate
every summary and figure from the committed records, and the commands and
resources that re-run each computation (density functional theory jobs,
paired campaigns, simulations). `requirements.txt` lists the Python
packages; Quantum ESPRESSO 7.4 is needed only to re-run the DFT jobs.

## Licences and citation

Code (Python and shell scripts) is released under the MIT License
(`LICENSE`); data, result files and regenerated figures under the Creative
Commons Attribution 4.0 International licence (`LICENSE-CC-BY-4.0.txt`). The
candidate structures keep CC0-1.0. Cite with `CITATION.cff`.

`FILES.sha256` lists a SHA-256 hash for every file. Pseudopotentials are not
redistributed (GBRV 1.5 and PSlibrary 1.0.0 keep their own licences); file
names and hashes are given in `REPRODUCE.md` and in the experiment folders.
User identifiers were removed from the committed outputs.
