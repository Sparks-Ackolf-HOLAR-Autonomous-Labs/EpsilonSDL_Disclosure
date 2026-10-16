# Multi-node strong-scaling bench on kingspeak (future-work item 5)

Submitted 2026-09-10 on the **kingspeak general allocation** (account
sparks, partition kingspeak — a real allocation, not guest; QE 7.4 +
openmpi/5.0.3 + python/3.10.3 verified loading there):

| job | nodes × ranks |
| --- | --- |
| `28272521` | 1 × 16 |
| `28272522` | 2 × 16 |
| `28272523` | 4 × 16 |

Each runs the same two fixed problems (TiS2_1T and MoSe2_2H 3×3
supercells, committed inputs from `scale_validation/inputs/`), so the
inter-node communication penalty is isolated at matched physics. This
supplies the multi-node half of the parallel-efficiency exponent
(s = 0.425 was fitted on the single grn061 box) for the posterior twin.
Cost: ≤ ~1.5 node-hours per job, `--time=06:00:00` hard stop.

## Collecting results

Requires an authenticated SSH connection to the cluster (CHPC uses Duo
two-factor login).

```
ssh -fNM -o ControlPath=~/.ssh/cm/%r@%h:%p "$CHPC_USERNAME@kingspeak.chpc.utah.edu"
ssh <cm> 'cat /scratch/general/vast/$USER/mpt_multinode/results/multinode_results.jsonl'
scp <cm> ...:/scratch/general/vast/$USER/mpt_multinode/results/multinode_results.jsonl multinode_bench/results/
```

Analysis on collection: efficiency(N) = wall(1) / (N * wall(N)) per
problem; fold into the twin's parallel-efficiency prior; note whether
2→4 nodes crosses the communication cliff for these cell sizes. Clean
up `mpt_multinode` scratch after collection.
