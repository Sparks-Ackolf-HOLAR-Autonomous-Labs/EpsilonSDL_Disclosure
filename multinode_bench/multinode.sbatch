#!/bin/bash
#SBATCH --job-name=mpt_multinode
#SBATCH --account=sparks
#SBATCH --partition=kingspeak
#SBATCH --time=06:00:00
#SBATCH --output=multinode_%j.log
# Multi-node strong-scaling benchmark (future-work item 5)
# on the kingspeak GENERAL allocation (verified 2026-09-02:
# account sparks holds a general allocation there -- not guest, no
# preemption). Node count is set at submission time:
#   sbatch -N 1 --ntasks-per-node=16 multinode.sbatch
#   sbatch -N 2 --ntasks-per-node=16 multinode.sbatch
#   sbatch -N 4 --ntasks-per-node=16 multinode.sbatch
# Each run executes the same two fixed problems (TiS2_1T and MoSe2_2H
# 3x3 supercells, committed inputs from scale_validation), so the
# inter-node communication penalty is isolated at matched physics.
# Cost guard: 2 problems x <=30 min x <=4 nodes, --time hard stop.
set -euo pipefail
module load openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3 2>/dev/null \
  || module load gcc openmpi quantum-espresso python  # kingspeak stack may differ; verified at submit
cd "${MPT_MN_ROOT:?set MPT_MN_ROOT to the staged multinode dir}"
mkdir -p results
for name in TiS2_1T_s3_k6 MoSe2_2H_s3_k6; do
  wd="work/${name}_N${SLURM_NNODES}"
  mkdir -p "$wd" && cd "$wd"
  ln -sf ../../pseudos pseudos
  t0=$(date +%s)
  mpirun -np "$SLURM_NTASKS" pw.x -nk 2 -in "../../inputs/${name}.pw.in" \
    > run.out 2>&1 || true
  wall=$(( $(date +%s) - t0 ))
  conv=$(grep -c "convergence has been achieved" run.out || true)
  python3 - "$name" "$SLURM_NNODES" "$SLURM_NTASKS" "$wall" "$conv" <<'EOF'
import json, sys
name, nn, nt, wall, conv = sys.argv[1:6]
rec = dict(name=name, nodes=int(nn), ntasks=int(nt), wall_s=int(wall),
           converged=conv != "0")
print(json.dumps(rec))
open("../../results/multinode_results.jsonl", "a").write(
    json.dumps(rec) + "\n")
EOF
  cd ../..
  rm -rf "$wd/out"
done
echo DONE
