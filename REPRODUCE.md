# Reproducing: Minimal reciprocal disclosure in shared semiconductor screening depends on memory pressure, billing, timing masking and division of work

This file explains how to reproduce every number, table and figure of the
article from this folder. All commands run from the folder root unless a
step says otherwise.

## Three levels of reproduction

1. **Check the archive.** `sha256sum -c FILES.sha256` confirms that every
   file is the one the article was written from.
2. **Re-analyse the committed records (no new compute).** Every summary,
   table and figure is regenerated from the raw records committed here
   (QE outputs parsed to JSON or JSONL, per-call campaign transcripts,
   simulator outputs). This level needs a workstation with Python and runs
   in minutes. It is the level a reader should run first.
3. **Re-run the computation.** The density functional theory jobs, the
   paired campaigns and the simulations can be repeated with the drivers,
   inputs and job scripts given for each experiment folder below. Measured
   job costs (wall time, memory, node-hours) depend on the hardware and on
   co-tenants; band gaps, energies and barriers do not. Simulations with
   fixed seeds reproduce exactly; the LLM-agent runs reproduce only
   statistically.

   Several steps below name a collector script (`collect_*.sh`). Those
   scripts copied the result files from the cluster into the working
   repository over the group's authenticated SSH connection and hard-code
   its account and paths, so they are not part of this folder. Copy the
   files each step lists by any means (`scp`, `rsync`) into the folder the
   step names; nothing else in the step changes.

Results are labelled in every folder as **measured** (from runs on
hardware) or **simulated** (from the campaign simulator); simulated
node-hours are simulated units, not measured cost.

## Software and data

**Analysis and figures.** Python 3.12 with numpy 2.5, scipy 1.18 and
matplotlib 3.11 (the versions the committed figures and summaries were
produced with; numpy 1.26 or later and matplotlib 3.8 or later also run the
scripts). Folders that need more state it in their section (for example
PySR for the cost-model fit, MACE for the machine-learned barriers, an
OpenAI-compatible LLM server for the LLM-agent campaigns).

```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` lists the packages the scripts of this repository
import; packages needed only to re-run a computation are listed there as
comments.

**Density functional theory.** Quantum ESPRESSO 7.4 (`pw.x`, `ph.x`,
`neb.x`) built with Open MPI 5.0.3, loaded on the clusters used here with
`module load openmpi/5.0.3 quantum-espresso/7.4`. Campaign drivers that
run on compute nodes need Python 3.10 or later (`module load python/3.10.3`
on those clusters). Functional: PBE throughout; D3 dispersion only where the
stacking study states it.

**Pseudopotentials** (not redistributed; download from the original
sources and check the hashes):

- Scalar-relativistic runs: GBRV 1.5 ultrasoft sets (Garrity, Bennett,
  Rabe and Vanderbilt, Comput. Mater. Sci. 81, 446 (2014)), file names of
  the form `mo_pbe_v1.uspp.F.UPF`. SHA-256 hashes:
  `pilot/results/pseudos_manifest.txt`.
- Spin-orbit runs: PSlibrary 1.0.0 fully relativistic PAW sets, file names
  of the form `Mo.rel-pbe-spn-kjpaw_psl.1.0.0.UPF`. SHA-256 hashes and
  cutoffs: `dft_campaign/soc/PSEUDOS.md`.

Place the files in the `pseudos/` folder each driver names (or the path
its job script sets) before staging inputs.

**Cluster settings.** Job scripts keep the resource requests used for the
article (cores, memory, wall time). Account, partition and scratch paths
are site settings: replace them with your own (`<account>`,
`<partition>`, `$SCRATCH`). Jobs that pack several QE runs onto one node
must be given the whole node's memory (`--mem=0` or the node size); the
packing logic assumes it.

**Candidates.** `prior_predictive/candidates/` holds the 30 idealized 1T
and 2H MX2 structures and their metadata (CC0-1.0); every DFT driver reads
them from there. `case_manifest.yaml` is the case definition, fixed before
the measured campaigns (budgets, thresholds, leakage limits, fidelity ladder
F0 to F4).

## Figures

```
cd papers/paperA_disclosure_theory/figures && python3 make_figures.py
```

regenerates every figure of the article from the committed records. The
files the generator reads are listed in `traced_inputs.json`;
`figure_test.json` records a run of the generator from a copy of this
folder with no access to anything else. Tables in the article are read from
the result summaries named in the experiment sections below.

## Experiments

One section per experiment folder of this article, in the order of the
layout table in `README.md`.

### `billing_regrade/`: re-grade of live comparison No. 1 under whole-node and per-core accounting

Level: analysis of committed records. The records are the 480 measured Quantum ESPRESSO calls of live comparison No. 1 (10 paired seeds, DTDE and CEDT_P4 arms), run on CHPC granite node grn061 (64 cores, 380 GB RAM). The same measured wall times are re-priced; no job was re-run.

**Re-analyse from the committed records (no new compute).**

Python 3, standard library only (`json`, `math`, `collections`).

1. `python3 billing_regrade/regrade_billing.py`
   - reads `paired_comparison_1/results/campaigns.jsonl` (per-job `wall_s`, `ranks`, `npool`, `cls`, `ok`, `gap_ev`, `t_start`, `candidate`; per-campaign `arm`, `seed`, `nh`, `labels_f2`, `fails`, `calls`), located relative to the script directory;
   - writes `billing_regrade/billing_regrade.json` (overwrites the committed file; work in a fresh copy of the repository) and prints both gradings and the oracle bounds.
   - No arguments, environment variables or random numbers.

What the script computes:

- Charge per job in 32-core node-hour equivalents: `node` = wall_s / 3600; `percore` = wall_s x ranks / 32 / 3600.
- Charge to first qualifier: jobs walked in `t_start` order until the first successful F3 with PBE gap in 1.0 to 2.0 eV (campaigns without a qualifier score their total charge).
- Grading as in `paired_comparison_1/analyze_live.py`: R passes if CEDT_P4 wins at least 60 % of pairs (one-sided sign test reported); H passes if F2 labels per charge is at least 1.05 x DTDE and the failure rate is at most DTDE + 0.04.
- Check of the recorded campaign `nh` against wall_s x ranks / 64 / 3600 (per-core on the 64-core node).
- Class charge shares, mean wall per (arm, class, ranks, pools), and oracle per-core bounds (best observed configuration per class, and per compound and class).

**Re-run the computation.**

The folder has no compute of its own. To regenerate the records, re-run live comparison No. 1 as documented in `paired_comparison_1/` (`live_campaign.py`, `collect_live.sh`), then repeat step 1.

**Outputs.**

- `billing_regrade/billing_regrade.json`
- `billing_regrade/RESULTS.md` (tables)

**Checks.** From `billing_regrade.json`:

| accounting | wins (of 10) | sign-test p | labels per charge vs DTDE | DTDE / CEDT_P4 total charge |
| --- | ---: | ---: | ---: | --- |
| whole node | 0 | 1.0 | 0.9087 | 9.4342 / 10.3823 |
| per core | 6 | 0.377 | 1.0051 | 9.4342 / 9.3868 |

- Failure rate: DTDE 0.0333, CEDT_P4 0.0292 (both accountings). Preregistered success: false in both.
- Recorded `nh` matches per-core charging on 64 cores to a maximum absolute difference of 7e-05.
- Mean wall (s): F1 56.5 (DTDE, 32 ranks) vs 89.6 (CEDT_P4, 16 ranks); F2 143.1 vs 139.2 (32 ranks, 2 pools); F3 225.0 vs 238.4 (32 ranks, 4 pools); 80 jobs per cell.
- F3 share of per-core charge: 0.530 (DTDE), 0.564 (CEDT_P4).
- Oracle per-core bounds: best configuration per class saves 3.69 %; per compound and class 4.82 %; difference 1.12 % of spend.

Limits: a re-pricing of fixed measured walls; it assumes freed cores are billed pro rata (per-core accounting with backfill) and cannot capture contention from co-tenants on the freed cores. Numbers apply to grn061 and the 3x3 supercell job sizes of this comparison.

### `bootstrap_ci/`: seed-level bootstrap intervals for the measured timing attacks of comparisons No. 1, No. 2 and No. 3

Level: analysis of committed records. Underlying records: comparison No. 1 (480 Quantum ESPRESSO calls, 10 paired seeds) and comparison No. 2 (15 paired seeds), both run on CHPC granite node grn061 (64 cores, 380 GB RAM); comparison No. 3 (60 campaigns, seeds 0 to 14, on granite-guest and notchpeak-guest nodes) and its 12 site-bridge copies run on notchpeak guest nodes.

**Re-analyse from the committed records (no new compute).**

Python 3 with `numpy`. Both scripts resolve paths from their own location, so they run from the repository root. Each overwrites its committed output; work in a fresh copy of the repository.

1. Comparisons No. 1 and No. 2 and the masking sweep:
   `python3 bootstrap_ci/seed_bootstrap.py`
   - imports `timing_masking/mask_study.py` and `paired_comparison_2/wire_attack2.py` (attack code reused unchanged);
   - reads `paired_comparison_1/results/campaigns.jsonl` (comparison No. 1), `timing_masking/mask_results.json` (list of masking clauses to re-evaluate), `paired_comparison_2/inputs/manifest2.json`, `paired_comparison_2/results/wire_log.jsonl`, and the `SALT` line of `paired_comparison_2/live2_campaign.py` (to map opaque identifiers back to compounds offline);
   - writes `bootstrap_ci/seed_bootstrap.json`.
2. Comparison No. 3:
   `python3 bootstrap_ci/seed_bootstrap3.py`
   - imports `paired_comparison_3/wire_attack3.py`, which reads `paired_comparison_3/collected_2026-10-14/<ARM>_s<seed>/{campaigns.jsonl,wire_log.jsonl}` (60 campaign folders), `paired_comparison_3/site_bridge_2026-10-14/<ARM>_s<seed>/` (12 folders) and `paired_comparison_2/inputs/manifest2.json`;
   - writes `bootstrap_ci/seed_bootstrap3.json`.

Method in both scripts: leave-one-seed-out identity and membership attacks as in the source folders; the per-seed held-out outcomes are resampled with replacement (cluster bootstrap over seeds, B = 10000, percentile 95 % intervals). References are not refitted per replicate. Paired arms share the resampled seed indices (No. 1 arms; DTDE and CEDT_P4 in No. 3, including the T3 difference). Seeds: `numpy.random.default_rng(20261008)` for `seed_bootstrap.py`, `default_rng(20261015)` for `seed_bootstrap3.py`. No command-line arguments or environment variables.

**Re-run the computation.**

The folder has no compute of its own. The records come from `paired_comparison_1/` (comparison No. 1), `paired_comparison_2/` (No. 2) and `paired_comparison_3/` (No. 3 and site bridge); re-running those campaigns and then the two scripts above regenerates the intervals.

**Outputs.**

- `bootstrap_ci/seed_bootstrap.json` (`comparison1`, `masking` worse-arm intervals for every clause, `comparison2`)
- `bootstrap_ci/seed_bootstrap3.json` (`arms`, `T3_identity_difference_CEDT_minus_DTDE`, `T1_cross_cluster`)
- The No. 3 table is reproduced in `paired_comparison_3/TIMING_ATTACK_RESULTS.md` (section "Bootstrap intervals").

**Checks.** Point estimates must equal the source attacks; intervals are 95 % percentile.

| record | identity accuracy | membership AUC |
| --- | --- | --- |
| No. 1, DTDE and CEDT_P4 (10 seeds) | 0.9625 (0.9125 to 1.0) | 1.0 (1.0 to 1.0) |
| No. 1, pad p99, worse arm | 0.075 (0.0375 to 0.1125) | 0.5013 (0.4726 to 0.5377) |
| No. 1, quant 600 s, worse arm | 0.05 (0.0125 to 0.0875) | 0.5 (0.5 to 0.5) |
| No. 2, DTDE (15 seeds) | 0.78 (0.68 to 0.875) | 0.9893 (0.979 to 0.9989) |
| No. 2, CEDT_P4 (15 seeds) | 0.5849 (0.4423 to 0.7193) | 0.9348 (0.9103 to 0.9587) |
| No. 3, DTDE (15 seeds) | 0.75 (0.6279 to 0.8605) | 0.9447 (0.9034 to 0.9754) |
| No. 3, CEDT_P4 | 0.4839 (0.3913 to 0.5761) | 0.8256 (0.7722 to 0.8749) |
| No. 3, CTDE_P2 | 0.2184 (0.1348 to 0.3177) | 0.6721 (0.613 to 0.7347) |
| No. 3, MIX50 routed jobs | 0.1739 (0.0895 to 0.2698) | 0.7216 (0.6395 to 0.7997) |
| No. 3, T1 cross-cluster (10 seeds) | 0.4655 (0.2632 to 0.6727) | 0.8324 (0.7313 to 0.9135) |

T3 difference (CEDT_P4 minus DTDE identity, No. 3): -0.2661 (-0.4154 to -0.0921). Identity limits: 0.087 (No. 1), 0.0845 (No. 3); AUC limit 0.60.

Limits: intervals describe seed-to-seed variation given fixed leave-one-seed-out references, not refitting uncertainty; with 10 or 15 seeds the percentile intervals are coarse; the measured walls, and therefore all values, depend on the nodes and co-tenant load during the original runs.

### `ceiling_diagnosis/`: decomposition of the baseline spend to first qualifier into irreducible, scientific and execution components

Level: simulated (simulated node-hours on the prior-predictive twin imported from `prior_predictive/simulator.py`, base prior card only). The hardware used is not in the repository.

**Re-analyse from the committed records (no new compute).** Python 3 with `numpy` and `matplotlib`.

1. `python3 ceiling_diagnosis/make_figures.py` (paths resolve relative to the script, so any working directory works). It reads `ceiling_diagnosis/results/ceiling_diagnosis.json` and writes `ceiling_diagnosis/results/fig_ceiling_decomposition.png`.
2. The same script also reads `decision_maker_leakage/dm_leakage.json`, `sociability_map/sociability_map.json` and `governance_regrade/governance_regrade.json` and overwrites the figures `decision_maker_leakage/fig_dm_leakage.png`, `sociability_map/fig_sociability_map.png` and `governance_regrade/fig_governance.png` in those sibling folders. All three inputs are committed.
3. The headline numbers can be read directly from the `summary` block of `ceiling_diagnosis.json` (per-world rows are in `rows`).

**Re-run the computation.**

1. `python3 ceiling_diagnosis/diagnose_ceiling.py`, optionally with `DIAG_WORLDS=<n>` (default 300). There is no command-line parser; the worker pool always uses `os.cpu_count()` processes.
2. The script sets `MPT_HARD_CAP=1` by default before importing the simulator (an explicit `MPT_HARD_CAP=0` in the environment overrides it).
3. For each base-card world id 0 to n-1 it runs the native CTCE-P0 and DTDE-P4 campaigns (30 paired seeds) and a nature oracle (`oracle_nh_first`) that knows which candidates qualify and every cost and failure draw and runs the minimum admissible F1 to F4 ladder.
4. Output: `ceiling_diagnosis/results/ceiling_diagnosis.json` (summary and per-world rows). The summary is printed to stdout; `results/diagnosis_stdout.txt` is a capture of that printout (redirect stdout to regenerate it).
5. No measured inputs are read. Worlds are seeded from `crc32("base:<world_id>")` in `simulator.sample_world`, so the run is deterministic for a given code version and NumPy version.

`oracle_nh_first` is imported by `metric_redesign/metric_study.py`, so this folder must be present for that study.

**Outputs.**

- `results/ceiling_diagnosis.json`
- `results/diagnosis_stdout.txt`
- `results/fig_ceiling_decomposition.png`

**Checks.** From `RESULTS.md` and `results/diagnosis_stdout.txt` (300 base-card worlds):

- Fractions of the DTDE spend to first qualifier: irreducible mean 0.376 (median 0.373), scientific gap mean 0.553 (median 0.515), execution gap mean 0.032 (median 0.056, q10 to q90 of -0.314 to 0.310).
- P(execution gap >= 20 %) = 0.200; P(execution gap >= 10 %) = 0.383.
- Fixed per-attempt overhead fraction of DTDE spend: mean 0.069.
- Labels per node-hour ratio CTCE / DTDE: mean 1.216, median 1.144; P(ratio >= 1.15) = 0.493.
- P(preregistered reservation gain, CTCE) = 0.183.
- With fixed seeds a rerun is expected to be identical; this has not been recorded as verified. Limits stated in `RESULTS.md`: a single (base) prior card; the oracle is a lower bound that obeys ladder rules but ignores contention-avoidance scheduling.

### `centralization_surface/`: continuous training-by-execution centralization surface, multi-party scaling, adaptive schedules and task-scale sweep

Level: simulated (twin physics imported unchanged from `prior_predictive/simulator.py`); the task-scale sweep is simulated on measured inputs. `RESULTS.md` records the 11 x 11 P1 and P3 surfaces as run on the DGX Spark (aarch64); hardware for the other runs is not in the repository.

**Re-analyse from the committed records (no new compute).** Python 3 with `numpy`, `scipy` and `matplotlib` (the 3D figure uses `mpl_toolkits.mplot3d`, shipped with matplotlib). Paths resolve relative to each script.

1. `python3 centralization_surface/make_figures.py` reads `results/surface_P4.json`, `surface_P3.json`, `surface_P2.json`, `surface_P1.json` (whichever exist), `results/scaling.json` and `results/schedules.json`, and writes `results/fig_centralization_surface.png`, `results/fig_centralization_heatmaps.png`, `results/fig_multiparty_scaling.png` and `results/fig_schedules.png`.
2. `python3 centralization_surface/make_tau_figure.py` reads `results/tau_diagnostic.json` and writes `results/fig_tau_answer.png`.
3. `python3 centralization_surface/make_scale_figure.py` reads `results/surface_scale.json` and writes `results/fig_surface_vs_scale.png`.

**Re-run the computation.** Each script below writes to `centralization_surface/results/` with a hard-coded file name; `--procs` defaults to `os.cpu_count()` and `--smoke` gives a tiny test run.

1. Surfaces at four disclosure levels (11 x 11 grid of (tau, eps) on [0, 1], 150 worlds, 30 paired seeds):
   `python3 centralization_surface/surface.py --worlds 150 --grid 11 --level P4` (repeat with `--level P3`, `P2`, `P1`); output `results/surface_<level>.json`. The default `--grid` is 6 and `--level` is P2, so pass both explicitly. P3 uses the default DP budget eps_DP = 4.
2. Training-axis diagnostic: `python3 centralization_surface/tau_diagnostic.py --worlds 120 --npts 21`; output `results/tau_diagnostic.json` (part A on 6 worlds, part B on 60 worlds with a fixed generator seed 7, part C transects on the requested worlds).
3. Multi-party scaling, N in {1, 2, 3, 5}: `python3 centralization_surface/scaling.py --worlds 200`; output `results/scaling.json`.
4. Adaptive schedules (eps-schedule at P4, tau-schedule at P2, time-mean 0.5, T = 80 rounds): `python3 centralization_surface/schedules.py --worlds 200`; output `results/schedules.json`.
5. Task-scale sweep on the posterior twin: `python3 centralization_surface/surface_scale.py --worlds 120 --grid 5` (defaults `--scales 1,10,30,100,300`, `--levels P4`, `--p2-scales 1,100`); output `results/surface_scale.json`. It reads the committed measured fits `stage2_twin_fit/twin_fit.json` and `pilot/results/pilot_fit.json`, and hard-codes the electron-scaling exponent by scale (1.20, 1.70, 2.00, 2.30, 2.50) and a 0.02 node-hour per-submission overhead. The scale is set through module globals before the worker pool starts, which relies on the `fork` start method (Linux default).
6. Corner and gradient check: run from inside the folder, because it uses working-directory-relative imports: `cd centralization_surface && python3 validate_continuity.py`. It uses 40 worlds at P4 and prints to stdout only (no file written).
7. Then rerun the three figure scripts above.

Seed handling: worlds come from `simulator.sample_world` (`crc32("<card>:<world_id>")`), with worlds split evenly over the three prior cards; the per-round delegation draws are seeded from each world's contention field, so (tau, eps) points are paired within a world; `surface_scale.py` adds `crc32("surfscale:<card>:<world_id>")` for the posterior patch. `MPT_HARD_CAP` has no effect on `surface.py`: its `run_mix` campaign loop stops once spend reaches the 500 node-hour budget (soft stop). Two module flags in `surface.py` (`SURR_SIZE_ADJ`, `IMMOBILE_FN`/`PASSRATE_TRAIN`) default to off and must stay off to reproduce these results.

**Outputs.**

- `results/surface_P1.json`, `surface_P2.json`, `surface_P3.json`, `surface_P4.json` (meta: 150 worlds, grid 11, 30 seeds)
- `results/tau_diagnostic.json` (120 worlds, 21 points), `results/scaling.json` (200 worlds), `results/schedules.json` (200 worlds), `results/surface_scale.json` (120 worlds, grid 5)
- Figures: `fig_centralization_surface.png`, `fig_centralization_heatmaps.png`, `fig_multiparty_scaling.png`, `fig_schedules.png`, `fig_tau_answer.png`, `fig_surface_vs_scale.png`

**Checks.**

- Corners of the mixed arm reproduce native DTDE and CEDT exactly and CTDE within 1.7 % on labels per node-hour (`RESULTS.md`).
- P4 at 11 x 11 (wide-prior cards): interior optimum win-win 0.26 at eps = 0.6 against 0.21 at the CEDT corner; every tau row is constant at P4 (part A of the diagnostic reports bit-identical outcomes for tau in {0, 0.5, 1}).
- P2 at 11 x 11: peak win-win 0.20 at (tau = 0, eps = 0.3) with leakage pass 0.99. P3: peak 0.19 at (0, 0.4). P1: win-win 0 in all 121 cells; throughput gain +25.3 % at full delegation.
- Cost-information R^2 at P2: own 0.986, surrogate 0.975, broker 0.759.
- Scaling: CEDT-P4 win-win 0.215 / 0.220 / 0.235 / 0.205 for N = 1, 2, 3, 5; CEDT-P2 identity accuracy rises 0.143 to 0.205.
- Schedules (eps at P4, mean 0.5): static 0.250, ramp-up 0.120, ramp-down 0.270, mid-pulse 0.230.
- Task scale (P4 ridge at eps = 1): 0.450 at x1, 0.942 at x10 and x30, 0.950 at x100 and x300.
- The tables in sections 2 and 3 of `RESULTS.md` quote an earlier 200-world, 6 x 6 run whose JSON is not in the repository; the committed `surface_P*.json` files are the later 11 x 11, 150-world grids. Reruns with the same code are expected to be identical (deterministic seeding), not recorded as verified. The N-party effects are reduced-form modifiers, and interior leakage is interpolated from the native attacker models.

### `cofit_probe/`: co-scheduling probe measuring 16-rank solo and concurrent 16+16 Quantum ESPRESSO walls and RAM for two 6x6 MX2 supercells on one node

Level: measured on hardware (CHPC granite node grn061, 64 cores, 380 GB, CPU-only `pw.x`; owner partition class, job 1940907).

**Re-analyse from the committed records (no new compute).**

1. Read `cofit_probe/results/cofit_results.jsonl` (four per-run records with `name`, `tag` (`solo16` or `co16`), `ranks`, `wall_s`, `converged`, `ram_mb_per_proc`, `ram_total`, `nh`, `nh_cum`, plus one `co16_makespan` record).
2. Recompute the quantities in `cofit_probe/results/RESULTS.md` by hand or in a few lines of Python (no analysis script for this step is in the repository):
   contention = `wall_s(co16) / wall_s(solo16)` per candidate;
   packing saving = `1 - makespan_s / 8645` (8,645 s is the sequential 32-rank baseline, 3,777 s + 4,868 s, recorded in `memory_band_probe/results/RESULTS.md`);
   rank-scaling exponent s from `wall(16) = wall(32) * 2**s`.
3. Regenerate the figure: `(cd cofit_probe/results && python3 make_figure.py)`, which writes `cofit_probe/results/fig_cofit.png`. The script uses values typed into the source (it does not read the JSONL). Requires `matplotlib`.
4. The post-refit design regrade quoted in RESULTS.md reads `paired_comparison_2/prestudy/prestudy_results_postcofit*.json`. The committed `paired_comparison_2/prestudy/prestudy.py` still carries the pre-probe priors (s in 0.35 to 0.50, c in 0.05 to 0.12); the edited version with the refit priors (s in 0.76 to 0.84, c in 0.02 to 0.05) is not in the repository. To regrade, set those two `PRIORS` entries and run `MPT_TAG=_postcofit_c8p15 MPT_CALLS=8 MPT_PAIRS=15 python3 paired_comparison_2/prestudy/prestudy.py` (environment variables `MPT_WORLDS`, `MPT_PAIRS`, `MPT_CALLS`, `MPT_SCALES`, `MPT_TAG` as read by the script).

**Re-run the computation.**

1. Inputs: `memory_band_probe/inputs/MoSe2_2H_s6_k2.pw.in` and `memory_band_probe/inputs/WTe2_2H_s6_k2.pw.in` (6x6 in-plane supercells, 2x2x1 k-grid, ecutwfc 35 Ry, ecutrho 280 Ry, cold smearing 0.02 Ry, conv_thr 1e-6). They are regenerated by `python3 memory_band_probe/build_probe_inputs.py` (no arguments), which tiles `pilot/inputs/<cand>.pw.in`.
2. Pseudopotentials: GBRV PBE ultrasoft, files `mo_pbe_v1.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `te_pbe_v1.uspp.F.UPF`, downloaded from the GBRV site as in `memory_band_probe/stage_and_submit.sh`. No hash manifest for these files is in the repository.
3. Software: module stack `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3` (from `cofit_probe/cofit.sbatch`); `cofit.py` uses only the Python standard library.
4. Stage on the cluster: a directory `$SCRATCH/mpt_cofit` containing `cofit.py`, `cofit.sbatch`, `inputs/` (the two files above), `pseudos/`, and an empty `results/`. A staging script for this folder is not in the repository; the pattern in `memory_band_probe/stage_and_submit.sh` applies.
5. Submit: `sbatch --account=<account> --partition=<partition> --qos=<qos> --export=ALL,MPT_COFIT_ROOT=$SCRATCH/mpt_cofit cofit.sbatch`. Resources: 1 node, 64 tasks, `--time=10:00:00`; budget guard `MPT_COFIT_NH_CAP` (default 6 per-core node-hours). The committed script names the owner partition and account; replace them with your own.
6. Run order inside `cofit.py`: MoSe2 solo at 16 ranks, then WTe2 solo at 16 ranks, then both concurrently at 16+16 ranks (`mpirun -np 16 --bind-to none pw.x -nk 1`). Each record is appended to `results/cofit_results.jsonl`.
7. Collect: copy `$SCRATCH/mpt_cofit/results/cofit_results.jsonl` into `cofit_probe/results/`, then apply the re-analysis steps above.
8. Observed cost: 6 h 38 min wall, 2.13 per-core node-hours, 4 of 4 SCFs converged.

**Outputs.**

- `cofit_probe/results/cofit_results.jsonl`
- `cofit_probe/results/RESULTS.md`
- `cofit_probe/results/fig_cofit.png`

**Checks.**

- Solo 16-rank walls: MoSe2_2H 6,509.8 s, WTe2_2H 8,591.2 s. Concurrent: 6,760.9 s and 8,800.2 s (contention +3.9 % and +2.4 %).
- Concurrent makespan 8,800 s against the 8,645 s sequential 32-rank baseline: packing saving of -1.8 % (the registered 19 % prediction is falsified).
- Rank-scaling exponent s = 0.785 (MoSe2) and 0.820 (WTe2), i.e. 1.72x and 1.77x the 32-rank wall.
- RAM totals at 16 ranks: 42.12 GB and 52.50 GB, within 1 % of the 32-rank values.
- Limits: walls depend on the node model, memory bandwidth and co-tenant load; the 32-rank baseline comes from a separate job (`memory_band_probe/`), not from this run.

### `decision_maker_leakage/`: leakage of a fixed contract under five decision-maker archetypes, single-policy against policy-robust audits

Level: simulated (base prior card, x1 task scale). The machine used for the committed run is not in the repository. All node-hours are simulated units.

The folder has no README; the definition, results and interpretation are in `decision_maker_leakage/RESULTS.md`.

**Re-analyse from the committed records (no new compute).**

1. The audit table in `RESULTS.md` is stored in `decision_maker_leakage/dm_leakage.json` (keys `worlds`, `table` with per-policy, per-contract channel means, `audit` with single-policy and policy-robust pass probabilities, `limits`). Print it with:
   `python -c "import json; d=json.load(open('decision_maker_leakage/dm_leakage.json')); [print(k, round(v['policy_robust'],2), {p: round(x,2) for p,x in v['single_policy'].items()}) for k,v in d['audit'].items()]"`
   This reproduces the lines of `decision_maker_leakage/dm_stdout.txt`.
2. The figure `decision_maker_leakage/fig_dm_leakage.png` is not written by any script in this folder. It is produced by `ceiling_diagnosis/make_figures.py` (figure 2 block), which reads `dm_leakage.json` and writes the PNG into this folder:
   `python ceiling_diagnosis/make_figures.py`
   The script has no main guard and also regenerates three other figures from committed files: `ceiling_diagnosis/results/fig_ceiling_decomposition.png`, `sociability_map/fig_sociability_map.png` and `governance_regrade/fig_governance.png`.
3. The paper version of this result (panel of `fig_policy.pdf`) is drawn by `fig_policy()` in `papers/paperC_leakage_attacks/figures/make_figures.py`, which also reads `measured_attacks/attack_results.json`.

Python packages: numpy, scipy (imported by the simulator), matplotlib.

**Re-run the computation.**

1. From the repository root:
   `python decision_maker_leakage/dm_leakage.py > decision_maker_leakage/dm_stdout.txt`
   Environment variables read: `DM_WORLDS` (default 200) and `MPT_HARD_CAP` (set to `1` by the script unless already defined). The process pool uses all CPU cores (`os.cpu_count()`); there is no option to change it.
2. The script imports `prior_predictive/simulator.py` (30 paired seeds per world) and installs each archetype through the simulator hook `R_PICK_POLICY`: `greedy` (the audit policy), `depth_first`, `repeat_prone` (factor 4 on the previous pick), `thompson`, `eps_greedy` (25 % random). It runs four contracts per world and archetype: CEDT-P2, CEDT-P3 (epsilon = 2), CTDE-P3 (epsilon = 2), CEDT-P4, giving 200 x 5 tasks.
3. Random-seed handling: worlds from `default_rng(crc32("base:<world>"))` in the simulator; the stochastic archetypes draw from fixed streams `default_rng(7000000 + round)` (thompson) and `default_rng(8000000 + round)` (eps_greedy). The only committed input is `prior_predictive/candidates/candidates.json`.
4. Output: the script overwrites `decision_maker_leakage/dm_leakage.json` (hard-coded path). Runtime is not in the repository.

**Outputs.**

- `decision_maker_leakage/dm_leakage.json`
- `decision_maker_leakage/dm_stdout.txt`
- `decision_maker_leakage/fig_dm_leakage.png` (via `ceiling_diagnosis/make_figures.py`)

**Checks.**

- P(all six leakage limits hold), policy-robust audit: CEDT-P2 0.00, CEDT-P3 0.03, CTDE-P3 0.01, CEDT-P4 1.00.
- Single-policy audits for CEDT-P3: greedy 0.56, depth_first 0.04, repeat_prone 0.43, thompson 0.49, eps_greedy 0.54; for CTDE-P3: 0.59, 0.01, 0.56, 0.46, 0.56.
- `RESULTS.md` reports a mean membership AUC of 0.80 to 0.82 for `depth_first` at P3 (limit 0.60), and, under CEDT-P3, found-rate 0.86 against 0.81 and labels per node-hour 0.022 against 0.031 for `depth_first` against `greedy`.
- The identification limit used here is `1/30 + 0.05` on `r_id_acc`, set in the script.
- All random streams are fixed, so a rerun with the same package versions is expected to reproduce the JSON exactly; a verified rerun is not in the repository.
- Limits: base prior card only; the attackers are the preregistered Bayes-style upper-bound constructions; the archetypes are scripted stand-ins for behaviours observed with LLM-driven decision makers, not LLM runs.

### `dft_campaign/`: Quantum ESPRESSO fidelity ladder (F1 to F4) on the 30 idealized MX2 candidates, plus spin-orbit gaps for the nine finalists (`dft_campaign/soc/`)

Level: measured on hardware. CHPC granite node grn061 (64 cores, 380 GB, one H100 not used), single-node partition of the group allocation; the jobs requested 48 of the 64 cores and 180 GB. All QE runs are CPU-only.

**Re-analyse from the committed records (no new compute).**

1. Python 3 standard library only (no third-party packages).
2. `python3 dft_campaign/analyze_dft.py` reads `dft_campaign/results/outcomes.jsonl` (later lines for a candidate override earlier ones) and `dft_campaign/results/campaign_summary.json`, and rewrites `dft_campaign/results/DFT_RESULTS.md` (per-candidate table, 1T minus 2H energy per formula unit within each composition, cost totals).
3. Optional, already applied to the committed files: `python3 dft_campaign/patch_f4.py` re-parses the nine raw phonon outputs in `dft_campaign/results/f4_outputs/*_f4.out` and backfills the Gamma frequencies into `outcomes.jsonl` and `campaign_summary.json` in place. Running it again is idempotent.
4. Spin-orbit sub-study: there is no separate analysis script; the summary is `dft_campaign/soc/results/soc_summary.json` as written by the driver (per-finalist `soc_gap_ev` and `soc_shift_ev`).

**Re-run the computation.**

1. Structures: `prior_predictive/candidates/candidates.json` (CC0-1.0, generated by `prior_predictive/make_candidates.py`, no arguments). The driver reads `candidates.json` from its working directory `$MPT_DFT_ROOT`, so copy it there.
2. Pseudopotentials: GBRV 1.5 ultrasoft PBE set (archive `all_pbe_UPF_v1.5.tar.gz`, Rutgers), files `ti_pbe_v1.4.uspp.F.UPF`, `zr_pbe_v1.uspp.F.UPF`, `hf_pbe_v1.uspp.F.UPF`, `mo_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, `te_pbe_v1.uspp.F.UPF`, placed in `$MPT_DFT_ROOT/pseudos/`. sha256 hashes for six of them (Ti, Mo, W, S, Se, Te) are in `pilot/results/pseudos_manifest.txt`; no hash file for the Zr and Hf files is in the repository. `stacking_study/stage_and_submit_stacking.sh` shows a download loop for the same eight files.
3. Software: Quantum ESPRESSO 7.4 (`pw.x`, `ph.x`; version confirmed in the committed `f4_outputs`), modules `openmpi/5.0.3 quantum-espresso/7.4`, `python3` on the login stack, `/usr/bin/time -v` for memory telemetry.
4. Staging of `run_campaign.py`, `candidates.json` and `pseudos/` to `$SCRATCH/mpt_dft/` was done by hand; a staging script is not in the repository.
5. Submit `dft_campaign/campaign.sbatch` (`--nodes=1 --ntasks=48 --mem=180G --time=20160` minutes, `--account=<account> --partition=<partition> --qos=<qos>`). It runs `python3 run_campaign.py` in `$MPT_DFT_ROOT` (default `$SCRATCH/mpt_dft`) with `OMP_NUM_THREADS=1`. Driver settings via environment: `MPT_NPROC_PER_RUN` (16), `MPT_NPOOL` (4), `MPT_WORKERS` (3 concurrent `pw.x`), `MPT_NODE_HOUR_CAP` (330, soft guard). Each QE call is `mpirun -np 16 --bind-to none pw.x -nk 4`.
6. Ladder (per candidate): F1 SCF 40 Ry, 6x6x1; F2 `vc-relax`, `cell_dofree='2Dxy'`, 45 Ry, 12x12x1; F3 NSCF 18x18x1 (gap window 1.0 to 2.0 eV); F4 fresh SCF then `ph.x` at Gamma for qualifiers. One retry per failed stage (mixing 0.3 to 0.2, `cg`, 200 steps). Non-spin-polarized, no SOC.
7. A second pass, `python3 run_campaign.py --repair-f3` (the only command-line option), finalized F3/F4 records in the original run (29 s).
8. Collect `results/outcomes.jsonl`, `results/campaign_summary.json` and `campaign_<jobid>.log` from `$MPT_DFT_ROOT` into `dft_campaign/results/` (`dft_campaign/collect_dft.sh` does this over an authenticated SSH connection; it requires `CHPC_USERNAME`), copy the nine `work/<candidate>/f4.out` files to `results/f4_outputs/<candidate>_f4.out`, then run `patch_f4.py` and `analyze_dft.py` (steps 2 and 3 above).
9. Observed cost: 0.883 h wall, 108 QE calls, 0.59 node-hours (driver convention: wall x cores used / 64); budget cap not hit.

Sub-study `dft_campaign/soc/` (spin-orbit gaps):

1. Input: `dft_campaign/soc/finalists.json` (nine finalists with relaxed `a`, fixed F2 positions and scalar-relativistic gap). The script that built it from `results/outcomes.jsonl` is not in the repository.
2. Pseudopotentials: fully relativistic PSlibrary 1.0.0 PAW (`*.rel-pbe-spn-kjpaw_psl.1.0.0.UPF` for Zr, Hf, Mo, W; `*.rel-pbe-n-kjpaw_psl.1.0.0.UPF` for S, Se, Te), not bundled; file names and sha256 hashes in `dft_campaign/soc/PSEUDOS.md`. Cutoffs 60/400 Ry.
3. Stage `soc_campaign.py`, `finalists.json` and `pseudos/` into `$MPT_SOC_ROOT` (by hand; no staging script in the repository) and submit `dft_campaign/soc/soc.sbatch` (`--ntasks=48 --mem=180G --time=4:00:00`, node grn061, same module stack, `OMP_NUM_THREADS=1`, 16 ranks x 3 workers, `MPT_NODE_HOUR_CAP=10`). It runs `python3 soc_campaign.py` (no arguments): SOC SCF 12x12x1, then NSCF 18x18x1.
4. Collect with `dft_campaign/soc/collect_soc.sh` into `dft_campaign/soc/results/`. Observed cost: 0.126 h wall, 18 QE calls, 0.079 node-hours. A first submission (log `soc_1914220.log`) was cancelled because `OMP_NUM_THREADS` was unset and the node was oversubscribed; the committed sbatch file contains the fix.

**Outputs.**

- `dft_campaign/results/DFT_RESULTS.md`
- `dft_campaign/results/outcomes.jsonl`, `dft_campaign/results/campaign_summary.json`, `dft_campaign/results/campaign_1913865.log`
- `dft_campaign/results/f4_outputs/*_f4.out` (nine raw `ph.x` outputs)
- `dft_campaign/soc/results/soc_summary.json`, `dft_campaign/soc/results/soc_outcomes.jsonl`, `dft_campaign/soc/results/soc_1914274.log`

**Checks.**

- 30/30 candidates completed; 29 F2-converged (HfSe2_2H failed its relaxation retry); 9 qualifiers: HfS2_1T, HfS2_2H, MoS2_2H, MoSe2_2H, MoTe2_2H, WS2_2H, WSe2_2H, WTe2_2H, ZrS2_1T.
- Example PBE gaps: MoS2_2H 1.557 eV, WS2_2H 1.770 eV, ZrS2_1T 1.201 eV. Relaxed `a` of MoS2_2H 3.1818 A.
- All nine qualifiers pass the Gamma check (minimum frequency at least -16.6 cm-1; instability threshold -30 cm-1).
- 1T minus 2H energy: negative for all Ti, Zr, Hf compositions, positive for Mo and W (for example MoS2 +0.843, HfS2 -0.652 eV per formula unit).
- SOC gaps (eV): HfS2_1T 1.3106, HfS2_2H 1.0356, MoS2_2H 1.5519, MoSe2_2H 1.3502, MoTe2_2H 0.928, WS2_2H 1.5682, WSe2_2H 1.2617, WTe2_2H 0.7382, ZrS2_1T 1.1515. The SOC shift mixes the spin-orbit effect with the change of pseudopotential family (GBRV to PSL).
- Limits: the "2H" entries are 6-atom AA' bilayers relaxed with plain PBE and no dispersion correction (see `stacking_study/`). Gaps are PBE screening quantities; Gamma phonons are not a dynamical-stability proof. Wall times and node-hours depend on the node and its co-tenants; energies and gaps should agree to SCF tolerance with the same pseudopotentials.

### `fast_path/`: recorded-cost replay of the paired-comparison driver and the run-time library that completes it

Level: analysis of committed records (replay of the 33 campaigns of `paired_comparison_2/`, measured on CHPC granite node grn061, 64 cores, 380 GB) plus a measured run-time library (`results_lib3/`) on CHPC granite guest nodes (AMD EPYC 9654P, 96 cores; 16 MPI ranks per task).

**Re-analyse from the committed records (no new compute).**

`results/` (replay validation and option grades):

1. Validation: `python3 fast_path/replay.py --validate` (the `--out` default is `fast_path/results/replay_validation.json`). Reads `paired_comparison_2/inputs/manifest2.json`, `paired_comparison_2/results/campaigns.jsonl` and `paired_comparison_2/f3_repair/results_raw/repair_gaps.json`; rebuilds each campaign with a leave-one-campaign-out library.
2. Option grades as committed (library without the guest ladders): `python3 fast_path/option_replay.py --lib3 '' --calls 16 --seeds 15 --out fast_path/results/option_replay_C.json` and `python3 fast_path/option_replay.py --lib3 '' --calls 8 --seeds 15 --out fast_path/results/option_replay_8calls.json`. Also reads `paired_comparison_3/parallel/ctde_logbook_seed.json`. With `--lib3 ''` the 24 missing entries are filled from stage ratios or the size law and the status is `provisional`, as in the committed files.
3. Option grades with the library completed: `python3 fast_path/option_replay.py` (defaults `--lib3 fast_path/results_lib3 --calls 16 --seeds 15 --out fast_path/results/option_replay.json`). Only records with role `missing` are merged; when no entry is filled the status becomes `final`. No committed output of this final run exists in the folder.
4. Packages: Python 3 standard library only.

Note: the committed `results/option_replay.json` and `results/option_replay_8calls.json` were written by an earlier version of `option_replay.py` without the CTDE_P2 arm (10 grade rows); the current script writes the 13-row layout of `results/option_replay_C.json`. Running step 3 overwrites `results/option_replay.json`.

`results_lib3/` (run-time library): the per-compound JSON records are themselves the measured data; they are read directly by step 3. A script comparing the three repeat ladders (MoS2-1T, ZrS2-1T, WS2-1T) with the grn061 records is not in the repository.

**Re-run the computation (`results_lib3/`).**

1. Inputs: the comparison No. 2 decks `paired_comparison_2/inputs/<compound>.f1.in`, `.f2.in`, `.f3.in` (8x8 supercells) and `paired_comparison_2/inputs/manifest2.json`; task list `fast_path/compounds.txt` (14 lines: 11 `missing`, 3 `repeat`; line index = array task id). No input builder is needed.
2. Pseudopotentials: GBRV ultrasoft PBE, downloaded from the GBRV site by `paired_comparison_3/parallel/stage_and_submit3.sh`: `ti_pbe_v1.4.uspp.F.UPF`, `zr_pbe_v1.uspp.F.UPF`, `hf_pbe_v1.uspp.F.UPF`, `mo_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, `te_pbe_v1.uspp.F.UPF`. No hash file for these is in the folder.
3. Staging: a run directory `$SCRATCH/mpt_lib3` with `inputs/`, `pseudos/`, `logs/`, `results/`, plus `library_ladder.py`, `library.sbatch`, `compounds.txt` and `qe_retry.py` copied in (`stage_and_submit3.sh` does this over SSH).
4. Submission: `sbatch --export=ALL,MPT_LIB_ROOT=$SCRATCH/mpt_lib3 fast_path/library.sbatch` from the run directory. Request: `--account=<account> --partition=<partition> --qos=<qos>` (a granite guest partition), `--constraint=gen` (the AMD node family of grn061), 1 node, 16 tasks, 180 GB, 72 h, `--requeue`, `--array=0-13`. Modules: `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`.
5. Each task runs `library_ladder.py` (no arguments): `pw.x` F1, F2, F3 with `mpirun -np 16 --bind-to none pw.x -nk 1`, timed by `/usr/bin/time -v`; on a solver failure `qe_retry.py` supplies the next diagonalisation. A requeued task skips converged stages. Records go to `$SCRATCH/mpt_lib3/results/<compound>.json` (host, processor model, wall time, peak per-rank memory, F3 gap).
6. Collection: copy `results/*.json` into `fast_path/results_lib3/` (no collection script is in the repository), then run step 3 of the re-analysis.
7. Observed cost: recorded call wall times sum to 969,455 s (269 task-hours at 16 cores, about 4,300 core-hours), excluding time lost to preemption; longest ladder TiTe2-2H, 46.5 h; five tasks were requeued once after preemption (MoSe2-2H, MoTe2-2H, TiTe2-2H, ZrS2-2H, ZrTe2-2H).

**Outputs.**

- `fast_path/results/replay_validation.json`
- `fast_path/results/option_replay.json`, `fast_path/results/option_replay_8calls.json`, `fast_path/results/option_replay_C.json`
- `fast_path/results_lib3/<compound>.json` (14 files)
- `fast_path/FAST_PATH.md` (summary)

**Checks.**

- `replay_validation.json`: 33 campaigns; same call set in 31, same order in 28; bill error median 0.88%, worst 4.14%; computing-centre ratio 1.149 replayed against 1.133 measured; paired bill sign agrees in 13 of 15.
- `option_replay_C.json` (16 calls, 15 seeds, provisional): CEDT_P4 without mask H ratio 1.157, PW60 10/15; with the 25% proportional mask 1.013, 7/15, timing identification 0.26; CTDE_P2 1.029, 9/15; CTCE 1.348; DTDE median makespan 30.2 h.
- `results_lib3/`: all 14 ladders finished with F1 to F3 converged on AMD EPYC 9654P nodes; for example MoSe2-2H F3 gap 1.684 eV, WS2-2H 2.002 eV.
- Known limits: run times depend on the processor model, so library entries from guest nodes and grn061 are comparable only within one node family; guest jobs can be preempted; the replay does not model new solver failures or contention beyond the measured 2 to 11%.

### `vacancy_barriers/`: force-field rung, vacancy kinetic Monte Carlo (kMC) applicability, DFT and Janus NEB barrier checks, and the kMC rung in the twin

Level: mixed. Force-field and kMC runs measured on the DGX Spark (NVIDIA GB10 GPU for MACE-MP-0; one aarch64 core for kMC). DFT NEB runs measured on CHPC notchpeak guest nodes (32 MPI ranks per task). Twin runs (`twin_kmc/`, `floor_125C/`) are simulated (simulated node-hours) on the DGX and on a notchpeak guest node. Registered predictions: `PREDICTION.md`, `dft_neb/PREDICTION.md`, `janus_neb/PREDICTION.md`, `GOAL_CHANGE.md`, `floor_125C/PREDICTION.md`.

**Re-analyse from the committed records (no new compute).** Packages: Python 3 with numpy and matplotlib (top level), numpy (`dft_neb/`), standard library only (`janus_neb/`). Each script overwrites its committed output; compare with a version-control diff.

1. `results` (force-field and kMC grading): `python3 vacancy_barriers/analyze.py` (no arguments). Reads `dft_campaign/results/outcomes.jsonl`, `vacancy_barriers/results/ff_rung.jsonl`, `results/vacancy_neb.jsonl`, `results/kmc_runs.jsonl`; writes `results/analysis.json` and `results/fig_cost_vs_size.png`.
2. Barrier disclosure probe: `python3 vacancy_barriers/disclosure_probe.py` (no arguments). Reads `results/kmc_runs.jsonl`; writes `results/disclosure_probe.json`.
3. `dft_neb`: `python3 vacancy_barriers/dft_neb/analyze_neb.py`. Reads `dft_neb/results_dft/<compound>.json`, `dft_neb/inputs/manifest.json` and `results/vacancy_neb.jsonl`; writes `dft_neb/results_dft/grading.json` (N1 to N5).
4. `janus_neb`: `python3 vacancy_barriers/janus_neb/analyze_janus.py`. Reads `janus_neb/results/<compound>_<face>.json`; writes `janus_neb/results/grading.json` (J0 to J4). Raw `neb.out`, `neb.dat` and gap outputs are in `janus_neb/results/outputs/raw.tgz`.

**Re-run the computation.**

1. Force-field rung (Test A): `python3 vacancy_barriers/ff_rung.py` on a CUDA GPU with `mace-torch` and ASE (`mace_mp(model="medium", device="cuda", default_dtype="float32")`). Reads the 30 CIFs in `prior_predictive/candidates/`; appends to `results/ff_rung.jsonl`. The script skips compounds already present, so move the committed file aside before a rerun. Package versions are not recorded in the repository.
2. MACE vacancy NEB (Test B, stage 1): `python3 vacancy_barriers/vacancy_neb.py`, same environment; needs `results/ff_rung.jsonl`; appends to `results/vacancy_neb.jsonl` (4x4 supercells, 3-image climbing-image NEB, IDPP start, fmax 0.1 eV/A). Also resume-safe, so move the committed file aside first.
3. kMC (Test B, stage 2): `python3 vacancy_barriers/run_kmc.py`. Compiles `vac_kmc.c` with `gcc -O2 -lm` to `/tmp/vac_kmc`, deletes and rewrites `results/kmc_runs.jsonl` (30 compounds x L = 24, 48; 1000 K, 2% vacancies, 1 s target, cap 200,000 events, seed 7). Direct use: `vac_kmc Ea Eb T L conc t_end max_events seed`.
4. Then re-analysis steps 1 and 2. Observed cost: steps 1 to 3 ran within 25 min on the DGX; a 200-step MD run takes 2.2 to 5.9 s, a relaxation under 2 s.

`dft_neb/` (PBE check of seven MACE barriers):

1. Inputs: `python3 vacancy_barriers/dft_neb/make_neb_inputs.py` (numpy only). Reads `rescreen_3x3/inputs/<compound>.f2.in`; writes `dft_neb/inputs/<compound>.ini.in`, `.fin.in`, `.neb.tmpl` and `inputs/manifest.json` (3x3 supercells, PBE, 40/320 Ry, cold smearing 0.015 Ry, 3x3x1 k-points, 5 images, path_thr 0.1 eV/A).
2. Pseudopotentials: GBRV 1.5 ultrasoft PBE, downloaded by `dft_neb/submit_neb.sh` from the GBRV site: `ti_pbe_v1.4.uspp.F.UPF`, `zr_pbe_v1.uspp.F.UPF`, `hf_pbe_v1.uspp.F.UPF`, `mo_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, `te_pbe_v1.uspp.F.UPF`. No hash file is in the folder.
3. Staging and submission: `submit_neb.sh` creates `$SCRATCH/mpt_neb/{inputs,results,pseudos}`, copies `run_neb.py`, `neb.sbatch` and `inputs/*`, runs `sbatch --test-only`, and submits when `MPT_NEB_SUBMIT=1`, with `--account=<account> --partition=<partition> --qos=<qos> --export=ALL,MPT_NEB_ROOT=$SCRATCH/mpt_neb`. `neb.sbatch`: 1 node, 32 tasks, 96 GB, 48 h, `--array=0-6`, `--requeue`; modules `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`, `OMP_NUM_THREADS=1`.
4. Each task runs `run_neb.py`: `pw.x` relaxations of both end states, then `neb.x` (`mpirun -np 32 ... -nk 2`, pools set by `MPT_NEB_NK`), restarting from the `.path` file after a requeue; writes `results/<compound>.json`.
5. Collection: `collect_neb.sh` copies `results/*.json` into `dft_neb/results_dft/`, the `.neb.out`, `_neb.dat` and logs into `dft_neb/results_dft/outputs/`, then runs `analyze_neb.py`. Only the `_neb.dat` profiles are committed under `outputs/`.
6. Observed cost: 2.0 to 4.3 h per task, 21.6 task-hours in total (about 690 core-hours), no requeues.

`janus_neb/` (Janus MXY layers and four single-layer references, 16 tasks):

1. Manifest: `python3 vacancy_barriers/janus_neb/make_janus_inputs.py`. Reads `stacking_study/results_2088961/stacking_summary.json`; writes `janus_neb/inputs/manifest.json` (start cells and the 16 tasks). Decks are generated on the node by `run_janus.py`.
2. Pseudopotentials: the Mo, W, S, Se and Te GBRV files listed above (`submit_janus.sh` downloads them).
3. `submit_janus.sh` stages to `$SCRATCH/mpt_janus` and submits when `MPT_JANUS_SUBMIT=1` (same placeholders, `MPT_JANUS_ROOT`). `janus.sbatch`: 1 node, 32 tasks, 96 GB, 48 h, `--array=0-15`, `--requeue`; same modules.
4. `run_janus.py` per task: 1x1 in-plane vc-relax (45/360 Ry, 12x12x1), PBE gap from scf 12x12x1 and nscf 18x18x1 with dipole correction, 3x3 end-state relaxations and `neb.x` with the `dft_neb` settings; writes `results/<compound>_<face>.json`.
5. Collection: `collect_janus.sh` copies the JSON records, packs raw outputs into `results/outputs/raw.tgz`, and runs `analyze_janus.py`. Observed cost: 1.2 to 3.1 h per task.

`twin_kmc/` (simulated; imports `prior_predictive/simulator.py` and `centralization_surface/{surface,tau_diagnostic}.py`; numpy):

1. kMC rung transects (120 worlds, 21 tau points), one run per committed file:
   `python3 vacancy_barriers/twin_kmc/kmc_rung.py --variant base --worlds 120 --npts 21` (add `--size-adj` for `transects_base_sizeadj.json`);
   `... --variant kmc --clip C --classes sizebar --worlds 120 --npts 21` for C = 0.5, 1, 1.5;
   `... --variant kmc --clip 1 --classes bar --worlds 120 --npts 21`, and both `clip 1` variants with `--size-adj`. Output `twin_kmc/results/transects_<tag>.json`.
2. Vacancy-immobility goal (needs `dft_neb/results_dft/grading.json`): `python3 vacancy_barriers/twin_kmc/vacancy_goal.py --rule R --classes K --worlds 200 --npts 11` for R in {mean, family} and K in {sizebar, bar}; output `twin_kmc/results/vacancy_goal_<R>_<K>.json`. `--procs` defaults to 16. These ran on the DGX; the kMC rung transects and the disclosure probe together took about 15 min.

`floor_125C/` (simulated; 1.70 eV floor):

1. Stage copies of `prior_predictive/`, `centralization_surface/` and `vacancy_barriers/` under `$MPT_FLOOR_ROOT/code` (no staging script is in the repository), then `sbatch --account=<account> --partition=<partition> --qos=<qos> --export=ALL,MPT_FLOOR_ROOT=<dir> vacancy_barriers/floor_125C/run_floor.sbatch` (1 node, 32 tasks, 48 GB, 6 h, `--requeue`; module `python/3.10.3`). It runs `vacancy_goal.py --rule {mean,family} --e-min 1.70 --worlds 200 --npts 11 --procs 16` side by side and copies the JSON and logs to a results directory in the home area.
2. `floor_125C/collect_floor.sh` (run from the repository root) fetches them into `twin_kmc/results/`. Observed cost: about 4 min on 32 cores. The same results can be produced locally with the two `vacancy_goal.py` commands.

**Outputs.**

- `results/analysis.json`, `results/fig_cost_vs_size.png`, `results/disclosure_probe.json`, `results/ff_rung.jsonl`, `results/vacancy_neb.jsonl`, `results/kmc_runs.jsonl`
- `dft_neb/results_dft/<compound>.json` (7), `dft_neb/results_dft/grading.json`, `dft_neb/results_dft/outputs/*_neb.dat`
- `janus_neb/results/<compound>_<face>.json` (16), `janus_neb/results/grading.json`, `janus_neb/results/outputs/raw.tgz`
- `twin_kmc/results/transects_*.json` (8), `twin_kmc/results/vacancy_goal_*.json` (6, two with `_emin1.70`)
- Summaries: `RESULTS.md`, `RESULTS_KMC_RUNG.md`, `RESULTS_VACANCY_GOAL.md`, `janus_neb/RESULTS.md`, `floor_125C/RESULTS.md`

**Checks.**

- `analysis.json`: QE F2 reference R^2 = 0.86 (n = 29); MACE MD R^2 = 0.65 (90 jobs, A1 fails); lattice constants within 3% for 28 of 29 (mean 0.7%); 1T versus 2H sign agrees 14 of 14; hop barriers 0.00 to 1.01 eV; kMC cost on size R^2 = 0.19 (60 runs), 0.95 with barriers.
- `disclosure_probe.json`: leave-one-compound-out R^2 own 0.21, one bit 0.69, tercile 0.75, 0.1 eV bins 0.88, exact 0.90; identification 0.067 (one bit) against a limit of 0.083; raw timing 0.68.
- `dft_neb/results_dft/grading.json`: PBE barriers WS2-2H 2.66, MoS2-2H 2.14, HfS2-1T 1.36, TiS2-1T 1.18, ZrTe2-1T 0.91, TiTe2-1T 0.85, MoS2-1T 1.55 eV; Spearman 0.643; stable spread 1.81 eV; N1 to N5 pass.
- `janus_neb/results/grading.json`: J0 pass (MoS2 2.16, WS2 2.66 eV), J1 fail (faces differ by 0.04 to 0.12 eV), J2 pass, J3 fail (Spearman 0.60), J4 fail (window share 1.00).
- `vacancy_goal_*.json`: G1 8 of 9 (mean) and 7 of 9 (family); G2 +0.100 and +0.0998; G3 +0.005 and +0.010. At 1.70 eV: F2 +0.126 (mean) and +0.153 (family).
- Known limits: MACE barriers sit 0.4 to 1.6 eV below the PBE values; kMC timings depend on the DGX core and use one seed per run; GPU MD timings are hardware specific; guest jobs can be preempted; twin numbers are simulated units.

### `governance_regrade/`: re-grading the 1,000-world hard-cap grid under relaxed acceptance margins and lowered thresholds

Level: analysis of committed records (re-grades the simulated prior-predictive grid `prior_predictive/results/raw_results_hardcap.json.gz`; no new simulation, all node-hours simulated units).

**Re-analyse from the committed records (no new compute).** Python 3 with numpy (matplotlib for the figure). Scripts resolve paths relative to their own folder, so they run from the repository root.

1. `python governance_regrade/regrade_governance.py` (no arguments). Reads `prior_predictive/results/raw_results_hardcap.json.gz` directly (gzip), grades every condition against its DTDE-P4 baseline per world, and writes `governance_regrade/governance_regrade.json`: `frozen` (preregistered margins), the option-A sweeps (`optA_hlabels_1.10`, `_1.05`, `_1.00`, `optA_hfail_0.04`, `optA_hlabels_1.05_hfail_0.04`), the execution-layer variants (`exec_gR20`, `exec_gR10`, `package_exec_gR10_hlabels_1.05`) and `optB_threshold_table`. It prints the top four contracts per scenario.
2. `python ceiling_diagnosis/make_figures.py` regenerates `governance_regrade/fig_governance.png`. This script also rewrites three other figures (`ceiling_diagnosis/results/fig_ceiling_decomposition.png`, `decision_maker_leakage/fig_dm_leakage.png`, `sociability_map/fig_sociability_map.png`) from their committed JSON records, which must be present.

**Re-run the computation.** Only the upstream grid involves simulation.

1. The hard-cap grid was produced by `prior_predictive/simulator.py` with the environment variable `MPT_HARD_CAP=1` (1,000 worlds x 10 conditions x 30 paired seeds, plus a 250-world eps sweep, 18 processes on a DGX Spark CPU). A command consistent with the script's argument parser is:
   `MPT_HARD_CAP=1 python prior_predictive/simulator.py --worlds 1000 --sweep-worlds 250 --procs 18 --out results/raw_results_hardcap.json`
   then `gzip prior_predictive/results/raw_results_hardcap.json`. `--out` is relative to `prior_predictive/`. The exact command line used is not in the repository.
2. Worlds are seeded by CRC32 of `card:world_id` in `prior_predictive/simulator.py`. The repository notes that the earlier soft-stop run predates this stable-seed derivation; whether the hard-cap grid was produced after the fix is not stated explicitly, so a rerun should be compared by distribution first, then record by record.
3. Then repeat the two re-analysis steps above.
4. The posterior re-grade in the addendum of `governance_regrade/RESULTS.md` is produced by `pilot/posterior_regrade.py` (300 worlds per scale), outside this folder.

**Outputs.**
- `governance_regrade/governance_regrade.json`
- `governance_regrade/fig_governance.png`

**Checks.**
- CEDT-P4 P(win-win), preregistered metrics: 0.041. H labels/nh margin 10 %: 0.047; 5 %: 0.049; 0 %: 0.049; failure tolerance 0.04: 0.041.
- Execution-layer R gain 20 %: 0.083; 10 %: 0.115; package (execution gain 10 %, H margin 5 %, failure tolerance 0.04): 0.175.
- Option B: under preregistered metrics no contract reaches any threshold from 0.90 down to 0.50.
- Posterior addendum (from `pilot/`): CEDT-P4 with the renegotiated package 0.713 (x10), 0.817 (x100), 0.813 (x300).
- The re-grade is deterministic and bit-identical given the committed input. Leakage limits and margins are hard-coded in `regrade_governance.py` (`LIMITS`, `C_CANDS = 30`).

### `hybrid_arms/`: hybrid-mix, negotiation-only (ALT) and broker-collusion arms graded beside the four standard topologies

Level: simulated (wide base prior at x1 task scale) and simulated on measured inputs (measurement-informed posterior at x100 scale). The machine used for the committed run is not in the repository. All node-hours are simulated units.

**Re-analyse from the committed records (no new compute).**

1. Regenerate the figure from the committed per-world records:
   `python hybrid_arms/make_figure.py`
   Input: `hybrid_arms/hybrid_results.json` (keys `wide_prior_x1` and `posterior_x100`, each a list of 300 per-world dictionaries keyed by condition). Output: `hybrid_arms/fig_hybrid_arms.png` (written next to the script; any working directory).
2. The summary table in `hybrid_arms/RESULTS.md` and `hybrid_arms/hybrid_run.log` is printed only by `hybrid_study.py` after a full run; no separate table script is committed. The same means can be read from the JSON, for example:
   `python -c "import json,numpy as np; d=json.load(open('hybrid_arms/hybrid_results.json')); r=d['posterior_x100']; print({c: round(np.mean([w[c]['win_win_redesigned'] for w in r]),3) for c in d['conds']})"`
   (replace `win_win_redesigned` by `leak_ok`, `pw_rate`, `win_win`, `r_mi_auc` or `h_rank_corr`; the labels-per-node-hour ratio is the per-world mean of `labels_per_nh` divided by the `DTDE_P4` value).

Python packages: numpy, scipy (imported by the simulator), matplotlib.

**Re-run the computation.**

1. From the repository root:
   `python hybrid_arms/hybrid_study.py > hybrid_arms/hybrid_run.log`
   Environment variables read: `HYB_WORLDS` (default 300), `HYB_PROCS` (default: all CPU cores), `MPT_HARD_CAP` (set to `1` by the script unless already defined; keep it at `1` to reproduce the strict 500 node-hour budget per campaign).
2. The script imports `prior_predictive/simulator.py` (30 paired seeds per world fixed by its constant `S`, 80 rounds at most) and runs 13 conditions (CTCE-P0, DTDE-P4, CTDE-P2/P3/P4, CEDT-P2/P3/P4, HYB-P2/P3, ALT-P4, and the two collusion variants; P3 uses epsilon = 2) on identical worlds, first on the `base` prior card at x1, then on a `posterior` card at x100 with `OVERHEAD_NH = 0.02`.
3. Committed measured inputs read: `stage2_twin_fit/twin_fit.json` (measured cost coefficients, electron exponent, residual spread), `pilot/results/pilot_fit.json` (parallel-efficiency exponent and quirk spread), and `prior_predictive/candidates/candidates.json` (public candidate metadata).
4. Random-seed handling: every world is drawn from `numpy.random.default_rng(crc32("<card>:<world>"))`, and the posterior perturbation from `crc32("post:<card>:<world>")`; all per-seed noise fields are drawn inside the world, so every condition shares common random numbers. No global random state is used.
5. Output: the script overwrites `hybrid_arms/hybrid_results.json` (hard-coded path next to the script). Runtime and hardware are not in the repository.

**Outputs.**

- `hybrid_arms/hybrid_results.json` (per-world records, both settings)
- `hybrid_arms/hybrid_run.log` (printed summary table)
- `hybrid_arms/fig_hybrid_arms.png`

**Checks.**

- Posterior x100, redesigned metrics: P(win-win) for CEDT-P4 0.920 (wide prior x1: 0.160); CEDT-P3 and HYB-P3 0.510; every other arm at most 0.003.
- P(all leakage limits hold): CEDT-P4 and CTDE-P4 1.000; ALT-P4 0.997 (wide prior 0.957); CEDT-P3 0.613 and HYB-P3 0.607, both 0.000 under collusion.
- Labels per node-hour relative to DTDE-P4 (posterior): CTCE-P0 1.498, CEDT-P2 1.401, HYB-P2 1.400, CEDT-P3 and HYB-P3 1.282, CEDT-P4 1.179, ALT-P4 1.000.
- Seeding is fixed, so a rerun with the same package versions is expected to reproduce `hybrid_run.log` exactly; the repository does not record a verified rerun or the package versions.
- Limits stated in `RESULTS.md`: the hybrid interaction is modelled at the information level only, ALT is a single-channel stand-in for alternating offers, and collusion is scored rather than simulated as strategic behaviour.

### `contention_transfer_bench/`: co-tenant contention against task size, and cost-transfer probes on a defect supercell and a heterobilayer

Level: measured on hardware (CHPC granite node grn061, owner partition, one 64-core allocation with 380 GB node memory; two 32-rank `pw.x` jobs share the node in the co-tenant runs; CPU only).

**Re-analyse from the committed records (no new compute).** Python 3 with `numpy`.

1. `python3 contention_transfer_bench/analyze_bench.py` (no arguments). Reads `contention_transfer_bench/results/bench_results.jsonl`; writes `contention_transfer_bench/results/bench_analysis.json` and prints it.
   - Contention: mean co-tenant wall over mean solo wall for the TiS2_1T job at each scale (s1, s2, s3), over 2 repeats.
   - Transfer: power law `wall = A × nelec^p` fitted to the solo and partner MX2 points of the same job, then measured over predicted wall for the two probes.
2. `paired_comparison_1/plot_live.py` reads `bench_analysis.json` for its fourth panel (outside this folder).

**Re-run the computation.**

1. Inputs:
   - Contention runs use the 6×6 k-grid supercell decks of `scale_validation/inputs/` (`TiS2_1T_s{1,2,3}_k6`, `MoSe2_2H_s{1,2,3}_k6`), built by `scale_validation/build_scale_inputs.py` (see that folder).
   - Transfer probes: `python3 contention_transfer_bench/build_transfer_inputs.py` (no arguments) writes `contention_transfer_bench/inputs/MoS2_3x3_Svac.pw.in` (3×3 MoS2 with one S vacancy, 53 atoms) and `contention_transfer_bench/inputs/MoS2_WS2_hetero_2x2.pw.in` (2×2 bilayer with the second-layer Mo replaced by W, 24 atoms). It reads the relaxed MoS2_2H lattice and positions from `dft_campaign/results/campaign_summary.json` and the vacuum from `prior_predictive/candidates/candidates.json` (both in the repository). Settings: ecutwfc 45 Ry, ecutrho 360 Ry, cold smearing 0.015 Ry, conv_thr 1e-7, 4×4×1 grid.
2. Pseudopotentials: GBRV ultrasoft PBE (`mo_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`, plus `ti_pbe_v1.4.uspp.F.UPF` and `se_pbe_v1.uspp.F.UPF` for the contention decks). Hashes: `pilot/results/pseudos_manifest.txt`. Not in the repository; download from the GBRV site.
3. Software: Quantum ESPRESSO 7.4, modules `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`. Python 3.10 is required: a first submission failed under the cluster's default Python 3.6 (`time.time_ns` missing; log `contention_transfer_bench/results/bench_1919941.log`, no QE run started).
4. Staging: create a directory `$SCRATCH/mpt_bench` containing `bench.py`, `bench.sbatch`, `inputs/` (the 2 probe decks plus the 8 decks of `scale_validation/inputs/`) and `pseudos/`. `paired_comparison_1/stage_and_submit.sh` performs this staging over SSH together with another job; its connection set-up is site-specific.
5. Submit: `sbatch --export=ALL,MPT_BENCH_ROOT=$SCRATCH/mpt_bench bench.sbatch` (1 node, 64 tasks, 4 h wall; replace `--account`, `--partition`, `--qos` by `<account>`, `<partition>`, `<qos>`). `bench.sbatch` sets the cost guard `MPT_BENCH_NH_CAP=5` and runs `python3 bench.py`.
6. Run order inside `bench.py`: for each of 2 repeats and each scale s1, s2, s3: TiS2_1T solo (32 ranks, `-nk 2`); then MoSe2_2H of the same scale started, 2 s later TiS2_1T started alongside it (32 + 32 ranks); then the two probes solo. Each run appends one record (wall, convergence, RAM per process, electrons) to `results/bench_results.jsonl`.
7. Collect `results/bench_results.jsonl` and `bench_<jobid>.log` into `contention_transfer_bench/results/` (`paired_comparison_1/collect_live.sh` does this), then run `analyze_bench.py`.
8. Observed cost: job 1919944, 22 min 30 s wall, 20 SCFs; the driver's own tally is 0.238 node-hours (`ranks / 64 × wall`, final log line), while `contention_transfer_bench/RESULTS.md` reports about 0.35 node-hours including the co-tenant pairs.

**Outputs.**

- `contention_transfer_bench/results/bench_results.jsonl`
- `contention_transfer_bench/results/bench_analysis.json`
- `contention_transfer_bench/results/bench_1919944.log` (completed run), `contention_transfer_bench/results/bench_1919941.log` (failed first submission)
- Summary: `contention_transfer_bench/RESULTS.md`

**Checks.**

- All 20 SCFs converged.
- Co-tenant interference factors: s1 1.064, s2 1.110, s3 1.076 (solo 3.12 s, 26.55 s, 141.2 s). Interference stays between 6 % and 11 % and does not grow with size up to 27 atoms and 216 electrons.
- MX2 power-law exponent 1.648. Transfer ratios (measured over predicted): `MoS2_3x3_Svac` 0.527 (161 s against 306 s, 462 electrons); `MoS2_WS2_hetero_2x2` 0.438 (36 s against 82 s, 208 electrons).
- Limits: single-node contention only (no inter-node measurement); 2 repeats per scale; absolute times and interference depend on the node's memory bandwidth and on any other load present during the run.

### `paired_comparison_1/`: preregistered live paired comparison of CEDT-P4 against DTDE with Quantum ESPRESSO on 3x3 MX2 supercells, plus executed timing attacks on the wire log

Level: measured on hardware. One whole node (granite `grn061`, 64 cores, CPU only; the node's GPU was not used), single SLURM allocation, 480 `pw.x` calls, 19.8 h wall, 9.41 node-hours.

**Re-analyse from the committed records (no new compute).** Python 3.8 or later; `analyze_live.py` uses the standard library only, `wire_attack.py` needs `numpy`, `plot_live.py` needs `numpy` and `matplotlib`. All three resolve paths relative to their own directory, so they can be run from the repository root. Each one overwrites its committed output in `paired_comparison_1/results/`; compare against the committed version (or run on a copy of the folder).

1. Preregistered grading (fixed before submission): `python3 paired_comparison_1/analyze_live.py`. Reads `paired_comparison_1/results/campaigns.jsonl`, prints the per-seed node-hours-to-first-qualifier table and writes `paired_comparison_1/results/live_grading.json`. Criteria in the script: R passes if CEDT-P4 has lower node-hours-to-first-qualifier in at least 0.60 of the paired seeds (a campaign without a qualifier scores its total spend), with a one-sided sign test; H passes if pooled valid F2 labels per node-hour are at least 1.05 times DTDE and the failure rate is at most DTDE + 0.04.
2. Executed timing attacks: `python3 paired_comparison_1/wire_attack.py`. Reads `paired_comparison_1/results/campaigns.jsonl` (it uses only the wire fields `cls` and `wall_s` per opaque ID as attacker input, and the `candidate` field only as scoring truth); writes `paired_comparison_1/results/wire_attack_results.json`. Leave-one-seed-out per arm: (a) exact candidate identity by nearest median log wall time per class, limit prior + 0.05; (b) membership inference AUC, limit 0.60. The 480-row wire view itself is `paired_comparison_1/results/wire_log.jsonl`.
3. Figure: `python3 paired_comparison_1/plot_live.py`. Reads `campaigns.jsonl`, `live_grading.json`, `wire_attack_results.json` and `contention_transfer_bench/results/bench_analysis.json` (panel D, co-tenant contention, produced by the separate `contention_transfer_bench/` study); writes `paired_comparison_1/results/fig_live_comparison.png`.

**Re-run the computation.**

1. Inputs: `python3 paired_comparison_1/build_live_inputs.py` (no arguments). Reads `dft_campaign/results/campaign_summary.json` (relaxed 1x1 geometries and lattice constants) and `prior_predictive/candidates/candidates.json`; writes 87 decks `paired_comparison_1/inputs/<name>.f{1,2,3}.in` and `inputs/manifest.json` (29 candidates; HfSe2_2H skipped, no converged relaxation). Decks: 3x3 in-plane supercells, `ibrav = 4`, c = 18 Å, PBE via GBRV ultrasoft pseudopotentials, cold smearing 0.015 Ry, `mixing_beta = 0.3`, `ecutrho = 8 ecutwfc`. F1 SCF 40 Ry, 2x2x1 k, `conv_thr 1e-6`; F2 SCF 45 Ry, 4x4x1 k, `1e-8`; F3 NSCF 45 Ry, 6x6x1 k, `nbnd = nelec/2 + max(8, 0.2 nelec)`. Full setup table: `paired_comparison_1/JOB_SETUP.md`.
2. Pseudopotentials: GBRV 1.5 USPP files `ti_pbe_v1.4`, `zr_pbe_v1`, `hf_pbe_v1`, `mo_pbe_v1`, `w_pbe_v1.2`, `s_pbe_v1.4`, `se_pbe_v1`, `te_pbe_v1` (`.uspp.F.UPF`), from `https://www.physics.rutgers.edu/gbrv/`, placed in `<staging dir>/pseudos/` (the driver symlinks this into every work directory). Not redistributed in the repository.
3. Software: modules `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`. Python 3.8 or later is required on the compute node (the driver uses the walrus operator, and `analyze_live.py` uses `math.comb`; a first submission under the cluster default Python 3.6.8 died with a `SyntaxError` before any QE call, log `results/live_1919942.log`). `/usr/bin/time -v` must exist (peak RSS per call).
4. Staging and submission: `paired_comparison_1/stage_and_submit.sh` copies `live_campaign.py`, `live.sbatch`, `analyze_live.py`, `inputs/` and the pseudopotentials to `$SCRATCH/mpt_live` on the login node through an existing SSH ControlMaster (`CHPC_USERNAME` must be set; the login helper is not in this folder), then submits `sbatch --export=ALL,MPT_LIVE_ROOT=$SCRATCH/mpt_live,MPT_LIVE_NH_CAP=100 live.sbatch`. The same script also stages and submits the separate `contention_transfer_bench/` job first; to reproduce only this study, run the live part by hand.
5. `live.sbatch`: `--account=<account> --partition=<partition> --qos=<qos>`, `--nodes=1 --ntasks=64 --time=120:00:00` (whole node; node-hours are charged as wall x ranks / 64, which assumes whole-node accounting). It sets `MPT_LIVE_SEEDS=10`, `MPT_LIVE_MAX_CALLS=24`, `MPT_LIVE_CAMPAIGN_NH=5.0` and defaults `MPT_LIVE_NH_CAP=100`, then runs `python3 live_campaign.py`. Memory per call is not requested explicitly.
6. Driver `live_campaign.py`: for seed s in 0..9 the 29 candidates are shuffled with `random.Random(1000 + s)`; both arms replay the same order and inputs (DTDE first on even seeds, CEDT-P4 first on odd seeds). Execution configs (`mpirun -np`, `pw.x -nk`): DTDE 32/1 for every class; CEDT-P4 F1 16/1, F2 32/2, F3 32/4. Each candidate runs F1, F2, F3; an F1/F2 non-convergence stops that candidate; the F3 PBE gap qualifies if in [1.0, 2.0] eV. A campaign stops at 24 calls, 5 nh, or the global cap. Opaque IDs are `sha1("mpt-live-2026-09-09:<seed>:<name>")[:10]`. Writes `results/campaigns.jsonl`, `results/wire_log.jsonl` (appended, so start from an empty `results/`), `results/progress.json`, `results/live_summary.json`, and `live_<jobid>.log`; wavefunction directories are deleted after each candidate.
7. Collection: `paired_comparison_1/collect_live.sh` copies the four result files and `live_*.log` from `$SCRATCH/mpt_live` into `paired_comparison_1/results/` (and the bench results into `contention_transfer_bench/results/`). Then run the three analysis steps above.

Observed cost: 480 QE calls, 9.41 node-hours (cap 100), 19 h 49 min wall, 0.36 to 0.66 nh per campaign.

**Outputs.**
- `paired_comparison_1/results/campaigns.jsonl` (20 campaigns with per-job records and truth)
- `paired_comparison_1/results/wire_log.jsonl` (480 wire rows)
- `paired_comparison_1/results/live_summary.json`, `progress.json`, `live_1919945.log`
- `paired_comparison_1/results/live_grading.json`
- `paired_comparison_1/results/wire_attack_results.json`
- `paired_comparison_1/results/fig_live_comparison.png`

**Checks.**
- Every campaign made 24 calls and 8 valid F2 labels; total 480 calls, 9.411 nh, 19.82 h wall (`live_summary.json`).
- R: CEDT-P4 wins 6 of 10 pairs (seeds 1, 2, 4, 6, 8, 9), `pw_rate` 0.60, one-sided sign test p = 0.377; passes the bar exactly at the boundary.
- H: labels per node-hour ratio 1.005 (required 1.05), fail; failure rate 0.029 (CEDT-P4) against 0.033 (DTDE), pass. `preregistered_success: false`.
- Timing attacks: 27 candidates reached across campaigns (prior 0.037, identity limit 0.087); identity accuracy 0.9625 (n = 80) and membership AUC 1.000 in both arms; both limits breached. The timing channel was preregistered as accept-and-measure, so this is reported, not graded as a pass.
- Limits: wall times depend on the node, its load and the MPI build; the node partition was empty at submission and no co-tenant was recorded, so the timing fingerprints reflect a quiet dedicated node. The identity attack assumes labeled reference timings for the public candidate pool. Exact per-seed winners can change under re-run because the paired differences are a few percent of node-hours.

### `paired_comparison_2/`: preregistered live paired comparison No. 2 (DTDE against CEDT-P4 with one memory bit) as memory-reservation packing policies, Quantum ESPRESSO on 8x8 MX2 supercells, with pre-study, void first attempt, F3 repair pass, fallback regrade and timing attacks

Level: measured on hardware (granite node `grn061`, 64 cores, 380 GB, CPU-only `pw.x`, GPU unused; one whole-node allocation per window), except `prestudy/`, which is simulated (pure NumPy scheduler model, no QE). Arms differ only in the memory reserved per job; billing is TRES-style, billed pc-nh = wall_h x max(16/64, reserved_GB/380).

**Re-analyse from the committed records (no new compute).** Python 3.8 or later (`math.comb`). `analyze_live2.py`, `fallback_regrade.py`, `repair_regrade.py`, `deviation_comparison.py` use the standard library only; `wire_attack2.py` and `prestudy/prestudy.py` need `numpy`; `plot_final.py` and `prestudy/make_figure.py` need `matplotlib`. Every script resolves defaults relative to its own directory and overwrites its committed output, so compare against the committed version (or work on a copy of the folder). Run from the repository root in this order:

1. Preregistered grading (committed before submission): `python3 paired_comparison_2/analyze_live2.py` (optional argument: results directory). Reads `paired_comparison_2/results/campaigns.jsonl` (33 campaigns: 15 DTDE, 15 CEDT_P4, 3 CEDT_P4_UNMASKED replays), writes `paired_comparison_2/results/graded.json`. Rules: PW60 (CEDT wins a pair iff it has a first qualifier and DTDE has none or a higher billed cost to it; both-none pairs are non-wins; one-sided sign test); H = pooled F2 labels per billed pc-nh, CEDT/DTDE >= 1.05; masking price on seeds 0 to 2. On the as-run transcript PW60 is 0/15 because no F3 produced a gap (see Checks).
2. Fallback regrade (deviation D-2026-09-22-B, folded 1x1 gap at F2 completion): `python3 paired_comparison_2/fallback_regrade/fallback_regrade.py paired_comparison_2/results/campaigns.jsonl paired_comparison_2/fallback_regrade/results`. Give the output directory: the default `results_midrun/` is the location of an earlier interim grade that is not part of this repository. Reads `gap_1x1_ev` from `inputs/manifest2.json` (13 of 29 candidates have none).
3. Repair regrade (amendment D-2026-09-22-A, primary R-side grade): `python3 paired_comparison_2/f3_repair/repair_regrade.py paired_comparison_2/results/campaigns.jsonl paired_comparison_2/f3_repair/results_raw/repair_gaps.json paired_comparison_2/f3_repair/results`. The second argument must be given: the default `paired_comparison_2/results_repair/repair_gaps.json` is the on-cluster location and is not in the repository. Each failed F3 record is replaced by the measured 8x8 gap and cost (f3_wall + hold)/3600 x frac(original res_gb), hold 300 s for masked CEDT campaigns. Writes `f3_repair/results/repair_graded.json`.
4. Deviation comparison (prediction P-2026-09-22, repair PW60 >= fallback PW60): `python3 paired_comparison_2/f3_repair/deviation_comparison.py paired_comparison_2/fallback_regrade/results/fallback_graded.json paired_comparison_2/f3_repair/results/repair_graded.json paired_comparison_2/f3_repair/results_raw/repair_gaps.json paired_comparison_2/f3_repair/results` (third argument again required). Writes `f3_repair/results/deviation_report.json`.
5. Timing attacks on the quantized wire log: `python3 paired_comparison_2/wire_attack2.py` (no arguments). Reads `results/wire_log.jsonl` (264 rows) and `inputs/manifest2.json`; recovers ground truth from the salted hash in `live2_campaign.py`; leave-one-seed-out identity attack (limit 1/29 + 0.05) and membership AUC (limit 0.60) per arm on successful F1/F2 rows. Writes `results/wire_attack_results.json`. Do not feed the void wire log to it.
6. Figure: `python3 paired_comparison_2/final/plot_final.py`; reads `f3_repair/results/repair_graded.json`, `f3_repair/results_raw/repair_gaps.json`, `inputs/manifest2.json`, `results/wire_attack_results.json`; writes `final/fig_attempt2_verdict.png`.
7. Pre-study (simulated): `python3 paired_comparison_2/prestudy/prestudy.py` reads `dft_campaign/results/outcomes.jsonl` (measured 1x1 walls and qualifier flags) and writes `prestudy/prestudy_results.json` (defaults 400 worlds, 20 pairs, 12 calls, scales 6,7,8, seed 20260911). Environment: `MPT_WORLDS`, `MPT_PAIRS`, `MPT_CALLS`, `MPT_SCALES`, `MPT_TAG` (file suffix); the variants are e.g. `MPT_CALLS=8 MPT_PAIRS=15 MPT_TAG=_c8p15`, likewise `_c8p20`, `_c12p15`. Then `python3 paired_comparison_2/prestudy/make_figure.py` writes `prestudy/fig_prestudy.png`. The `prestudy_results_postcofit*.json` files used refit priors (s 0.76 to 0.84, c 0.02 to 0.05 from the co-scheduling probe in `cofit_probe/`); the script version with those priors is not in the repository (the committed `prestudy.py` hard-codes the pre-probe priors s 0.35 to 0.50, c 0.05 to 0.12).

**Re-run the computation.**

1. Inputs: `python3 paired_comparison_2/build_live2_inputs.py` (no arguments). Reads the 3x3 decks and `manifest.json` in `paired_comparison_1/inputs/`, recovers the relaxed 1x1 motif, and writes 87 decks `paired_comparison_2/inputs/<name>.f{1,2,3}.in` plus `inputs/manifest2.json` (29 candidates, HfSe2_2H excluded; 192 to 384 atoms; RAM estimates 75 to 138 GB, median 98.9 GB, 14 high-bit). Decks: 8x8 supercells, `ibrav = 4`, PBE GBRV USPP, cold smearing 0.015 Ry, `mixing_beta = 0.3`, Davidson, `K_POINTS automatic 1 1 1` (not the Gamma trick). F1 SCF 40/320 Ry, `conv_thr 1e-6`; F2 SCF 45/360 Ry, `1e-8`; F3 NSCF 45/360 Ry, `nbnd = int(1.10 nocc) + 16`.
2. Pseudopotentials: GBRV `ti_pbe_v1.4`, `zr_pbe_v1`, `hf_pbe_v1`, `mo_pbe_v1`, `w_pbe_v1.2`, `s_pbe_v1.4`, `se_pbe_v1`, `te_pbe_v1` (`.uspp.F.UPF`) from `https://www.physics.rutgers.edu/gbrv/`, fetched by the staging script into `$SCRATCH/mpt_live2/pseudos/`; not redistributed.
3. Software: modules `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`; `mpirun -np 16 --bind-to none pw.x -nk 1` per job; `/usr/bin/time -v` for peak RSS. The driver imports `qe_retry.py` from the project root (staged alongside it).
4. Staging and submission: `paired_comparison_2/stage_and_submit2.sh` (needs `CHPC_USERNAME` and an existing SSH ControlMaster to the granite login node; the login helper is outside this project tree). It copies `qe_retry.py`, `live2_campaign.py`, `live2.sbatch`, `analyze_live2.py` and `inputs/` to `$SCRATCH/mpt_live2`, compiles the driver, and submits window A: `sbatch --export=ALL,MPT_LIVE2_ROOT=$SCRATCH/mpt_live2,MPT_SEED_LO=0,MPT_SEED_HI=7,MPT_W_CAP=280,MPT_QUANT=600 live2.sbatch`, then window B with `--dependency=afterany:<A>` and `MPT_SEED_LO=8,MPT_SEED_HI=14,MPT_W_CAP=240,MPT_QUANT=600,MPT_REPLAY_SEEDS=0:1:2`. Total cap 520 billed pc-nh.
5. `live2.sbatch`: `--account=<account> --partition=<partition> --qos=<qos> --nodes=1 --ntasks=64 --mem=0 --time=320:00:00`. `--mem=0` (whole-node memory) is required: without it the void first attempt received the 125 GB partition default.
6. Driver `live2_campaign.py` (default multi-campaign mode; leave `MPT_CAMPAIGN` unset and `MPT_MASK=fixed`): seed s shuffles the 29 candidates with `random.Random(2000 + s)`; DTDE first on even seeds, CEDT_P4 first on odd seeds; 8 calls per campaign, at most 3 open ladders, deepest-ready-first; campaign cap `MPT_CAMP_CAP` 25 pc-nh; window cap `MPT_W_CAP` (launch refused if the projected bill would cross it). Reservations: DTDE 1.10 x class maximum x stage factor (f1 0.85, f2 1.00, f3 1.05); CEDT_P4 uses the maximum of its bit half; packing budget 342 GB and 64 cores. CEDT completions become visible at the next 600 s boundary (`MPT_QUANT`) and are billed until then; replay seeds run as `CEDT_P4_UNMASKED`. Qualifier: F3 gap in [1.0, 2.0] eV. Writes `results/campaigns.jsonl`, `results/wire_log.jsonl` (appended: start from an empty `results/`), `results/progress.json`, `results/summary_w<lo>_<hi>.json`. The committed driver keeps each save directory until the ladder ends (the fix of the F3 bug) and also contains the solver-retry rule and the arms and options of comparison No. 3; the exact as-run attempt-2 driver revision is not in the repository.
7. F3 repair pass (only needed to reconstruct attempt 2; a re-run with the fixed driver measures F3 directly): `paired_comparison_2/f3_repair/submit_repair.sh` stages `repair_driver.py` and `repair.sbatch` and submits `sbatch --dependency=afterany:<window B> --export=ALL,MPT_LIVE2_ROOT=$SCRATCH/mpt_live2,MPT_REPAIR_CAP=80 f3_repair/repair.sbatch` (same module stack, `--ntasks=64 --mem=0 --time=144:00:00`). The driver takes every candidate with an F3 record in `results/campaigns.jsonl` (`MPT_REPAIR_SCOPE=attempted`, or `all`), runs F2 then F3 heaviest first, at most 2 streams within 342 GB, and writes `results_repair/repair_gaps.json`, `repair_progress.json` and `f3_outputs/`.
8. Collection: no collection script is in the repository; copy the result files listed under Outputs from `$SCRATCH/mpt_live2/` (and `results_repair/` into `f3_repair/results_raw/`), then run the re-analysis steps above.

Observed cost (attempt 2): window A 173.9 h wall, 107.3 billed pc-nh, 128 calls; window B 167.4 h wall, 101.1 pc-nh, 136 calls; repair pass about 2 d 3 h wall, 29.8 pc-nh, 18 candidates, cap not reached. Void attempt 1: about 56 node-hours wall, about 26 driver-billed pc-nh. Total about 264 of the 520 pc-nh cap.

**Outputs.**
- `paired_comparison_2/results/campaigns.jsonl`, `wire_log.jsonl`, `progress.json`, `summary_w0_7.json`, `summary_w8_14.json`, `graded.json`, `wire_attack_results.json`
- `paired_comparison_2/f3_repair/results_raw/repair_gaps.json`, `repair_progress.json`; `f3_repair/results/repair_graded.json`, `deviation_report.json`
- `paired_comparison_2/fallback_regrade/results/fallback_graded.json`
- `paired_comparison_2/void_run_1948457/` (void attempt records, `VOID_RUN.md`, two driver logs)
- `paired_comparison_2/final/RESULTS.md`, `fig_attempt2_verdict.png`; `paired_comparison_2/prestudy/prestudy_results*.json`, `fig_prestudy.png`, `RESULTS.md`

**Checks.**
- H (`graded.json`): 40 F2 labels per arm, billed 100.68 (DTDE) and 88.84 (CEDT_P4) pc-nh, ratio 1.133, pass; corrected for repaired F3 costs 1.207 (`repair_graded.json`).
- R: preregistered analyzer as run 0/15; repair grade 5/15 = 0.333, sign p = 0.941, fail; fallback grade 5/15, fail (mid-run 1/9 = 0.111). Deviation report: prediction holds as a tie, 2 verdict flips, 3 first-qualifier identity changes, 0 window flips.
- Masking price (seeds 0 to 2): +3.01 %, +7.15 %, +2.73 % billed.
- Attacks: CEDT_P4 identity accuracy 0.585 (n = 53), AUC 0.935; DTDE 0.78 (n = 50), AUC 0.989; limit 0.0845 and 0.60, all breached. The unmasked replay (n = 11) is too small for a separate estimate.
- Repaired gaps: HfS2_1T 1.329 eV, ZrS2_1T 1.199 eV, MoS2_2H 1.734 eV, WSe2_2H 1.812 eV, HfS2_2H 1.034 eV; Gamma-only F3 sampling widens the 2H direct gaps relative to 1x1.
- Pre-study (simulated): 6x6 is a structural null; at 8x8 predicted H gain 1.131 [1.06, 1.16], P(H >= 1.05) 0.95; post-refit 1.145 with budget 432 [376, 512] pc-nh for 8 calls x 15 pairs.
- Known limits: the void first attempt (jobs 1948457/1948458) ran without a memory request, received 125 GB, and nearly every QE call was OOM-killed (153 and 102 oom_kill events); its data are discarded. In attempt 2 the driver deleted save directories after every call, so all as-run F3 calls failed; the repair pass re-measured one F2+F3 per affected candidate and reconstructs costs with an expected 300 s hold and the transcript's launch order. Walls depend on the node, MPI build and co-tenants (contention 2.4 to 3.9 % measured); the masked replay ran days after the originals; 8 calls per campaign leave 8 of 15 pairs without any confirmed qualifier.

### `paired_comparison_3/`: paired comparison No. 3, four disclosure arrangements (DTDE, CEDT_P4, MIX50, CTDE_P2) x 15 seeds of live 8x8 MX2 Quantum ESPRESSO campaigns on guest nodes, with the corrected candidate list, an out-of-memory repair pass, notchpeak site-bridge copies, the final grade and the timing attack

Level: measured on hardware. One campaign per SLURM job, 64 MPI ranks (four 16-rank pw.x streams at most), on preemptible zero-charge guest nodes: CHPC granite guest nodes (AMD Genoa, `--constraint=gen`, 96 cores, e.g. EPYC 9654P) until 9 Oct 2026, then notchpeak guest nodes (AMD Genoa, 64 to 192 cores, EPYC 9554, 9654 and 9334 among others; 384 GB to 1.5 TB). The node and processor model of every campaign are recorded in `progress.json`/`campaigns.jsonl` and summarised in `paired_comparison_3/pair_sites.json`. The timing attack and grading are analyses of the committed records.

**Re-analyse from the committed records (no new compute).** Python 3.10 or later; standard library, plus `numpy` for the timing attack. Every script resolves its paths from its own folder, so the commands below work from the repository root. Each one overwrites its committed output in place; compare against the committed version with a version-control diff.

1. Corrected candidate list: `python3 paired_comparison_3/build_candidate_list.py` reads `dft_campaign/results/outcomes.jsonl`, `stacking_study/results_2088961/outcomes.jsonl` and `paired_comparison_2/inputs/manifest2.json`; writes `paired_comparison_3/candidates_corrected.json` (gap window 1.0 to 2.0 eV, lists `q_first_pass`, `q_single_layer`, `q_bilayer_AA`, `q_bilayer_3R`) and `paired_comparison_3/candidates_corrected_check.json`. The committed check file covers the 13 campaigns collected by 4 Oct; a rerun now covers every `collected_*` snapshot (first line of each `campaigns.jsonl`), so only the list file is expected to match.
2. Pair sites: `python3 paired_comparison_3/pair_sites.py` reads `paired_comparison_3/collected_*/*/campaigns.jsonl` (a later snapshot replaces an earlier one) and writes `paired_comparison_3/pair_sites.json` (host, cluster, CPU model, SLURM job per campaign; same-site flag per pair).
3. Preregistered grade (preregistered rule of `paired_comparison_2/analyze_live2.py`): `python3 paired_comparison_3/grade_both_lists.py` reads the same snapshots and `candidates_corrected.json`; writes `paired_comparison_3/graded_both_lists.json`: computing-centre metric (pooled F2 labels per billed per-core node-hour, pc-nh, ratio to DTDE) and research-side PW60 pair wins under (a) the as-run in-campaign gap test, (b) the corrected single-layer list, (c) the D3 AA' and 3R bilayer lists, with a one-sided sign-test p.
4. Final grade: `python3 paired_comparison_3/final_grade_2026-10-14.py` reads only `paired_comparison_3/collected_2026-10-14/` and `paired_comparison_3b/collected_2026-10-14/` plus each folder's `pair_sites.json` (run step 2 and `python3 paired_comparison_3b/pair_sites.py` first); writes `paired_comparison_3/final_grade_2026-10-14.json` (all 15 pairs, same-processor subset, first qualifiers).
5. Timing attack (registered in `TIMING_ATTACK_PLAN.md` and `parallel/OPTION_C.md`, prediction P-2026-10-01 item 3): `python3 paired_comparison_3/wire_attack3.py` reads `collected_2026-10-14/<ARM>_s<seed>/{campaigns,wire_log}.jsonl` (asserts 60 campaigns), the 12 copies in `site_bridge_2026-10-14/` and the candidate names in `paired_comparison_2/inputs/manifest2.json` (opaque ids are reversed offline with the driver's salted SHA-1). It runs the leave-one-seed-out identity and membership attacks per arm and tests T1 to T4; writes `paired_comparison_3/timing_attack3.json`. Seed-bootstrap intervals: `python3 bootstrap_ci/seed_bootstrap3.py` (imports `wire_attack3.py`; writes `bootstrap_ci/seed_bootstrap3.json`).
6. CTDE_P2 seed logbook: `python3 paired_comparison_3/parallel/build_ctde_logbook.py` reads `paired_comparison_2/inputs/manifest2.json` and `paired_comparison_2/results/campaigns.jsonl`; writes `paired_comparison_3/parallel/ctde_logbook_seed.json` (bin-level maxima of 16 x peak rank RSS).

**Re-run the computation.**

1. Inputs: the No. 3 campaigns use the comparison No. 2 inputs unchanged, `paired_comparison_2/inputs/*.in` and `manifest2.json` (29 compounds, HfSe2-2H excluded; 1T cells 8x8 single layer, 192 atoms; 2H cells 8x8 PBE-spaced bilayer, 384 atoms), regenerated by `python3 paired_comparison_2/build_live2_inputs.py` (no arguments). Stages: F1 SCF 40/320 Ry, conv 1e-6; F2 SCF 45/360 Ry, conv 1e-8; F3 NSCF 45/360 Ry, nbnd = 1.10 x nocc + 16; all Gamma-only.
2. Pseudopotentials: GBRV PBE ultrasoft `ti_pbe_v1.4`, `zr_pbe_v1`, `hf_pbe_v1`, `mo_pbe_v1`, `w_pbe_v1.2`, `s_pbe_v1.4`, `se_pbe_v1`, `te_pbe_v1` (`.uspp.F.UPF`), downloaded from the GBRV site by `parallel/stage_and_submit3.sh`. No checksums are in the repository.
3. Software: modules `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`; each stream runs `mpirun -np 16 --bind-to none pw.x -nk 1`.
4. Driver: `paired_comparison_2/live2_campaign.py` with `qe_retry.py` (Davidson to conjugate-gradient solver retry) staged next to it. Option A (DTDE, CEDT_P4), the site-bridge copies and the repair pass ran the earlier driver revision kept as `paired_comparison_3/oom_repair_2026-10-14/live2_campaign.py`; option C (MIX50, CTDE_P2) ran the committed `paired_comparison_2` revision, which adds only the MIX50 routing draw (`Random(f"{seed}:{compound}:{stage}") < 0.5`) and the CTDE_P2 logbook reservation (1.10 x largest recorded RAM per size bin and stage, capped at the DTDE worst case, seeded from `parallel/ctde_logbook_seed.json`). The driver models a 64-core, 380 GB node (packing budget 342 GB) and bills pc-nh = wall_h x max(16/64, reservation_GB/380).
5. Environment variables read by the driver (set with `sbatch --export`): `MPT_LIVE2_ROOT` (staging dir with `inputs/`, `pseudos/`), `MPT_RESULTS`, `MPT_WORK`, `MPT_CAMPAIGN=<ARM>:<seed>` (ARM in DTDE, CEDT_P4, MIX50, CTDE_P2; seeds 0 to 14), `MPT_MAX_CALLS=16`, `MPT_CAMP_CAP=25` (campaign cap, pc-nh), `MPT_W_CAP=30` (launch refused if the projected bill crosses it), `MPT_MASK=prop`, `MPT_MASK_FRAC=0.25` (completion time rounded up to 25 % of the expected run time, CEDT_P4 and routed MIX50 jobs only).
6. Batch file `parallel/live3_guest.sbatch`: 1 node, `--ntasks=64`, `--mem=372000M` (the 380 GB node the driver assumes), `--time=72:00:00`, `--requeue`, `--constraint=gen`, account and partition `<account>`, `<partition>` (a granite guest partition). A requeued job restarts its campaign; the lost attempt's wire rows go to `wire_log.lost.jsonl`.
7. Staging and submission (SSH to the login node, username in `CHPC_USERNAME`): `bash paired_comparison_3/parallel/stage_and_submit3.sh` stages `$SCRATCH/mpt_live3` and submits 30 option A jobs (also a 14-task library array for `fast_path/`, see that folder); `bash paired_comparison_3/parallel/stage_and_submit3c.sh` stages `$SCRATCH/mpt_live3c` and submits 30 option C jobs. Job-to-arm maps: `parallel/.live3_jobids`, `parallel/.live3c_jobids`.
8. Site move (sub-study `move_2026-10-09/`): `bash paired_comparison_3/move_2026-10-09/move41.sh test|go` (run on the cluster) resubmits every pending `l3_*`, `l3b_*` and `l3_oom_repair` job to notchpeak guest nodes (`-M notchpeak`, `--constraint=gen`; DTDE `--mem=372000M`, all other arms and the repair `--mem=500000M`) with identical `--export` settings, then cancels the granite copy; old to new ids in `JOBMAP.txt`. `move_2026-10-09/site_bridge.sh test|go` submits 12 `l3np_*` notchpeak copies (CEDT_P4 s0 and s13, DTDE s3 to s11 and s14) into `results_notchpeak/` and `work_notchpeak/`.
9. Out-of-memory repair (sub-study `oom_repair_2026-10-14/`): three CEDT_P4 calls were killed when three 2H streams shared a 372000M node (s3 ZrTe2_2H F1, s4 ZrSe2_2H F2, s7 TiSe2_2H F3). `oom_repair_driver.py` (staged with its own `live2_campaign.py` and `qe_retry.py`) reruns them concurrently, TiSe2_2H F2 first as prerequisite, sampling summed pw.x RSS every 15 s. `oom_repair.sbatch`: 64 tasks, `--mem=500000M`, `--constraint=gen&m768`, `--time=36:00:00`; env `MPT_REPAIR_DIR`, `MPT_REPAIR_OUT`, `MPT_LIVE2_ROOT`. It ran on notchpeak after the move. The repaired calls are recorded separately and are not folded into the campaign records or the grade (CEDT_P4 shows 3 fails).
10. Collection: copy each `<ARM>_s<seed>/` results directory (`campaigns.jsonl`, `wire_log.jsonl`, `wire_log.lost.jsonl` if present, `progress.json`) into `collected_<date>/`, and the notchpeak copies into `site_bridge_<date>/`; a collection script is not in the repository. Then run the analysis steps above.
11. Observed cost: per-campaign makespan 63,806 to 164,335 s (17.7 to 45.6 h, `progress.json`); billed totals in the driver's units, DTDE 316.5, CEDT_P4 299.7, MIX50 325.9, CTDE_P2 340.7 pc-nh (no allocation charge on guest partitions). Repair pass 75,708 s on notch492, peak job RSS 426.5 GB.

**Outputs.**

- `paired_comparison_3/FINAL_RESULTS.md`, `final_grade_2026-10-14.json`, `graded_both_lists.json`, `pair_sites.json`
- `paired_comparison_3/TIMING_ATTACK_RESULTS.md`, `timing_attack3.json`
- `paired_comparison_3/CANDIDATE_LIST.md`, `candidates_corrected.json`, `candidates_corrected_check.json`
- `paired_comparison_3/oom_repair_2026-10-14/results/oom_repair.json` and `results/work/*/*.time`
- Raw records: `collected_2026-10-14/` (all 60 campaigns), `site_bridge_2026-10-14/`

**Checks.**

- Computing-centre ratio vs DTDE, all 15 pairs (same-processor pairs): CEDT_P4 1.069 (1.102, n = 10), MIX50 0.959 (1.167, n = 3), CTDE_P2 0.929 (0.953, n = 6). DTDE 80 labels over 316.481 pc-nh; CEDT_P4 81 over 299.68.
- Research-side wins of 15 (as run): CEDT_P4 6, MIX50 3, CTDE_P2 2; PW60 needs 9, fails in every arm. All first qualifiers lie on the corrected single-layer list (nine compounds, same as the first pass).
- Timing attack, identity accuracy (membership AUC): DTDE 0.750 (0.945), CEDT_P4 0.484 (0.826), CTDE_P2 0.218 (0.672), MIX50 routed 0.174 (0.722); limits 0.084 and 0.60. T1 0.466 pass, T2 0.069 fail, T3 pass, T4 0.0152 pass.
- Repair: all three calls converged; TiSe2_2H F3 gap 0.4927 eV.
- Limits: guest nodes are shared with other users and preemptible (21 of 60 final campaigns carry a `wire_log.lost.jsonl`); pairs often ran on different clusters or processor models (5 of 15 CEDT_P4 pairs), so wall times and bills depend on hardware and co-tenants. Fifty pending jobs were moved from granite to notchpeak on 9 Oct with only the scheduler request changed; DTDE then requested 372000M and the other arms 500000M.

### `paired_comparison_3b/`: paired comparison No. 3b, the single-layer companion of No. 3 (DTDE vs CEDT_P4, 15 seeds, every cell an 8x8 single layer of 192 atoms, so the disclosed memory bit separates chemistry instead of layer count)

Level: measured on hardware. One campaign per SLURM job, 64 MPI ranks (16-rank pw.x streams), submitted to the CHPC granite guest partition (`--constraint=gen`) on 5 Oct 2026. Seeds 0 to 4 ran on the group-owned granite node grn061 (AMD EPYC 9554, 64 cores); seeds 5 to 14 were moved before starting to notchpeak guest nodes (AMD EPYC 9554, 9554P, 9654, 9654P, 9454). Node and processor model per campaign are in `paired_comparison_3b/pair_sites.json`. Grading is an analysis of the committed records.

**Re-analyse from the committed records (no new compute).** Python 3.10 or later, standard library only. Scripts resolve paths from their own folder; run from the repository root. Each overwrites its committed output in place.

1. Pair sites: `python3 paired_comparison_3b/pair_sites.py` reads `paired_comparison_3b/collected_*/*/campaigns.jsonl` (the later snapshot replaces the earlier) and writes `paired_comparison_3b/pair_sites.json`.
2. Preregistered grade: `python3 paired_comparison_3b/grade_3b.py` (same rule as `paired_comparison_3/grade_both_lists.py`, paths changed) reads the same snapshots and the qualifier lists in `paired_comparison_3/candidates_corrected.json`; writes `paired_comparison_3b/graded_3b_interim.json` (the file name is historical; the committed copy holds all 30 campaigns): pooled F2 labels per billed per-core node-hour (pc-nh) per arm and the ratio to DTDE, and PW60 pair wins under the as-run gap test, the corrected single-layer list and the two D3 bilayer lists.
3. Final grade with the same-processor subset and first qualifiers: `python3 paired_comparison_3/final_grade_2026-10-14.py`, which reads `paired_comparison_3b/collected_2026-10-14/` and `paired_comparison_3b/pair_sites.json` (key `No3b` in `paired_comparison_3/final_grade_2026-10-14.json`).

**Re-run the computation.**

1. Inputs: `python3 paired_comparison_3b/build_live3b_inputs.py` (no arguments) writes `paired_comparison_3b/inputs/<name>.f1/f2/f3.in` and `inputs/manifest2.json` (file name kept for the unchanged driver). It imports `paired_comparison_2/build_live2_inputs.py` (stage blocks, valence table, chalcogen factors) and reads `paired_comparison_1/inputs/manifest.json` and the 3x3 `*.f2.in` files there for the 1T layers (identical to No. 3), `paired_comparison_3b/mono2H_geometries.json` for the relaxed single 2H layers (c = 20 A; taken from the single-layer vc-relax of `stacking_study/`, job 2088961; the extraction script is not in the repository) and `paired_comparison_3/candidates_corrected.json` for the reference gaps. Pool: 29 compounds (TiS2-2H out, HfSe2-2H in). RAM model: 30.9 GB x (nelec/864)^1.55 x chalcogen factor/0.90 x c/18 A; `mem_bit` = 1 above the median (94.8 GB). Stages as in No. 3: F1 SCF 40/320 Ry, conv 1e-6; F2 SCF 45/360 Ry, conv 1e-8; F3 NSCF, nbnd = 1.10 x nocc + 16; Gamma-only.
2. Pseudopotentials: the GBRV PBE ultrasoft set of No. 3, copied from the No. 3 staging directory by the staging script (see `paired_comparison_3.md`).
3. Software: modules `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`.
4. Driver: `paired_comparison_2/live2_campaign.py` with `qe_retry.py`, unchanged; arms DTDE and CEDT_P4, seeds 0 to 14, environment `MPT_LIVE2_ROOT`, `MPT_RESULTS`, `MPT_WORK`, `MPT_CAMPAIGN=<ARM>:<seed>`, `MPT_MAX_CALLS=16`, `MPT_CAMP_CAP=25`, `MPT_W_CAP=30`, `MPT_MASK=prop`, `MPT_MASK_FRAC=0.25` (see `paired_comparison_3.md` for their meaning).
5. Batch file `live3b_guest.sbatch`: 1 node, `--ntasks=64`, `--mem=372000M`, `--time=72:00:00`, `--requeue`, `--constraint=gen`, account and partition `<account>`, `<partition>` (granite guest class); runs `python3 live2_campaign.py` in `$MPT_LIVE2_ROOT`.
6. Staging and submission: `bash paired_comparison_3b/stage_and_submit3b.sh` (SSH control connection, username in `CHPC_USERNAME`, login host `CHPC_HOST`, default notchpeak, with `sbatch -M granite`) stages `$SCRATCH/mpt_live3b` (inputs, pseudopotentials, driver, `qe_retry.py`, batch file) and submits 30 jobs `l3b_<ARM>_s<seed>`. Job ids: `JOBIDS.txt`.
7. Run order as executed: the jobs waited behind a granite maintenance window; seeds 0 to 4 were run on grn061 through the group-owned partition (the resubmission commands are not in the repository); seeds 5 to 14 were moved unstarted to notchpeak guest nodes with `paired_comparison_3/move_2026-10-09/move41.sh` (same `--export`, `--mem=372000M` for DTDE, `--mem=500000M` for CEDT_P4; ids in that folder's `JOBMAP.txt`).
8. Collection: copy each `$SCRATCH/mpt_live3b/results/<ARM>_s<seed>/` (`campaigns.jsonl`, `wire_log.jsonl`, `progress.json`) into `collected_<date>/`; a collection script is not in the repository. Then run the analysis steps.
9. Observed cost: per-campaign makespan 39,512 to 77,291 s (11.0 to 21.5 h, `progress.json`); billed totals in the driver's units DTDE 150.6, CEDT_P4 156.5 pc-nh.

**Outputs.**

- `paired_comparison_3b/graded_3b_interim.json` (final 30-campaign grade)
- `paired_comparison_3b/pair_sites.json`
- Key `No3b` of `paired_comparison_3/final_grade_2026-10-14.json`, summarised in `paired_comparison_3/FINAL_RESULTS.md`
- `paired_comparison_3b/inputs/` (87 inputs, `manifest2.json`), raw records in `collected_2026-10-14/` (all 30 campaigns)

**Checks.**

- RAM estimates 75 to 130 GB, median 94.8 GB; 12 of 29 compounds carry the high bit (`inputs/manifest2.json`).
- Computing-centre ratio CEDT_P4/DTDE: 0.905 on all 15 pairs (DTDE 84 F2 labels over 150.598 pc-nh, CEDT_P4 79 over 156.523), 0.978 on the 7 same-processor pairs; no failed calls.
- Research-side wins of 15: 4 as run (2 both none), 5 on the single-layer list, 5 on the AA' bilayer list; PW60 fails.
- Registered predictions (`DESIGN.md`, P-2026-10-05): P3b-1 (ratio at least 1.05) fail; P3b-2 (within 0.10 of the No. 3 ratio 1.069) fail; P3b-3 (PW60 fails) pass; P3b-4 (all first qualifiers on the corrected single-layer list) pass.
- Limits: 8 of 15 pairs ran on different processor models, and wall times on shared guest nodes depend on co-tenants; one campaign (DTDE s11) records a nonzero restart count after preemption.

### `rescreen_3x3/`: 29-candidate MX2 screening ladder (F1, F2, F3) at 3x3-supercell scale with Quantum ESPRESSO on a preemptible guest partition, plus a conjugate-gradient rerun of four failed band calculations

Level: measured on hardware (CHPC granite, `granite-guest` partition class: preemptible, zero allocation charge; main job 2048736 on node grn068, 32 MPI ranks; follow-up job 2087605 on node grn021, 32 MPI ranks).

**Re-analyse from the committed records (no new compute).**

1. Run `(cd rescreen_3x3 && python3 rebuild_summary.py)` (no arguments; it imports `guest_screen.py` from the same folder, so run it from inside `rescreen_3x3/`). Python standard library only.
2. It reads: `rescreen_3x3/results/qe_outputs/guest_2048736_outs.tgz` (the 29 x 4 raw `pw.x` outputs `<cand>/f1.cedt.out`, `f2.cedt.out`, `f3.cedt.out`, `f2.dtde.out`), `rescreen_3x3/results/qe_outputs/followup_2087605/<cand>/f3cg.cedt.out`, `rescreen_3x3/inputs/manifest.json`, `dft_campaign/results/outcomes.jsonl` (1x1 gaps) and `dft_campaign/soc/results/soc_summary.json` (1x1 SOC gaps).
3. It writes `rescreen_3x3/results/guest_summary_final.json` and `rescreen_3x3/results/GUEST_RESULTS.md`, overwriting the committed copies; `guest_summary.json` (the as-run summary) is not touched.
4. Gap: the directory `results/qe_outputs/followup_2087605/` is not in the repository. Without it, the four candidates rescued by the follow-up (TiS2_1T, TiS2_2H, ZrS2_1T, ZrSe2_1T) come out as "pending", and the rebuilt file reports 25 of 29 gaps and 8 qualifiers instead of 29 and 9. Their committed final values are in `GUEST_RESULTS.md`.

**Re-run the computation.**

1. Inputs: the committed `rescreen_3x3/inputs/*.f1.in`, `*.f2.in`, `*.f3.in` (29 candidates x 3 stages) and `manifest.json` are byte-identical to `paired_comparison_1/inputs/`, which `python3 paired_comparison_1/build_live_inputs.py` (no arguments) regenerates from `dft_campaign/results/campaign_summary.json` and `prior_predictive/candidates/candidates.json`. Stages: F1 coarse SCF (ecutwfc 40 Ry, 2x2 k, conv 1e-6), F2 production SCF (45 Ry, 4x4 k, conv 1e-8), F3 dense NSCF (6x6 k). The follow-up inputs `rescreen_3x3/followup/inputs/<cand>.f3cg.in` differ from the F3 inputs only in `diagonalization = 'cg'`.
2. Pseudopotentials: GBRV PBE ultrasoft, `ti_pbe_v1.4.uspp.F.UPF`, `zr_pbe_v1.uspp.F.UPF`, `hf_pbe_v1.uspp.F.UPF`, `mo_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, `te_pbe_v1.uspp.F.UPF` (fetched from the GBRV site by the staging script). No hash manifest for these files is in the repository.
3. Software: `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`; Python standard library only.
4. Stage and dry-run: `bash rescreen_3x3/stage_and_submit_guest.sh` (requires an SSH connection to the cluster login node and the username in an environment variable). It lists the guest partitions and QoS available, fetches the pseudopotentials into `$SCRATCH/mpt_guest/pseudos`, copies `qe_retry.py`, `guest_screen.py`, `guest.sbatch`, the inputs and the manifest, compiles the driver remotely and runs `sbatch --test-only`.
5. Submit: `MPT_GUEST_SUBMIT=1 MPT_GUEST_PART=<partition> MPT_GUEST_QOS=<qos> MPT_GUEST_ACCT=<account> bash rescreen_3x3/stage_and_submit_guest.sh`. `rescreen_3x3/guest.sbatch` requests 1 node, 32 tasks, `--time=12:00:00`, `--requeue`, `--open-mode=append`, and runs `python3 guest_screen.py` with `MPT_GUEST_ROOT` set to the staged directory.
6. Run order in `guest_screen.py`, per candidate in manifest order: F1 at 16 ranks, 1 pool; F2 at 32 ranks, 2 pools; F3 at 32 ranks, 4 pools (class-matched configuration); then F2 again at 32 ranks, 1 pool (worst-case configuration). Each call has a timeout `MPT_GUEST_CALL_TIMEOUT` (default 9000 s). On requeue, any stage with a clean output (`JOB DONE` plus convergence for SCF) is skipped. The cost metric is QE's own `PWSCF ... CPU` seconds. Outputs: `results/guest_results.jsonl`, `results/progress.json` (after each candidate), `results/run_log.jsonl` (start and finish events with node and restart count), `results/guest_summary.json`.
7. Note: the committed driver now applies the Davidson-to-conjugate-gradient retry of `qe_retry.py` inline. The run of record predates that rule, which is why the follow-up below was needed; a rerun with the committed driver should not require it.
8. Follow-up (sub-study `rescreen_3x3/followup/`): `rescreen_3x3/followup/f3cg.sbatch` (1 node, 32 tasks, `--time=06:00:00`, `--requeue`; modules `openmpi/5.0.3 quantum-espresso/7.4`) reruns F3 for TiS2_1T, TiS2_2H, ZrS2_1T, ZrSe2_1T with `mpirun -np 32 --bind-to none pw.x -nk 4`, reading the converged F2 charge density left in `work/<cand>/out` by the main job and writing `work/<cand>/f3cg.cedt.out`. It expects `followup/inputs/` inside `$MPT_GUEST_ROOT`; a script that stages the follow-up is not in the repository. Submit with `sbatch --account=<account> --partition=<partition> --qos=<qos> --export=ALL,MPT_GUEST_ROOT=$SCRATCH/mpt_guest followup/f3cg.sbatch`.
9. Collect: archive `work/<cand>/{f1.cedt,f2.cedt,f3.cedt,f2.dtde}.out` as `results/qe_outputs/guest_<jobid>_outs.tgz`, copy each `f3cg.cedt.out` to `results/qe_outputs/followup_<jobid>/<cand>/`, copy the `results/*.json*` files, then run `rebuild_summary.py` (job ids in that script are fixed to 2048736 and 2087605; adjust the two paths for a new run).
10. Observed cost: the main job ran from start to finish in 23,548 s (6.5 h) on 32 cores without preemption (`run_log.jsonl`, restart 0). The follow-up wall time is not recorded in the repository.

**Outputs.**

- `rescreen_3x3/results/GUEST_RESULTS.md`
- `rescreen_3x3/results/guest_summary_final.json`
- `rescreen_3x3/results/guest_results.jsonl`, `rescreen_3x3/results/guest_summary.json`, `rescreen_3x3/results/progress.json`, `rescreen_3x3/results/run_log.jsonl` (as-run records)
- `rescreen_3x3/results/qe_outputs/guest_2048736_outs.tgz`

**Checks.**

- 29 of 29 gaps at 3x3; the largest difference from the 1x1 campaign gap is 0.0017 eV over the 19 candidates with both values.
- Nine qualifiers (PBE gap 1.0 to 2.0 eV), identical to the 1x1 set: ZrS2_1T, HfS2_1T, HfS2_2H, MoS2_2H, MoSe2_2H, MoTe2_2H, WS2_2H, WSe2_2H, WTe2_2H. The as-run `guest_summary.json` lists eight, because ZrS2_1T had no F3 gap before the follow-up.
- F2 cost ratio (2 pools over 1 pool, QE CPU seconds): median 0.986, range 0.849 to 1.191, n = 29.
- Example gaps: MoS2_2H 1.557 eV, WS2_2H 1.770 eV, TiS2_1T 0.061 eV (conjugate-gradient rerun).
- Limits: guest nodes can be preempted (requeue delays the run but the CPU-second metric is unaffected); CPU times depend on the node model assigned; this is a screening run, not a paired comparison of the two configurations on the same node at the same time.

### `memory_band_probe/`: wall time and memory of 5×5 to 8×8 supercells under two k-point parallelisation settings

Level: measured on hardware (CHPC granite node grn061, owner partition, 64-core allocation with 380 GB node memory, each run 32 MPI ranks; CPU only).

**Re-analyse from the committed records (no new compute).**

1. `memory_band_probe/results/probe_results.jsonl` holds one record per run (candidate, configuration `lean` = `-nk 1` or `fast` = `-nk 4`, wall, convergence, RAM per process, electrons, node-hours and cumulative node-hours). The same records appear in `memory_band_probe/results/probe_1928420.log`.
2. No analysis script for this folder is in the repository. The fast/lean wall ratios of `results/RESULTS.md` follow directly from `wall_s` in the jsonl (for example `MoSe2_2H_s8_k1`: 43014.48 / 11766.58 = 3.66).
3. The total-RAM columns of `results/RESULTS.md` (lean and fast, in GB) are not in the jsonl: the driver's original regular expression read only values printed in MB, so most `ram_mb_per_proc` fields are null and `ram_total` is null throughout. The totals were re-parsed from the per-run `pw.x` outputs on cluster scratch, which are not in the repository. The regular expression in `probe.py` now reads both MB and GB, so a rerun records these values directly.
4. The paper figure that uses these memory values transcribes them from `results/RESULTS.md` (`papers/paperB_qe_mx2_campaign/figures/make_figures.py`, Python 3 with `numpy` and `matplotlib`). The script that produced `results/fig_probe_bench.png` is not in the repository.

**Re-run the computation.**

1. Inputs: `python3 memory_band_probe/build_probe_inputs.py` (no arguments) writes 7 decks to `memory_band_probe/inputs/` from `pilot/inputs/<candidate>.pw.in`: TiS2_1T, MoSe2_2H and WTe2_2H at 5×5 and 6×6 on a 2×2×1 grid, and MoSe2_2H 8×8 at Γ only (1×1×1). Settings: SCF, ecutwfc 40 Ry, ecutrho 320 Ry, cold smearing 0.02 Ry, mixing 0.3, conv_thr 1e-6, Davidson, at most 60 steps. The committed decks are the ones that were run.
2. Pseudopotentials: GBRV ultrasoft PBE (`ti_pbe_v1.4.uspp.F.UPF`, `mo_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, `te_pbe_v1.uspp.F.UPF`), downloaded by `stage_and_submit.sh` from the GBRV site at Rutgers. Hashes: `pilot/results/pseudos_manifest.txt`.
3. Software: Quantum ESPRESSO 7.4, modules `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`, `mpirun --bind-to none`.
4. Staging: directory `$SCRATCH/mpt_memband` with `probe.py`, `probe.sbatch`, `inputs/`, `pseudos/` and `results/`. `memory_band_probe/stage_and_submit.sh` performs this staging and submission over an existing authenticated SSH connection (site-specific); with `SKIP_KINGSPEAK=1` it stops after this job, otherwise it also submits the separate multi-node bench of `multinode_bench/`.
5. Submit: `sbatch --export=ALL,MPT_PROBE_ROOT=$SCRATCH/mpt_memband probe.sbatch` (1 node, 64 tasks, 44 h wall; replace `--account`, `--partition`, `--qos` by `<account>`, `<partition>`, `<qos>`). `MPT_PROBE_NH_CAP` (default 30, in units of `ranks / 64 × wall` hours) is the cost guard.
6. Run order inside `probe.py`: smallest first (5×5 TiS2, MoSe2, WTe2; 6×6 TiS2, MoSe2, WTe2; 8×8 MoSe2), each run once with `lean` and then `fast`, serially. A run whose projected cost would exceed the cap is skipped and recorded as `skipped`. Each run appends a record to `results/probe_results.jsonl` and deletes its QE scratch `out/` directory; `work/<name>_<cfg>/run.out` is kept on scratch.
7. Collect `results/probe_results.jsonl` and `probe_<jobid>.log` into `memory_band_probe/results/` (commands in `memory_band_probe/README.md`). To fill the total-RAM columns, also copy `work/*/run.out` and read the line `total dynamical RAM`.
8. Observed cost: job 1928420, 25 h 50 min wall, 12.91 node-hours in the ranks/64 convention (cap 30). The 8×8 `fast` run alone took 43014 s.

**Outputs.**

- `memory_band_probe/results/probe_results.jsonl`, `memory_band_probe/results/probe_1928420.log`
- `memory_band_probe/results/RESULTS.md` (measured table), `memory_band_probe/results/fig_probe_bench.png`

**Checks.**

- 14/14 runs converged, none skipped.
- fast/lean wall ratios: TiS2 5×5 1.85, 6×6 2.12; MoSe2 5×5 1.98, 6×6 1.90, 8×8 3.66; WTe2 5×5 1.63, 6×6 1.97. The single k-point pool (`lean`) is faster in every case, consistent with about 2 irreducible k-points on the 2×2×1 grids and Γ only at 8×8, which leave most of the 4 pools idle.
- Total dynamical RAM (lean / fast): MoSe2 8×8 112.0 / 424.4 GB, above the node's 380 GB for `fast`; iso-electron spread WTe2 against MoSe2: 30.8 against 23.3 GB at 1,300 electrons, 52.6 against 42.6 GB at 1,872 electrons.
- Limits: one run per configuration; wall times depend on node and memory bandwidth, and the 8×8 `fast` time includes memory-pressure effects specific to a 380 GB node. RAM values are QE's own estimates, not measured resident memory.

### `metric_redesign/`: battery of seven candidate reservation-gain metrics and fresh-world validation of the paired-seed win-rate metric

Level: simulated on measured inputs (the wide-prior setting is purely simulated; the posterior setting at x100 task scale patches the twin with the measured campaign fit and the 81-job pilot fit). The hardware used is not in the repository.

**Re-analyse from the committed records (no new compute).** Python 3 with `numpy` and `matplotlib`.

1. `python3 metric_redesign/make_figure.py` reads `metric_redesign/metric_study.json` and writes `metric_redesign/fig_metric_redesign.png` (paths resolve relative to the script).
2. The battery table in `RESULTS.md` can be read from `metric_study.json` (keys `wide_prior_x1` and `posterior_x100`, each with `p_r_gain`, `p_ww_frozen`, `p_ww_package` per metric, plus `_h` and `_snr` blocks). The fresh-world numbers are in `fresh_world_validation.json` under the same keys.

**Re-run the computation.**

1. Required committed inputs: `stage2_twin_fit/twin_fit.json` (measured per-call cost amplitudes, electron-scaling exponent `p_e`, residual spread) and `pilot/results/pilot_fit.json` (parallel-efficiency exponent and configuration quirk spread). Both are read at import of `metric_study.py`. The study also imports `prior_predictive/simulator.py` and `ceiling_diagnosis/diagnose_ceiling.py` (for the nature oracle).
2. Battery on the selection worlds (ids 0 to 299 in both settings):
   `MRS_WORLDS=300 MRS_PROCS=<n> python3 metric_redesign/metric_study.py`
   Output: `metric_redesign/metric_study.json`; a summary table is printed to stdout. There is no command-line parser; `MRS_WORLDS` (default 300) and `MRS_PROCS` (default `os.cpu_count()`) are read from the environment.
3. Fresh-world validation of the pre-chosen PW60 metric with the package H margins (world ids 500000 to 500299):
   `MRS_WORLDS=300 python3 metric_redesign/validate_fresh_worlds.py`
   Output: `metric_redesign/fresh_world_validation.json`; `fresh_validation.log` is a capture of its two-line stdout.
4. Both scripts set `MPT_HARD_CAP=1` by default before importing the simulator. Each world compares CEDT-P4 with DTDE-P4 on identical worlds, seeds and noise fields (common random numbers, 30 paired seeds).
5. Seed handling: world truth comes from `crc32("<card>:<world_id>")`; the posterior patch draws its extra parameters from `crc32("post:<card>:<world_id>")`.
6. The posterior setting is applied by reassigning module globals (`SCALE`, `sim.sample_world`, `sim.mem_per_node`, `sim.OVERHEAD_NH = 0.02`) in the parent process before the worker pool starts. This relies on the `fork` start method of `multiprocessing` (the Linux default); under `spawn` (macOS and Windows defaults) the workers would not see the patch.

**Outputs.**

- `metric_study.json`
- `fresh_world_validation.json`
- `fresh_validation.log`
- `fig_metric_redesign.png`

**Checks.** From `RESULTS.md` (300 worlds per setting):

- Preregistered metric T20: P(win-win, package margins) 0.043 on the wide prior at x1 and 0.190 on the posterior at x100.
- PW60 (contract beats baseline in at least 60 % of the 30 paired seeds): P(R gain) 0.230 and P(win-win, package) 0.160 at x1; 0.947 and 0.920 at x100 (0.593 with the preregistered H margins).
- EX10 (labels per node-hour >= 1.10x): 0.817 at x100; QY05 collapses to 0.000 at x100.
- Fresh worlds (`fresh_validation.log`): PW60 P(R gain) 0.263 and win-win 0.193 at x1; 0.943 and 0.920 at x100.
- Median paired t-statistics at x1: 2.2 (node-hours to first qualifier) and 3.4 (labels per node-hour); at x100: 23 and 126.
- With fixed world seeds a rerun is expected to be identical for the same code and NumPy version; this is not recorded as verified. The PW60 battery result carries selection optimism (chosen from seven metrics on the same worlds); the fresh-world run addresses this. Attacker models remain prior beliefs.

### `multinode_bench/`: multi-node strong-scaling benchmark of two fixed 3x3 MX2 SCF problems at 1, 2 and 4 nodes

Level: measured on hardware (CHPC kingspeak, general allocation (non-preemptible), 16 MPI ranks per node; jobs 28272521, 28272522, 28272523).

**Re-analyse from the committed records (no new compute).**

1. Read `multinode_bench/results/multinode_results.jsonl` (six records: `name`, `nodes`, `ntasks`, `wall_s`, `converged`).
2. Compute the per-core-hour efficiency `eff(N) = wall(1) / (N * wall(N))` per problem. No analysis script for this step is in the repository; the arithmetic is a few lines with the Python standard library (`json`).
3. Compare against the table in `multinode_bench/results/RESULTS.md`.

**Re-run the computation.**

1. Inputs: `scale_validation/inputs/TiS2_1T_s3_k6.pw.in` and `scale_validation/inputs/MoSe2_2H_s3_k6.pw.in` (3x3 in-plane supercells, 6x6x1 k-grid). They are regenerated by `python3 scale_validation/build_scale_inputs.py` (no arguments).
2. Pseudopotentials: GBRV PBE ultrasoft, `ti_pbe_v1.4.uspp.F.UPF`, `mo_pbe_v1.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, downloaded from the GBRV site. No hash manifest for these files is in the repository.
3. Software: `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`; `multinode_bench/multinode.sbatch` falls back to `gcc openmpi quantum-espresso python` if that exact stack is absent, so record the versions actually loaded.
4. Stage: the kingspeak block of `memory_band_probe/stage_and_submit.sh` creates `$SCRATCH/mpt_multinode/{inputs,results,pseudos}`, copies `multinode.sbatch` and the two inputs, and fetches the pseudopotentials. That script first stages and submits the memory-band probe on granite; it has no switch to skip that part (`SKIP_KINGSPEAK=1` skips the kingspeak part instead), so run only its kingspeak block by hand.
5. Submit three jobs (run order is irrelevant):
   `sbatch -N 1 --ntasks-per-node=16 --export=ALL,MPT_MN_ROOT=$SCRATCH/mpt_multinode multinode.sbatch`
   and the same with `-N 2` and `-N 4`. Script settings: `--account=<account>`, `--partition=<partition>` (a non-preemptible allocation), `--time=06:00:00`.
6. Each job runs `mpirun -np $SLURM_NTASKS pw.x -nk 2` on TiS2_1T then MoSe2_2H, and appends one JSON record per problem to `results/multinode_results.jsonl` (wall clock from `date +%s`).
7. Collect: copy `$SCRATCH/mpt_multinode/results/multinode_results.jsonl` into `multinode_bench/results/`, then apply the re-analysis.
8. Observed cost: 13 to 25 min wall per job; summing the two recorded `pw.x` walls per job gives about 0.35, 0.82 and 0.87 node-hours for the 1-, 2- and 4-node jobs (2.0 node-hours in total).

**Outputs.**

- `multinode_bench/results/multinode_results.jsonl`
- `multinode_bench/results/RESULTS.md`

**Checks.**

- TiS2_1T 3x3: 383 s (1 node), 409 s (2 nodes), 230 s (4 nodes); eff(2) = 0.47, eff(4) = 0.42.
- MoSe2_2H 3x3: 873 s, 1,067 s, 557 s; eff(2) = 0.41, eff(4) = 0.39.
- All six SCFs converged. Two nodes are slower than one in wall time for both problems; four nodes are 1.7x faster than one at about 40 % efficiency.
- Limits: a single repetition per point (no spread); results depend on the interconnect and node generation of the cluster used; wall times include MPI start-up.

### `pilot/`: 81-job F1 cost pilot (3 candidate sizes x 9 parallel configurations x 3 repeats of a coarse `pw.x` SCF), its parameter fit, and a simulated posterior re-grade

Level: measured on hardware for the 81 jobs (CHPC granite node grn061: 64 cores, 380 GB, single-node partition, empty at submission, no co-tenant jobs); simulated for the posterior re-grade (`posterior_regrade.py`, simulated units).

**Re-analyse from the committed records (no new compute).**

1. Python 3 with `numpy` (both scripts); the re-grade also imports `prior_predictive/simulator.py` and its dependencies.
2. `python3 pilot/pilot_analysis.py` reads `pilot/results/pilot_results.csv` and `pilot/job_matrix.csv` and writes `pilot/results/pilot_fit.json` (parallel-efficiency exponent, pool and aggressive-mode effects, configuration spread, repeat noise, failure-rate bound, cross-term ablation by leave-one-cell-out CV). Node-hour convention here: 16 cores count as one node.
3. `python3 pilot/posterior_regrade.py` reads `pilot/results/pilot_fit.json` and `stage2_twin_fit/twin_fit.json`, re-runs the simulator at scales x10, x100, x300 with `POST_WORLDS` worlds (environment variable, default 300; uses all CPU cores through `multiprocessing`), and writes `pilot/results/posterior_regrade.json`.

**Re-run the computation.**

1. Inputs: `python3 pilot/make_inputs.py` (option `--check-pseudos` hashes the files in `pilot/pseudos/` into `pilot/pseudos_manifest.json`) builds six `pw.x` inputs (TiS2_1T, MoSe2_2H, WTe2_2H; conservative and `_agg`) from `prior_predictive/candidates/candidates.json`, and `pilot/job_matrix.csv` (81 rows, shuffled with seed 20260902). Caution: the pseudopotential file names in `make_inputs.py` (for example `Mo_ONCV_PBE-1.0.oncvpsp.upf`, `Se_pbe_v1.uspp.F.UPF`) differ from those in the committed inputs, which use the GBRV lower-case names (`mo_pbe_v1.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, `te_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `ti_pbe_v1.4.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`). To reproduce the measured runs, use the committed `pilot/inputs/*.pw.in` and do not regenerate them.
2. Settings in the committed inputs: SCF, 6x6x1 k-points, `ecutwfc` from the candidate metadata (35 Ry for WTe2_2H), `ecutrho = 8 x ecutwfc`, cold smearing 0.02 Ry; conservative `mixing_beta = 0.3`, `conv_thr = 1e-8`; aggressive `mixing_beta = 0.7`, `conv_thr = 1e-6`.
3. Pseudopotentials: GBRV ultrasoft PBE (the README mentions SSSP, but the measured runs used GBRV); sha256 hashes of the six files used are in `pilot/results/pseudos_manifest.txt`. Place them in `pilot/pseudos/`.
4. Software: Quantum ESPRESSO 7.4, modules `openmpi/5.0.3 quantum-espresso/7.4`.
5. Submission: `PILOT_AUTHORIZED=1 MAX_NODE_HOURS=<cap> bash pilot/submit.sh` (optional `PILOT_TARGET=kingspeak` for a multi-node layout). It walks `job_matrix.csv`, refuses to run without the two variables or without files in `pilot/pseudos/`, stops when the worst-case projected spend (nodes x 0.5 h per job) exceeds the cap, and submits `pilot/job_template.sbatch` with `--nodes=1 --ntasks=<16 x nodes>` (16, 32 or 64 tasks) and `--export=ALL,PILOT_CAND,PILOT_NPOOL,PILOT_AGG,PILOT_JOBID`. The template requests `--time=00:30:00` and writes to `$SCRATCH/mpt_pilot/job_<id>/`; replace the account, partition and QoS lines with `<account>`, `<partition>`, `<qos>`. The recorded run used `MAX_NODE_HOURS=100`.
6. Known difference: the measured batch used a corrected template (`mpirun -np $SLURM_NTASKS --bind-to none pw.x`, `OMP_NUM_THREADS=1`, GBRV file names), as recorded in `pilot/results/PILOT_RESULTS.md`. The committed `job_template.sbatch` still launches `srun pw.x` without setting `OMP_NUM_THREADS`; apply those two changes before rerunning. A first batch with the uncorrected template was cancelled and is excluded.
7. Collection: `pilot/collect_pilot.sh` runs on the cluster in `$SCRATCH/mpt_pilot_bundle` (the staging of the bundle to that folder is not in the repository), reads each `slurm-<id>.out`, `sacct` and `pw.out`, keeps job ids from the resubmitted batch only (hard-coded threshold 1914396; change it for a new run), and writes `pilot_results.csv` with the columns `pilot_analysis.py` expects. Copy it to `pilot/results/`. (`pilot/collect_results.sh` writes a different, sacct-only CSV that `pilot_analysis.py` cannot read.)
8. Then run `pilot_analysis.py` and `posterior_regrade.py` as above.
9. Observed cost: 81 jobs, 0.212 node-hours in total (16-core convention), 2.15 to 8.56 s `pw.x` wall time per job.

**Outputs.**

- `pilot/results/PILOT_RESULTS.md`
- `pilot/results/pilot_results.csv`, `pilot/job_matrix.csv`
- `pilot/results/pilot_fit.json`
- `pilot/results/posterior_regrade.json`
- `pilot/results/pseudos_manifest.txt`

**Checks.**

- 81/81 completed and SCF-converged, 0 failures (95% upper bound on the failure rate 3.6%).
- `pilot_fit.json`: parallel-efficiency exponent s = 0.425 (prior 0.65 +/- 0.10); configuration spread 0.061 (log sd); repeat noise 0.076 (log sd); aggressive-mode effect -0.269 in log wall time; pool effect -0.078; maximum memory 3.05 GB; mean wall per candidate 3.88 s (TiS2_1T), 4.09 s (MoSe2_2H), 5.21 s (WTe2_2H).
- Cross-term ablation: leave-one-cell-out RMSE 0.124 (additive) against 0.134 (with cross-party products), a held-out change of -8.1%.
- `posterior_regrade.json` (300 worlds): the only configuration with a non-zero joint-gain rate is `CEDT_P4`, at 0.07 / 0.19 / 0.203 (preregistered metrics) and 0.713 / 0.817 / 0.813 (execution-layer package) for scales x10 / x100 / x300.
- Limits: jobs last seconds on one dedicated node, so the exponent and noise terms describe that regime only; timings depend on node and load. The re-grade is a simulation; the posterior patch seeds each world from its index (CRC32), so a rerun with the same `POST_WORLDS`, simulator and `twin_fit.json` is expected to reproduce the fractions, provided the base simulator is seeded in the same way.

### `prior_predictive/`: prior-predictive digital-twin simulator, main contract grid, extension grid and their gradings

Level: simulated (all node-hours are simulated units; the grids were run on the DGX Spark (aarch64) with 18 worker processes, about 45 s wall time for the main grid). The 30 MX2 candidate structures are generated idealized prototypes, not measured inputs.

**Re-analyse from the committed records (no new compute).** Python 3 with `numpy`, `scipy` and `matplotlib`. All scripts resolve paths relative to their own file, so they can be run from the repository root.

1. Hard-cap dataset of record (grades `results/summary.json`, `results/drivers.json` and the four main figures). `analyze.py` reads the uncompressed file `results/raw_results.json`, which is not committed, so decompress the hard-cap records under that name first:
   `gunzip -c prior_predictive/results/raw_results_hardcap.json.gz > prior_predictive/results/raw_results.json`
   `python3 prior_predictive/analyze.py`
   Outputs (overwritten): `results/summary.json`, `results/drivers.json`, `results/winwin_probability.png`, `results/privacy_utility_frontier.png`, `results/eps_sensitivity.png`, `results/privacy_tax_vector.png`.
2. Soft-stop grading (`results/summary_pre_hardcap.json`): no script writes this file name. Decompress `results/raw_results.json.gz` to `results/raw_results.json`, run `analyze.py`, and compare the resulting `summary.json` with `summary_pre_hardcap.json` (then repeat step 1 to restore the file of record).
3. Reservation-gain renegotiation (reads `results/raw_results.json.gz`, the soft-stop grid, directly):
   `python3 prior_predictive/reanalysis_gR.py`
   Outputs: `results/gR_renegotiation.json`, `results/gR_renegotiation.png`.
4. Education axis and ablations (reads `results/ext_raw.json.gz`; the post hoc leakage-matching block also reads the current `results/summary.json`, so run step 1 first):
   `python3 prior_predictive/analyze_extensions.py`
   Outputs: `results/ext_summary.json`, `results/fig_education.png`, `results/fig_ablations.png`.

**Re-run the computation.**

1. Candidates (deterministic, no random numbers): `python3 prior_predictive/make_candidates.py` rewrites `candidates/candidates.json`, the 30 `.cif` files and `candidates/LICENSE`. `simulator.py` reads `candidates/candidates.json` at import.
2. Main grid under the hard budget cap (dataset of record):
   `MPT_HARD_CAP=1 python3 prior_predictive/simulator.py --worlds 1000 --sweep-worlds 250 --procs 18 --out results/raw_results.json`
   then `gzip -c prior_predictive/results/raw_results.json > prior_predictive/results/raw_results_hardcap.json.gz` if a compressed copy is wanted. `--out` is resolved relative to `prior_predictive/`. Worlds are split evenly over the `base`, `strong_coupling` and `adversarial` prior cards; the sweep worlds use ids from 100000. Omitting `MPT_HARD_CAP` (default `0`) gives the earlier soft-stop semantics of `raw_results.json.gz`. `MPT_TRACE` enables debug tracing only. `--smoke` runs 6 + 3 worlds on one process.
3. Extension grid (education axis Q0 to Q3 and the ablations):
   `python3 prior_predictive/extensions.py --worlds 1000 --procs 18 --out results/ext_raw.json`, then gzip to `results/ext_raw.json.gz`. `extensions.py` carries its own copy of the campaign loop and does not read `MPT_HARD_CAP`.
4. Then run the re-analysis steps above.

Seed handling: each world is drawn from `numpy.random.default_rng(crc32("<card>:<world_id>"))`, and the 30 paired seeds share common noise fields across conditions. `results/README.md` records that `raw_results.json.gz` predates this stable seeding (it used a process-salted hash), so a rerun reproduces its distributions but not its exact worlds; runs made after the fix are stated to be exactly reproducible. Whether `ext_raw.json.gz` predates the fix is not documented.

**Outputs.**

- `results/raw_results_hardcap.json.gz` (11,750 records: 1,000 worlds x 10 conditions + 250 sweep worlds x 7 conditions) and `results/raw_results.json.gz` (soft-stop predecessor)
- `results/summary.json`, `results/summary_pre_hardcap.json`, `results/drivers.json`
- `results/gR_renegotiation.json`, `results/ext_raw.json.gz` (18,000 records), `results/ext_summary.json`
- Figures: `winwin_probability.png`, `privacy_utility_frontier.png`, `eps_sensitivity.png`, `privacy_tax_vector.png`, `gR_renegotiation.png`, `fig_education.png`, `fig_ablations.png`

**Checks.**

- Soft-stop grid: P(win-win) for CEDT-P4 0.051, CEDT-P3 (eps = 4) 0.014, CTDE-P3 0.005; no condition reaches 0.80.
- Hard-cap grid (`summary.json`): CEDT-P4 0.041 (P(R gain) 0.049, P(H gain) 0.234, leakage pass 1.0), CEDT-P3 0.006, CTDE-P3 0.001; maximum campaign spend 496.5 simulated node-hours.
- Renegotiated reservation gain at 10 %: CEDT-P4 win-win 0.097, CEDT-P3 (eps = 2) 0.056.
- Education axis: mean competency Q0 0.913, Q1 0.897, Q2 with 0 hints 0.987.
- Reruns of the hard-cap grid with fixed seeds are expected to be identical; reruns compared with `raw_results.json.gz` agree statistically only. The attacker models, educator-effort constants and prior cards are model beliefs, not measurements.

### `result_sharing/`: exchange of scientific results among N research groups (records, verdicts, family counts, public claims, a booking broker and decoy refusals)

Level: simulated on measured inputs (measured 1x1 PBE gaps, DFT NEB and offset-corrected MACE vacancy barriers, measured gap-step and NEB node-hours). Run on the DGX Spark (aarch64): `peer_exchange.py` with 16 processes in 7 min; `broker_exchange.py` with 18 processes in about 25 min; `broker_decoy.py` on the same worlds and seeds (runtime not recorded). Campaign numbers are simulated units.

Registered predictions: `PREDICTION.md` (R1 to R6) and `BROKER_PREDICTION.md` (B1 to B4); graded in `RESULTS.md` and `RESULTS_BROKER.md`.

**Re-analyse from the committed records (no new compute).**

1. Each results JSON already holds the graded quantities per configuration (`configs[i]` with `n`, `o`, `e_min`, `asym`, `rule` and `grade[level]` containing `P_all_gain`, `pw_mean`, `q_mean`, `auc_pool`, `famadv_pool`, `P_leak_ok_pool`, `P_winwin_pool`, the single-peer counterparts and 10/50/90 % world percentiles). Print a summary with:
   `python -c "import json; d=json.load(open('result_sharing/results/broker_decoy.json')); [print(c['n'], c['o'], {lv: (round(g['P_all_gain'],3), round(g['P_leak_ok_pool'],3), round(g['P_winwin_pool'],3)) for lv,g in c['grade'].items()}) for c in d['configs']]"`
   (the same command works for `peer_exchange.json` and `broker_exchange.json`). `result_sharing/results/broker_diag.json` is a flat table of four levels.
2. No figure script is committed in this folder. The paper figure that uses these results is drawn by `fig_peer()` in `papers/paperA_disclosure_theory/figures/make_figures.py`, which reads the three JSON files above and writes `papers/paperA_disclosure_theory/figures/fig6_peer.pdf`. To draw only this figure:
   `python -c "import sys; sys.path.insert(0,'papers/paperA_disclosure_theory/figures'); import make_figures as m; m.fig_peer()"`

Python packages: numpy, scipy, matplotlib (figure only).

**Re-run the computation.**

1. `python result_sharing/peer_exchange.py --worlds 200 --seeds 30 --procs 16`
   Writes `result_sharing/results/peer_exchange.json` (default `--out`, resolved next to the script, so any working directory works; the file is rewritten after each configuration). Configurations: N in {2, 3, 5} x o in {0, 0.25, 0.5, 1} where feasible (E_min 1.5 eV, rule `mean`); N = 3 at o in {0, 0.5, 1} with E_min 1.7 eV and with rule `family`; N = 3 at o in {0, 0.5} with twice the budget for group 0. Levels X0, X1, X2, X3 and the post hoc X1c.
2. `python result_sharing/broker_exchange.py --worlds 200 --seeds 30 --procs 18`
   Writes `result_sharing/results/broker_exchange.json`; levels X0, X1c, Xb on the feasible (N, o) grid.
3. `python result_sharing/broker_decoy.py --worlds 200 --seeds 30 --procs 16`
   Writes `result_sharing/results/broker_decoy.json`; N = 3, o in {0.5, 1}, levels X0, Xb and Xb-d with q in {0.1, 0.2, 0.3, 0.5}. The process count of the committed run is not recorded.
4. `python result_sharing/broker_diag.py` (no arguments; fixed N = 3, o = 0.5, 60 worlds x 30 seeds, single process). Writes `result_sharing/results/broker_diag.json` and prints it.
5. Committed measured inputs read (through `peer_exchange.py` and `vacancy_barriers/twin_kmc/vacancy_goal.py`): `dft_campaign/results/outcomes.jsonl` (F3 gaps), `paired_comparison_1/results/campaigns.jsonl` (gap-step node-hours), `vacancy_barriers/dft_neb/results_dft/<compound>.json` and `grading.json` (7 DFT NEB barriers and wall times), `vacancy_barriers/results/vacancy_neb.jsonl` and `kmc_runs.jsonl` (MACE barriers), `prior_predictive/candidates/candidates.json`. `vacancy_goal.py` also imports `prior_predictive/simulator.py`, `centralization_surface/surface.py` and `centralization_surface/tau_diagnostic.py`.
6. Random-seed handling: barriers per world from `default_rng(crc32("pw:<rule>:<world>"))`; lists, gap estimates and cost noise per seed from `default_rng(crc32("ps:<world>:<N>:<o>:<seed>"))`; decoys from `default_rng(crc32("dec:<world>:<N>:<o>:<seed>:<q>"))`. All levels within a configuration share these draws (paired design), and the broker scripts reuse the peer-exchange streams, which is why X1c reproduces 0.335 against the earlier 0.34.

**Outputs.**

- `result_sharing/results/peer_exchange.json`
- `result_sharing/results/broker_exchange.json`
- `result_sharing/results/broker_decoy.json`
- `result_sharing/results/broker_diag.json`

**Checks.**

- Peer exchange, all-party win-win: 0 % of worlds for every registered level at every N and o. N = 3, o = 0.5: mean paired win rate 0.15 (X1), 0.12 (X2), 0.05 (X3); pooled membership AUC 0.86, 0.85, 0.53. Qualifiers per group under X0: 1.66.
- Post hoc X1c at N = 3, o = 1: every group gains in 0.335 of worlds, qualifiers per group 1.90, membership AUC 0.70.
- Broker (N = 3): all groups gain in 0.995 of worlds at o = 1; leakage limits met in 0.95, 0.04 and 0 of worlds at o = 0.25, 0.5, 1; best all-party win-win 0.03 (N = 5, o = 0.5).
- Decoys (N = 3, o = 0.5): all-party win-win 0.035, 0.06, 0.115, 0.26 for q = 0.1, 0.2, 0.3, 0.5; membership AUC 0.565, 0.537, 0.509, 0.458.
- Diagnostic: spend to first qualifier 2.08 (X0), 1.54 (Xb), 1.42 (q = 0.3), 1.34 nh (q = 0.5).
- All streams are seeded per world and seed, so reruns are expected to be identical with the same package versions; a verified rerun is not in the repository.
- Limits stated in the results files: fixed lists, synchronous rounds, one goal; 23 of 30 barriers are offset-corrected MACE values; X1c and the decoy level were added after the first registered run (X1c is exploratory; B4 was registered before the decoy run).

### `scale_validation/`: measured SCF cost against electron count (in-plane supercells), with the layers and initial-setup extension in `layers_naxis/`

Level: measured on hardware (CHPC granite node grn061, owner partition, CPU only, 32 MPI ranks of the node's 64 cores; node memory 380 GB; the node's GPU is not used).

**Re-analyse from the committed records (no new compute).** Python 3 with `numpy`.

1. Supercell series: `python3 scale_validation/scale_analysis.py`. Reads `scale_validation/results/results.jsonl`; prints the per-run table; writes `scale_validation/results/scale_fit.json` (electron exponent per family on the 6×6 k-grid series, k-point exponent from `MoSe2_2H_s2_k6` vs `MoSe2_2H_s2_k12`, cost multipliers relative to the mean 1×1 cost). Node-hours are computed as `ranks / 16 × wall_s / 3600`.
2. Layers and setup extension: `python3 scale_validation/layers_naxis/layers_analysis.py`. Reads `scale_validation/layers_naxis/results/results.jsonl`; writes `scale_validation/layers_naxis/results/layers_fit.json` (exponents for layers, in-plane and mixed series; strained-start wall and iteration ratios; cross-material spread). Node-hours here are computed as `ranks / 64 × wall_s / 3600`.

Neither script takes arguments. Per-run QE outputs (`scale_validation/results/*.out`, `scale_validation/layers_naxis/results/raw_outputs/*.out`) allow the jsonl fields (wall time aside) to be checked by hand.

**Re-run the computation.**

1. Inputs. Both builders derive their structures, cutoffs and pseudopotential names from `pilot/inputs/<candidate>.pw.in` and take no arguments:
   - `python3 scale_validation/build_scale_inputs.py` writes 8 decks to `scale_validation/inputs/`: TiS2_1T and MoSe2_2H at n×n = 1, 2, 3 on a 6×6×1 grid, `MoSe2_2H_s2_k12` (12×12×1, k-point check) and `MoSe2_2H_s4_k3` (4×4 supercell, 832 electrons, 3×3×1).
   - `python3 scale_validation/layers_naxis/build_layers_inputs.py` writes 17 decks to `scale_validation/layers_naxis/inputs/`: z-stacks L1 to L3 (3.2 Å gap between chalcogen planes) crossed with 1×1 and 2×2 in-plane cells, ±2 % strained 2×2 starts for TiS2_1T and MoSe2_2H, and WTe2_2H at 1×1 and 2×2; all on 6×6×1.
   - Common settings: SCF, ecutwfc 40 Ry, ecutrho 320 Ry, cold smearing 0.02 Ry, mixing 0.3, conv_thr 1e-8, Davidson, at most 80 steps. The committed decks are the ones that were run.
2. Pseudopotentials: GBRV ultrasoft PBE, files `ti_pbe_v1.4.uspp.F.UPF`, `s_pbe_v1.4.uspp.F.UPF`, `mo_pbe_v1.uspp.F.UPF`, `se_pbe_v1.uspp.F.UPF`, `w_pbe_v1.2.uspp.F.UPF`, `te_pbe_v1.uspp.F.UPF`. SHA-256 hashes: `pilot/results/pseudos_manifest.txt`. The UPF files are not in the repository; place them in a `pseudos/` directory next to the sbatch file (the scripts copy `pseudos/*.UPF` from the submit directory).
3. Software: Quantum ESPRESSO 7.4 (`pw.x`, "PWSCF v.7.4" in the outputs), modules `openmpi/5.0.3 quantum-espresso/7.4`, `OMP_NUM_THREADS=1`, `mpirun --bind-to none`.
4. Jobs (submit from the folder holding `inputs/` and `pseudos/`; replace `--account`, `--partition`, `--qos` by `<account>`, `<partition>`, `<qos>`; the working directory is `$SCRATCH/mpt_scale` or `$SCRATCH/mpt_layers`):
   - `sbatch scale.sbatch`: 1 node, 32 tasks, 8 h wall, runs the decks sequentially with a 4 h per-run timeout; `-npool 2` (1 for `*_k3`, 4 for `*_k12`).
   - `sbatch layers_naxis/layers.sbatch` (submitted from `layers_naxis/`): 1 node, 32 tasks, 2 h wall, 30 min per-run timeout, `-npool 2`.
   Each script appends one JSON line per run to `results.jsonl` (wall, convergence flag, electrons, k-points or atoms, SCF iterations, total energy for the layers run) and copies `results.jsonl` and `*.out` to a results directory in the submitting user's home area.
5. Collect: copy `results.jsonl` and the `.out` files into `scale_validation/results/` (layers: `results.jsonl` into `layers_naxis/results/`, `.out` files into `layers_naxis/results/raw_outputs/`), then run the two analysis scripts above. No collection script is in the repository for these two jobs.
6. Observed cost: supercell job 22 min 52 s wall, 0.76 node-hours in the ranks/16 convention; layers job about 22 min wall, 0.16 node-hours in the ranks/64 convention (`layers_fit.json`, `total_node_hours`).

**Outputs.**

- `scale_validation/results/results.jsonl`, `scale_validation/results/scale_fit.json`, `scale_validation/results/*.out`
- `scale_validation/layers_naxis/results/results.jsonl`, `scale_validation/layers_naxis/results/layers_fit.json`, `scale_validation/layers_naxis/results/raw_outputs/*.out`, `scale_validation/layers_naxis/results/slurm-1919292.out`
- Summaries: `scale_validation/RESULTS.md`, `scale_validation/layers_naxis/RESULTS.md`

**Checks.**

- Supercell series: 8/8 converged; wall times from 4 s (TiS2 1×1) to 695 s (MoSe2 4×4, 832 electrons). Electron exponents on the 6×6 series: TiS2_1T 1.63, MoSe2_2H 1.90; k-point exponent 0.61. Cost multipliers against the 1×1 mean: about 6 to 10 (2×2), 34 to 79 (3×3), 154 (4×4).
- Layers extension: 17/17 converged. Exponents (layers / in-plane / mixed L2×s2): TiS2_1T 1.32 / 1.60 / 1.61; MoSe2_2H 1.95 / 2.03 / 2.07. Strained starts change wall time by -7 % to +8 % against the unstrained parent. Max/min wall ratio across the three materials: 1.5 at 1×1, 1.81 at 2×2.
- Limits: wall times depend on the node, MPI layout and concurrent load; expect the exponents and ratios, not the seconds, to reproduce on other hardware. Each point is a single measurement (no repeats). The two analysis scripts use different node-hour conventions (ranks/16 and ranks/64); compare costs only within one convention.

### `shared_stations/`: disclosure contracts at a shared tube furnace and sputter deposition line (simulated growth stations)

Level: simulated. Every station parameter (temperatures, rates, run times, calibration errors) is an assumed value; the only measured content is the list of eight MX2 compositions with a PBE gap in 1.0 to 2.0 eV, which is hard-coded in `station_sim.py` (`COMPS`) and not read from a file at run time. The committed run took 132 s on 8 cores; the machine is not named in the repository.

Design and registered predictions S1 to S7: `shared_stations/DESIGN_AND_PREDICTION.md`; results: `shared_stations/RESULTS.md`.

**Re-analyse from the committed records (no new compute).**

1. Regenerate the figure from the committed graded summary (paths are taken from the command line, relative to the working directory):
   `python shared_stations/make_figure.py shared_stations/results/station_summary.json shared_stations/results/`
   Output: `shared_stations/results/fig_shared_stations.png`.
2. The grading step (`analyze.py`) needs the per-campaign file `station_raw.json` (about 74 MB), which is not committed. Re-grading therefore requires the rerun below; the committed `station_summary.json` and `predictions_graded.json` are its outputs.

Python packages: numpy, matplotlib.

**Re-run the computation.**

1. From the repository root:
   `python shared_stations/station_sim.py --worlds 150 --seeds 15 --procs 8 --out shared_stations/results`
   `--out` defaults to `results` relative to the working directory, so either pass it as shown or run from inside `shared_stations/`. Other options: `--grid` (default 6, giving the tau and eps grid 0, 0.2, ..., 1.0) and `--ps` (default `P2,P3`). Output: `shared_stations/results/station_raw.json` (not committed). The defaults (80 worlds, 10 seeds, 6 processes) are not those of the committed run.
2. Conditions per world: 36 (tau, eps) cells for each of P2 and P3, ten P4 variants (open tube with 50 C or 100 C programme menu, sealed ampoules with no, 50 C or 100 C menu, each at eps = 0 and 1) and a CTCE reference, 83 in total. `RESULTS.md` states 78 conditions; the committed `station_summary.json` holds 83 graded conditions.
3. Grade and write the summary and the prediction verdicts:
   `python shared_stations/analyze.py shared_stations/results/station_raw.json shared_stations/results/`
   Outputs: `station_summary.json` and `predictions_graded.json` in the given directory.
4. Redraw the figure as in step 1 of the re-analysis.
5. Random-seed handling: each world from `default_rng([world, 999])` and each campaign from `default_rng([world, seed, 7])`, so every condition shares the same world and seed streams and the result does not depend on the number of processes. `RESULTS.md` states that the command regenerates the raw file exactly.

**Outputs.**

- `shared_stations/results/station_summary.json` (graded metrics per condition; 150 worlds, 15 seeds)
- `shared_stations/results/predictions_graded.json` (S1 to S7)
- `shared_stations/results/fig_shared_stations.png`

**Checks.**

- S1 (logbook shortens hours to first film by at least 10 %): -0.004, fail.
- S2 (full brokering at P3 gives at least 1.05 x films per furnace-hour in at least 80 % of worlds): 0.947, pass; median ratio 1.19 x.
- S3 (furnace-log identification above 0.175 in at least 95 % of worlds, every arm): minimum 0.98, pass.
- S4 (sealed ampoules): identification drop 0.184; co-firing gain 1.189 (open) against 1.264 (ampoules), pass.
- S5: furnace log 0.506, deposition log 0.494, joined 0.94, pass.
- S6 (thermocouple offset recovered from a shared logbook): correlation 0.795 (P2), 0.704 (P3), 0.754 with no logbook, pass.
- S7: absolute-limit win-win 0 everywhere; best rebased win-win at tau = 0 is 0.367, fail.
- Limits stated in `RESULTS.md`: all station parameters assumed; offsets and rate factors constant within a campaign; identification scored one log entry at a time (a lower bound); leakage of one group's list to other groups through the logbook not graded.

### `sociability_map/`: value of information exchange versus its leakage price across task scale, on the calibrated twin

Level: simulated on measured inputs (the simulator of `prior_predictive/simulator.py`, recalibrated with the measured cost fit `stage2_twin_fit/twin_fit.json`; all node-hours are simulated units). Run on a DGX Spark CPU, base prior card only.

**Re-analyse from the committed records (no new compute).** Python 3 with numpy and matplotlib.

1. `python ceiling_diagnosis/make_figures.py` (from the repository root; paths resolve relative to the script). Reads `sociability_map/sociability_map.json` and regenerates `sociability_map/fig_sociability_map.png`. The script also rewrites `ceiling_diagnosis/results/fig_ceiling_decomposition.png`, `decision_maker_leakage/fig_dm_leakage.png` and `governance_regrade/fig_governance.png` from their committed JSON records.
2. Per-scale, per-contract numbers (`labels_ratio`, `nh_first_saving`, `found`, `fail`, `worst_leak_util`, `p_leak_ok`, the six leakage channels) are read directly from `sociability_map/sociability_map.json` under `results.scale_<s>.<condition>`; no further script is needed.

**Re-run the computation.**

1. `python sociability_map/sociability_map.py` (no command-line arguments). Environment variables: `SOC_WORLDS` (default 150), `SOC_SCALES` (default `1,3,10,30,100,300,1000`); the script sets `MPT_HARD_CAP=1` by default (hard 500 simulated nh campaign cap). Explicit form:
   `SOC_WORLDS=150 SOC_SCALES=1,3,10,30,100,300,1000 python sociability_map/sociability_map.py`
2. Inputs read: `stage2_twin_fit/twin_fit.json` (measured amplitudes, `p_e`, log residual SD, minimum per-call node-hours) and `prior_predictive/simulator.py` (imported via `sys.path`). Per-sbatch overhead is fixed at 0.02 nh in the script.
3. Conditions: DTDE-P4 (baseline), CTDE-P2, CTDE-P3 (eps=2), CTDE-P4, CEDT-P2, CEDT-P3 (eps=2), CEDT-P4, CTCE-P0; 30 paired seeds per world (simulator default).
4. Parallelism: a `multiprocessing.Pool` with `os.cpu_count()` workers per scale. The script sets the scale as a module global and patches the simulator before creating the pool, so it relies on the `fork` start method (Linux); under `spawn` the workers would not see the calibration.
5. Seeds: base worlds from CRC32 of `card:world_id`, calibration perturbations from CRC32 of `emp:card:world_id`; no unseeded randomness, so a rerun on the same numpy version should be bit-identical. Runtime is not recorded.
6. Output is written to `sociability_map/sociability_map.json` (overwrites the committed file).

**Outputs.**
- `sociability_map/sociability_map.json`
- `sociability_map/fig_sociability_map.png`

**Checks.**
- Labels/nh ratio vs DTDE-P4 (`labels_ratio`) rising from x1 to the x100 to x300 plateau, as stated in `RESULTS.md`: CTCE-P0 1.07 to 1.35, CEDT-P2 1.06 to 1.27, CEDT-P4 1.03 to 1.15 to 1.17. In the JSON, CEDT-P4 reads 1.032 (x1), 1.146 (x100), 1.148 (x300), 1.165 (x1000); CTCE-P0 reads 1.071 (x1), 1.342 (x100), 1.346 (x300), 1.256 (x1000). At x1 every contract lies within 6 % of DTDE-P4.
- Worst-channel leakage utilisation is flat across scale: CEDT-P2 about 2.0 (limit breached), P3 with eps=2 about 1.0, P4 about 0.73 (e.g. `scale_100`, DTDE-P4 `worst_leak_util` = 0.726).
- CEDT-P4 exceeds CTDE-P2 in value at every scale from x3 upward.
- Limit: the scale-validation measurements referred to in `RESULTS.md` live in `scale_validation/`, not in this folder.

### `stacking_study/`: 2H geometry check (single-layer 2H, AA' bilayer and 3R bilayer with DFT-D3) for 15 MX2 compositions, with follow-up relaxations, spin-orbit gaps and Gamma phonons (`stacking_study/followup_2026-10-12/`)

Level: measured on hardware. Main run: one CHPC granite guest node (free guest partition, 32 cores and 120 GB requested; exact node model not recorded). Follow-up: CHPC notchpeak guest nodes (32 cores, 96 GB requested, preemptible, submitted with `--requeue`). CPU-only Quantum ESPRESSO.

**Re-analyse from the committed records (no new compute).**

1. No analysis script for this folder is in the repository; the driver writes the summaries directly. The records are JSON and can be read with the Python 3 standard library (`json`).
2. Main run: `stacking_study/results_2088961/outcomes.jsonl` (one record per cell; fields `candidate`, `stages.F2.relax_converged`, `a_relaxed_angstrom`, `gap_ev`, `qualifier`) and `stacking_study/results_2088961/stacking_summary.json` (totals and full records).
3. Follow-up: `followup_2026-10-12/results/relax/results_16208957/{outcomes.jsonl,followup_relax_summary.json}` and `followup_2026-10-12/results/socph/results_16208958/{soc_outcomes.jsonl,phonon_outcomes.jsonl,followup_socph_summary.json}`.

**Re-run the computation.**

Main run (`results_2088961`):

1. Inputs are generated inside the driver: `stacking_study/run_stacking.py` (no arguments) builds 45 cells (Ti, Zr, Hf, Mo, W x S, Se, Te x `mono2H`, `bi2H`, `bi3R`), writes `candidates.json` into `$MPT_DFT_ROOT`, and reuses `dft_campaign/run_campaign.py` for the F1 to F3 ladder (F1 SCF 40 Ry 6x6x1; F2 `vc-relax` `2Dxy` 45 Ry 12x12x1; F3 NSCF 18x18x1; no phonons). Bilayers add `vdw_corr = 'dft-d3'`, `dftd3_version = 4` (Becke-Johnson damping), start at a metal-metal distance of 6.2/6.5/7.0 A (S/Se/Te) in a 30 A cell; single layers use a 20 A cell.
2. Pseudopotentials: GBRV ultrasoft PBE, the same eight files as `dft_campaign/` (listed in `stacking_study/stage_and_submit_stacking.sh`, downloaded from the GBRV site). Partial sha256 manifest: `pilot/results/pseudos_manifest.txt` (Zr and Hf not hashed).
3. Software: Quantum ESPRESSO 7.4, modules `openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3`.
4. Staging and submission: `bash stacking_study/stage_and_submit_stacking.sh` (requires an authenticated SSH connection and `CHPC_USERNAME`; optional `MPT_GUEST_PART`, `MPT_GUEST_ACCT`, `MPT_GUEST_QOS` set `<partition>`, `<account>`, `<qos>`). It creates `$SCRATCH/mpt_stack/{pseudos,results}`, downloads the pseudopotentials, copies `run_stacking.py`, `stacking.sbatch` and `run_campaign.py`, runs `sbatch --test-only`, and submits only when `MPT_STACK_SUBMIT=1` (job id written to `stacking_study/.stack_jobid`).
5. `stacking_study/stacking.sbatch`: `--nodes=1 --ntasks=32 --mem=120G --time=24:00:00`; `OMP_NUM_THREADS=1`, `MPT_NPROC_PER_RUN=16`, `MPT_NPOOL=4`, `MPT_WORKERS=2`, `MPT_NODE_HOUR_CAP=12`.
6. Collection: the job copies `results/` to `$HOME/mpt_stack_results/results_<jobid>`; a collection script for this run is not in the repository (copy `outcomes.jsonl` and `stacking_summary.json` into `stacking_study/results_<jobid>/`).
7. Observed cost: 2.712 h wall, 138 QE calls, 1.355 node-hours (driver convention: wall x cores used / 64).

Follow-up (`followup_2026-10-12/`):

1. Driver `followup_2026-10-12/run_followup.py <mode>` with `mode` = `relax` or `socph` (first positional argument). It reads the main-run records from `$MPT_STACK_OUTCOMES` (set by the sbatch file to `$MPT_DFT_ROOT/stack_outcomes.jsonl`, a copy of `results_2088961/outcomes.jsonl`). `relax`: TiS2_mono2H and ZrS2_bi3R with `mixing_mode = 'local-TF'`, `conv_thr = 1e-10` in the relaxation, `trust_radius_ini = 0.2`, `nstep = 300`, start `a` from the relaxed AA' bilayer. `socph`: for the seven single-layer 2H cells in the 1.0 to 2.0 eV window, a SOC gap through `dft_campaign/soc/soc_campaign.py` (PSL 1.0.0 fully relativistic PAW, 60/400 Ry, hashes in `dft_campaign/soc/PSEUDOS.md`) and a Gamma `ph.x` on the GBRV ladder at the fixed geometry.
2. `followup_2026-10-12/followup.sbatch`: `--nodes=1 --ntasks=32 --mem=96G --time=12:00:00 --requeue`; same module stack; `MPT_WORKERS=2`, `MPT_NODE_HOUR_CAP=4`. A requeued attempt renames earlier `*.jsonl` files to `*.jsonl.preempted_<stamp>`.
3. Staging and submission: `followup_2026-10-12/stage_and_submit.sh`, run from the repository root with `PSL_DIR` pointing to the seven PSL files. Its variable `M` is the repository root (`.`). It copies the GBRV files from the main run's scratch folder `$SCRATCH/mpt_stack/pseudos`, so the main run must be staged first. It submits with `-A <account> -p <partition> --qos=<qos>` and `--export=ALL,MODE=<mode>,MPT_DFT_ROOT=<dir>`; it also submits an unrelated job from `vacancy_barriers/floor_125C/`, which can be removed.
4. Collection: `followup_2026-10-12/collect_followup.sh` (run from the repository root) copies `$HOME/mpt_stackfu_results/<mode>/results_<jobid>` into `followup_2026-10-12/results/`.
5. Observed cost: `relax` 0.277 h wall, 6 QE calls, 0.084 node-hours; `socph` 0.368 h wall, 28 QE calls, 0.184 node-hours.

**Outputs.**

- `stacking_study/results_2088961/outcomes.jsonl`, `stacking_study/results_2088961/stacking_summary.json`
- `stacking_study/followup_2026-10-12/results/relax/results_16208957/outcomes.jsonl`, `followup_relax_summary.json`
- `stacking_study/followup_2026-10-12/results/socph/results_16208958/soc_outcomes.jsonl`, `phonon_outcomes.jsonl`, `followup_socph_summary.json`

**Checks.**

- Main run: 45 cells, 43 relaxations converged; TiS2_mono2H (BFGS cycling at 0.002 Ry/bohr) and ZrS2_bi3R (SCF loss at the first BFGS step) did not.
- 16 cells in the 1.0 to 2.0 eV window: single layer HfS2, MoS2, MoSe2, MoTe2, WS2, WSe2, WTe2; AA' bilayer MoS2, MoSe2, WS2, WSe2; 3R bilayer MoS2, MoSe2, WS2, WSe2, WTe2.
- Example PBE gaps (eV): MoS2 single layer 1.6735, AA' 1.2592, 3R 1.2372; WS2 single layer 1.8368. MoS2 single-layer `a` = 3.1817 A.
- Follow-up `relax`: both cells converge; F3 gaps TiS2_mono2H 0.7383 eV, ZrS2_bi3R 0.6074 eV, neither in the window.
- Follow-up `socph`: SOC gaps (eV) HfS2 1.1035, MoS2 1.6067, MoSe2 1.3515, MoTe2 0.9298, WS2 1.5764, WSe2 1.2885, WTe2 0.7474; Gamma minimum frequencies from -24.6 cm-1 (HfS2) to +4.7 cm-1 (MoTe2), none below the -30 cm-1 instability threshold.
- Limits: twisted bilayers are not included (smallest commensurate cell has 42 atoms). Gaps are PBE screening quantities; the SOC shift also contains the GBRV to PSL pseudopotential change; Gamma phonons are not a stability proof. Guest nodes are preemptible and heterogeneous, so wall times and node-hours are not comparable across reruns; node-hours use a 64-core denominator regardless of the guest node size.

### `stage2_twin_fit/`: calibration of the cost twin against the measured Quantum ESPRESSO calls and recalibrated re-grade of the contract grid

Level: analysis of committed records (the 98 scalar QE calls of `dft_campaign/`, measured on CHPC granite node grn061, 64 cores, 380 GB, 16 MPI ranks and 4 pools per call), followed by a simulated re-grade (prior-predictive twin, simulated node-hours) on the DGX Spark (aarch64, 20 cores).

**Re-analyse from the committed records (no new compute).**

1. Rebuild the call table: `python3 stage2_twin_fit/build_dataset.py` (no arguments). Reads `dft_campaign/results/outcomes.jsonl`, `dft_campaign/soc/results/soc_outcomes.jsonl` (when present) and `prior_predictive/candidates/candidates.json`; writes `stage2_twin_fit/qe_calls.csv` (116 rows: 98 scalar calls and 18 spin-orbit calls).
2. Parametric fit: `python3 stage2_twin_fit/fit_twin.py` (no arguments). Reads `qe_calls.csv` (scalar rows only); writes `stage2_twin_fit/twin_fit.json` and prints it.
3. Symbolic refit: `python3 stage2_twin_fit/pysr_fit.py` (no arguments). Reads `qe_calls.csv`; writes `stage2_twin_fit/pysr_wall_fit.json`. The validation split is fixed (numpy seed 41, one fifth of candidates held out) but PySR runs with `deterministic=False` and multithreading, so the selected expression can differ between runs.
4. Packages: Python 3 with numpy (steps 1 and 2 need only the standard library and numpy); step 3 needs PySR with its Julia back end (the original run used the PySR environment of `stage1_symbolic_recovery/`, PySR 2.2.0 per that folder's RESULTS.md).

All three scripts overwrite the committed files in place; compare against the committed versions with a version-control diff.

**Re-run the computation.**

1. The measured QE calls are not re-run here; they come from `dft_campaign/` (see that folder's instructions for inputs, pseudopotentials and job scripts).
2. Recalibrated re-grade: `MPT_HARD_CAP=1 python3 stage2_twin_fit/recalibrate.py --worlds 300 --card base --scales 1,10,100,1000,10000` (these are the script defaults; `--procs` defaults to the number of CPU cores). Reads `twin_fit.json` and imports `prior_predictive/simulator.py`; writes `stage2_twin_fit/recalibrated_grade.json` and prints the best contract and DTDE node-hours per scale. The in-allocation overhead scenario is run at scale 1 only.
3. Run order: `build_dataset.py`, `fit_twin.py`, then `recalibrate.py`; `pysr_fit.py` is independent of the re-grade.
4. Hardware and cost: the original re-grade ran on the DGX Spark (CPU, multiprocessing). Its wall time is not recorded.
5. The two-panel figure `stage2_twin_fit/stage2_calibration.png` has no generating script in the repository.

**Outputs.**

- `stage2_twin_fit/qe_calls.csv`
- `stage2_twin_fit/twin_fit.json`
- `stage2_twin_fit/pysr_wall_fit.json`
- `stage2_twin_fit/recalibrated_grade.json`
- `stage2_twin_fit/STAGE2_RESULTS.md` (summary tables), `stage2_twin_fit/stage2_calibration.png`

**Checks.**

- `twin_fit.json`: electron exponent p_e = 1.202 (prior 2.5), R^2 = 0.953 over n = 98 calls, residual sd 0.342 in log; stage amplitudes A(F1) = 0.000398, A(F2) = 0.009462, A(F3) = 0.000906, A(F4) = 0.015754 node-hours, that is prior over measured ratios of 3,015, 1,268, 8,830 and 2,539. Memory fit R^2 = 0.009 with a flat 0.138 GB per rank; minimum call cost 0.0002 node-hours; 18 spin-orbit rows available.
- `pysr_wall_fit.json`: selected expression of complexity 22, validation MSE 0.067, R^2 = 0.971 over all calls (an in-range interpolator; do not extrapolate).
- `recalibrated_grade.json`: the best contract is CEDT-P4 at every scale; P(win-win) 0.003 at measured scale with per-job overhead, 0.207 with in-allocation overhead, peaking at 0.203 at 100 times the measured cost and falling to 0.030 at 10,000 times; DTDE uses 2.0 of the 500 simulated node-hours at measured scale. With 300 worlds the probabilities carry about plus or minus 0.02 to 0.03.
- Known limits: every QE stage ran one fixed k-grid and one execution configuration, so the k-point exponent, parallel efficiency and contention are not identifiable and stay at their priors; a single prior card (base) is re-graded; the overhead scenarios are estimates.

### `timing_masking/`: price of masking clauses (quantized completion times, class-constant padding) against the measured timing attack

Level: analysis of committed records. The underlying records are the 480 measured Quantum ESPRESSO calls of live comparison No. 1 (SLURM jobs 1919944/1919945), run on CHPC granite node grn061 (64 cores, 380 GB RAM, single-node partition). The masks are applied analytically to the measured wall times; no masked job was executed.

**Re-analyse from the committed records (no new compute).**

Python 3 with `numpy` (sweep) and `matplotlib` (figure). Both scripts locate their files relative to their own directory, so they can be called from the repository root. Each script overwrites its committed output in place; work in a fresh copy of the repository and compare the regenerated file with the committed one.

1. Masking sweep:
   `python3 timing_masking/mask_study.py`
   - reads `paired_comparison_1/results/campaigns.jsonl` (per-job `arm`, `seed`, `opaque_id`, `candidate`, `cls`, `wall_s`);
   - writes `timing_masking/mask_results.json` and prints one line per clause.
   - Sweep (hard-coded): no mask; quantization q = 5, 15, 30, 60, 120, 300, 600, 1200, 3600 s; padding to the class percentile p = 90, 95, 99, 100.
   - Attacks (identical to `paired_comparison_1/wire_attack.py`): leave-one-seed-out identity attack (median wall per candidate and class from the other seeds, nearest neighbour in mean absolute log-wall distance) and membership AUC. Limits: identity accuracy at most 1/27 + 0.05 = 0.087, membership AUC at most 0.60. The worst arm (DTDE or CEDT_P4) is reported.
2. Figure:
   `python3 timing_masking/make_figure.py`
   - reads `timing_masking/mask_results.json`; writes `timing_masking/fig_timing_masking.png`.

**Re-run the computation.**

The folder has no compute of its own and no random seed (the sweep is deterministic). To regenerate the input records, re-run live comparison No. 1 as documented in `paired_comparison_1/` (driver `live_campaign.py`, collection `collect_live.sh`), then repeat steps 1 and 2 above.

**Outputs.**

- `timing_masking/mask_results.json` (fields `n_candidates`, `prior_identity`, `identity_limit`, `membership_auc_limit`, and `sweep` rows with `cost_inflation`, `worst_identity_acc`, `worst_membership_auc`, pass flags and `per_arm`)
- `timing_masking/fig_timing_masking.png`
- `timing_masking/RESULTS.md` (summary table)

**Checks.**

From `mask_results.json` (27 candidates in the records, prior 0.037, identity limit 0.087):

| clause | cost inflation | worst identity | worst membership AUC |
| --- | ---: | ---: | ---: |
| none | 0 | 0.9625 | 1.000 |
| quant 60 s | +20.2 % | 0.575 | 0.884 |
| quant 300 s | +124.1 % | 0.1125 | 0.550 |
| quant 600 s | +303.7 % | 0.050 | 0.500 |
| pad p95 | +124.6 % | 0.200 | 0.482 |
| pad p99 | +151.1 % | 0.075 | 0.501 |

Known limits:

- The stratified-padding row of `RESULTS.md` (padding by class and phase, +62 %) is not produced by `mask_study.py`; `make_figure.py` draws it as a fixed point (62.1 %, 1/14). The script that computed it is not in the repository.
- Cost is computed as the ratio of masked to true summed wall time; whether it is latency or billed node time depends on the accounting (see `billing_regrade/`).
- References are built from masked walls (a wire-only attacker); an executor holding unmasked references would do somewhat better at small q, so the small-q rows are lower bounds on attack success.
- Wall times, and hence all numbers, are specific to grn061 and the 3x3 supercell job sizes; seed-level confidence intervals for every row are in `bootstrap_ci/seed_bootstrap.json`.
