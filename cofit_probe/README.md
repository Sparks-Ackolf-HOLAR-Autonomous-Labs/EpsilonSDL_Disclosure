# Co-scheduling (packing) probe — gate for live comparison No. 2

Why this probe exists: job `1928420` showed that below the (measured)
memory wall the optimal npool is class-determined and DTDE's
conservative config is accidentally optimal — so the per-candidate
disclosure surface at coupling-band scale is **memory-aware
co-residency**, not config choice
(`../memory_band_probe/results/RESULTS.md`). Comparison No. 2 therefore
pits packing policies against each other, and this probe measures the
three inputs that design needs, for ~2 per-core node-hours:

1. **wall(16 ranks) solo** for MoSe2_2H and WTe2_2H 6×6 (the two
   heaviest committed candidates, 1,872 electrons each, iso-electron
   RAM spread 23%) — the half-node scaling point (predicted ≈1.34× the
   32-rank wall from s = 0.425);
2. **the same two jobs concurrently at 16+16 ranks** on grn061 —
   co-tenant contention at coupling-band size and the measured
   makespan vs the 8,645 s sequential 32-rank baseline from `1928420`;
3. **RAM per process at 16 ranks** — the feasibility arithmetic for
   memory-aware packing (does candidate identity change what co-fits).

Decision rule: if concurrent 16+16 beats sequential 32-rank node-time
by more than the contention it costs (predicted ~5–15% saving for
matched-length pairs), memory-aware co-scheduling has real surface and
comparison No. 2 (see `../paired_comparison_2/`) proceeds as designed. If
contention eats the saving, No. 2's H-gain must come from queue-level
packing across more than two streams, and the design needs n > 2
co-resident jobs.

Inputs are reused from `../memory_band_probe/inputs/` (committed);
pseudos are the GBRV set already staged on granite scratch.

## Collecting results

Requires an authenticated SSH connection to the cluster (CHPC uses Duo
two-factor login).

```
ssh -fNM -o ControlPath=~/.ssh/cm/%r@%h:%p "$CHPC_USERNAME@granite1.chpc.utah.edu"
ssh <cm> 'squeue -j <jobid>'      # jobid in .cofit_jobid
scp <cm>:$SCRATCH/mpt_cofit/results/cofit_results.jsonl cofit_probe/results/
```

Analysis on collection: contention = wall(co16)/wall(solo16) per
candidate; packing saving = 1 − makespan/8,645 s; RAM(16r) vs the
packing headroom on a 380 GB node. Clean up `$SCRATCH/mpt_cofit`.
