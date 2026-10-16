# Corrected 2H cells: follow-up runs (12 Oct 2026)

These runs close the three gaps left by
the stacking check (job 2088961, `../README.md`):

| Job | What | Cells | Settings |
| --- | --- | --- | --- |
| `stackfu_socph` | spin-orbit gap and Gamma-point phonons | the seven single-layer 2H cells with a PBE gap in 1.0-2.0 eV: HfS2, MoS2, MoSe2, MoTe2, WS2, WSe2, WTe2 | SOC: PSL 1.0.0 fully relativistic PAW (`../../dft_campaign/soc/PSEUDOS.md`, hashes re-checked), 60/400 Ry, 12x12x1 SCF, 18x18x1 NSCF. Phonons: GBRV, 45/360 Ry, 12x12x1 SCF at 1e-9, ph.x at Gamma. Geometry frozen from 2088961 |
| `stackfu_relax` | relaxation, then F3 gap | TiS2 single-layer 2H; ZrS2 3R bilayer (DFT-D3) | same F1-F3 ladder as 2088961; start a from the relaxed AA' bilayer of the same compound; `mixing_mode = 'local-TF'`; `conv_thr = 1e-10` inside the relaxation; `trust_radius_ini = 0.2`; `nstep = 300` |

Why the two relaxations failed in 2088961: TiS2 single-layer 2H cycled at BFGS step 8
until the 100-step limit with forces already at 0.002 Ry/bohr (energy noise against the
line search, hence the tighter SCF threshold); ZrS2 3R bilayer lost SCF convergence at
the first BFGS step (charge sloshing across the 30 A vacuum, hence local-TF mixing).

Interpretation limits as before: Gamma phonons are not a dynamical-stability proof
(a mode below -30 cm-1 flags an instability); PBE and SOC gaps are screening quantities;
the SOC shift mixes the spin-orbit effect with the change of pseudopotential family.

Files: `run_followup.py` (modes `relax`, `socph`), `followup.sbatch`,
`stage_and_submit.sh` (stages to `/scratch/general/vast/$USER/mpt_stackfu/{relax,socph}`
and submits on notchpeak-guest, plus the 125 C floor twin rerun of
`../../vacancy_barriers/floor_125C/`), `collect_followup.sh`.

## Submission record

Submitted 2026-10-12 18:12 UTC on notchpeak-guest (account owner-guest, qos
notchpeak-guest, 32 cores, `--requeue`; grn061 was running No. 3b seed 3):
`16208957` stackfu_relax, `16208958` stackfu_socph, `16208959` mpt_floor125.
Scratch: `/scratch/general/vast/$USER/mpt_stackfu/{relax,socph}`, `mpt_floor125`;
copies of results land in `~/mpt_stackfu_results/` and `~/mpt_floor125_results/`.
PSL hashes on the cluster were re-checked against `PSEUDOS.md` (7/7 match).
