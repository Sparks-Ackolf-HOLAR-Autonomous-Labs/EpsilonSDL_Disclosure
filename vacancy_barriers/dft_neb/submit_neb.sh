#!/bin/bash
# Stage and submit the DFT NEB array on the free notchpeak-guest partition.
# Needs an open SSH ControlMaster connection to notchpeak.chpc.utah.edu (CHPC uses Duo two-factor login)
# Guest triple verified 2026-10-09 on notchpeak: account owner-guest, qos notchpeak-guest.
# MPT_NEB_SUBMIT=1 submits; otherwise only sbatch --test-only.
set -euo pipefail
cd "$(dirname "$0")"
SSHOPT="-o ControlPath=$HOME/.ssh/cm/%r@%h:%p"
G="$CHPC_USERNAME@notchpeak.chpc.utah.edu"
R() { ssh $SSHOPT "$G" "bash -l -s" <<<"$*"; }
SCR=$(R 'echo /scratch/general/vast/$USER')
D="$SCR/mpt_neb"
R "mkdir -p $D/inputs $D/results $D/pseudos && cd $D/pseudos && \
 for f in ti_pbe_v1.4.uspp.F.UPF zr_pbe_v1.uspp.F.UPF hf_pbe_v1.uspp.F.UPF \
  mo_pbe_v1.uspp.F.UPF w_pbe_v1.2.uspp.F.UPF s_pbe_v1.4.uspp.F.UPF \
  se_pbe_v1.uspp.F.UPF te_pbe_v1.uspp.F.UPF; do \
  [ -s \$f ] || wget -q https://www.physics.rutgers.edu/gbrv/\$f; done; ls *.UPF | wc -l"
scp -q $SSHOPT run_neb.py neb.sbatch "$G:$D/"
scp -q $SSHOPT inputs/* "$G:$D/inputs/"
ARGS="--account=owner-guest --partition=notchpeak-guest --qos=notchpeak-guest --export=ALL,MPT_NEB_ROOT=$D"
R "cd $D && python3 -m py_compile run_neb.py && echo COMPILE_OK && sbatch --test-only $ARGS neb.sbatch"
if [ "${MPT_NEB_SUBMIT:-0}" = "1" ]; then
  R "cd $D && sbatch $ARGS neb.sbatch" | tee .neb_jobid
  R "squeue -u \$USER -n mpt_neb -o '%.18i %.9P %.2t %.10M %R'"
fi
