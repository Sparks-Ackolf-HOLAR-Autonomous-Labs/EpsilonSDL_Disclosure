#!/bin/bash
#SBATCH --job-name=mpt_guest_f3cg
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --time=06:00:00
#SBATCH --requeue
#SBATCH --open-mode=append
#SBATCH --output=f3cg_%j.log
# Follow-up to guest job 2048736: the F3 band calculation
# for four candidates crashed in the Davidson eigensolver ("problems
# computing cholesky", cdiaghg). This reruns only those four F3 NSCF
# calls with the conjugate-gradient eigensolver, from the converged F2
# charge density already on scratch, at the same execution config as the
# original ladder (32 ranks, 4 pools). Guest partition, no charge.
# Resume-safe: a candidate whose f3cg output already reports JOB DONE is
# skipped on requeue.
set -uo pipefail
module load openmpi/5.0.3 quantum-espresso/7.4
export OMP_NUM_THREADS=1
cd "${MPT_GUEST_ROOT:?}"
echo "restart=${SLURM_RESTART_COUNT:-0} node=$SLURMD_NODENAME part=$SLURM_JOB_PARTITION"
for c in TiS2_1T TiS2_2H ZrS2_1T ZrSe2_1T; do
  wd=work/$c; out=$wd/f3cg.cedt.out
  if [ -f "$out" ] && grep -aq "JOB DONE" "$out"; then echo "$c: resumed"; continue; fi
  t0=$(date +%s)
  ( cd $wd && mpirun -np 32 --bind-to none pw.x -nk 4 \
      -in ../../followup/inputs/$c.f3cg.in > f3cg.cedt.out 2>&1 )
  echo "$c: rc=$? wall=$(( $(date +%s) - t0 ))s done=$(grep -ac 'JOB DONE' $out)"
done
echo FOLLOWUP_DONE
