# Memory-band probe (future-work item 4)

Submitted 2026-09-10 as granite job **`1928420`** on grn061
(sparks-gpu-grn, node was empty — no guests preempted). Guards:
`MPT_PROBE_NH_CAP=30` per-core node-hours, `--time=44:00:00`,
smallest-first ordering with graceful skip at the cap.

What it measures: the growth of the
lean(nk1)/fast(nk4) config spread and the RAM law across 75–384-atom
supercells (1,300–3,300 electrons) — the live approach to the simulated
×300–×3000 coupling band whose onset extrapolates to ≈17.6k electrons.

## Collecting results

Requires an authenticated SSH connection to the cluster (CHPC uses Duo
two-factor login).

```
ssh -fNM -o ControlPath=~/.ssh/cm/%r@%h:%p "$CHPC_USERNAME@granite1.chpc.utah.edu"
ssh <cm> 'squeue -j 1928420'   # or: squeue -M granite from any CHPC login
scp <cm> $SCRATCH/mpt_memband/results/probe_results.jsonl memory_band_probe/results/
scp <cm> $SCRATCH/mpt_memband/probe_1928420.log memory_band_probe/results/
```

where `$SCRATCH=/scratch/general/vast/$USER`. Multi-cluster status also
works from kingspeak: `squeue -M granite -j 1928420`.

Analysis to run on collection: per-size config spread
(wall_fast vs wall_lean per candidate, per-core charge), RAM/process vs
electrons refit, and the registered decision gate
(spread ≥ ~10% by 8×8 → authorize live comparison No. 2; < 5% → the
positive-characterization conclusion stands). Clean up
`$SCRATCH/mpt_memband` after collection.
