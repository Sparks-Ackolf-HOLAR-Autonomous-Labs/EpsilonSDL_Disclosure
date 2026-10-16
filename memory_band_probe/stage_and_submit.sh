#!/bin/bash
# Stage and submit the memory-band probe (grn061) and the multi-node
# strong-scaling bench (kingspeak general allocation).
#
# Requires an authenticated SSH connection to each cluster (CHPC uses
# Duo two-factor login), opened with:
#   ssh -fNM -o ControlPath=~/.ssh/cm/%r@%h:%p "$CHPC_USERNAME@granite1.chpc.utah.edu"
#   ssh -fNM -o ControlPath=~/.ssh/cm/%r@%h:%p "$CHPC_USERNAME@kingspeak.chpc.utah.edu"
# Never prints credentials.
# Estimated spend: probe 10-20 per-core nh (cap 30, --time 44 h);
# multinode 3x <=1.5 nh on kingspeak general (no preemption of guests).
set -euo pipefail
cd "$(dirname "$0")"
: "${CHPC_USERNAME:?}"
SSHOPT="-o ControlPath=$HOME/.ssh/cm/%r@%h:%p"
G="$CHPC_USERNAME@granite1.chpc.utah.edu"
K="$CHPC_USERNAME@kingspeak.chpc.utah.edu"
RG() { ssh $SSHOPT "$G" "bash -lc '$*'"; }

SCR=$(RG 'echo /scratch/general/vast/$USER')
PROBE="$SCR/mpt_memband"

echo "== occupancy check on grn061 (preemption courtesy) =="
RG 'squeue -p sparks-gpu-grn -o "%.10i %.9P %.14j %.8u %.2t %.10M"' || true

echo "== pseudos =="
RG "mkdir -p $PROBE/pseudos && cd $PROBE/pseudos && \
   for f in ti_pbe_v1.4.uspp.F.UPF mo_pbe_v1.uspp.F.UPF \
            w_pbe_v1.2.uspp.F.UPF s_pbe_v1.4.uspp.F.UPF \
            se_pbe_v1.uspp.F.UPF te_pbe_v1.uspp.F.UPF; do \
     [ -f \$f ] || wget -q https://www.physics.rutgers.edu/gbrv/\$f; \
   done && ls *.UPF | wc -l"

echo "== stage + submit probe on grn061 =="
RG "mkdir -p $PROBE/inputs $PROBE/results"
scp -q $SSHOPT probe.py probe.sbatch "$G:$PROBE/"
scp -q $SSHOPT inputs/*.pw.in "$G:$PROBE/inputs/"
PJ=$(RG "cd $PROBE && sbatch --export=ALL,MPT_PROBE_ROOT=$PROBE probe.sbatch" | grep -o '[0-9]*')
echo "SUBMITTED probe=$PJ"
echo "$PJ" > .probe_jobid

if [ "${SKIP_KINGSPEAK:-0}" = "1" ]; then
  echo "SKIP_KINGSPEAK=1 -> not submitting multinode bench"; exit 0
fi
RK() { ssh $SSHOPT "$K" "bash -lc '$*'"; }
echo "== kingspeak: verify stack, stage, submit 1/2/4-node =="
RK 'module spider quantum-espresso 2>&1 | head -20' || true
KSCR=$(RK 'echo /scratch/general/vast/$USER')
MN="$KSCR/mpt_multinode"
RK "mkdir -p $MN/inputs $MN/results $MN/pseudos"
scp -q $SSHOPT ../multinode_bench/multinode.sbatch "$K:$MN/"
scp -q $SSHOPT ../scale_validation/inputs/TiS2_1T_s3_k6.pw.in \
   ../scale_validation/inputs/MoSe2_2H_s3_k6.pw.in "$K:$MN/inputs/"
RK "cd $MN/pseudos && for f in ti_pbe_v1.4.uspp.F.UPF \
      mo_pbe_v1.uspp.F.UPF s_pbe_v1.4.uspp.F.UPF se_pbe_v1.uspp.F.UPF; do \
      [ -f \$f ] || wget -q https://www.physics.rutgers.edu/gbrv/\$f; done"
for N in 1 2 4; do
  J=$(RK "cd $MN && sbatch -N $N --ntasks-per-node=16 \
       --export=ALL,MPT_MN_ROOT=$MN multinode.sbatch" | grep -o '[0-9]*')
  echo "SUBMITTED multinode N=$N job=$J"
  echo "$J" >> ../multinode_bench/.jobids
done
RK "squeue -u \$USER -o '%.10i %.14j %.2t %.10M %R'"
