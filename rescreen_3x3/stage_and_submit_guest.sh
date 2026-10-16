#!/bin/bash
# Stage and submit the real MX2 screening on a FREE / GUEST CHPC
# partition. Free of charge: guest QoS runs preemptibly on
# other owners' idle nodes and charges no allocation.
#
# Requires an authenticated SSH connection to the cluster (CHPC uses
# Duo two-factor login), opened with:
#   ssh -fNM -o ControlPath=~/.ssh/cm/%r@%h:%p "$CHPC_USERNAME@granite1.chpc.utah.edu"
# NOTE (verified 2026-09-22): CHPC does NOT run a unified Slurm here --
# the granite login node's scheduler only exposes granite partitions, so
# kingspeak/lonepeak/notchpeak-guest are NOT submittable from it (they
# live on those clusters' own schedulers). The free/guest partition
# reachable here is `granite-guest` (AllowQos=granite-guest, 3-day wall,
# PreemptMode=CANCEL, 39 non-owned granite nodes, zero allocation charge)
# -- that is the verified default below. The guest triple is still
# DISCOVERED live and echoed so it can be re-confirmed. Never prints
# credentials.
set -euo pipefail
cd "$(dirname "$0")"
: "${CHPC_USERNAME:?}"
SSHOPT="-o ControlPath=$HOME/.ssh/cm/%r@%h:%p"
G="$CHPC_USERNAME@granite1.chpc.utah.edu"
R() { ssh $SSHOPT "$G" "bash -lc '$*'"; }

SCR=$(R 'echo /scratch/general/vast/$USER')
LG="$SCR/mpt_guest"

echo "== discover guest partitions/qos available to this account =="
R 'sacctmgr -n show assoc user=$USER format=account%20,qos%60' || true
echo "-- guest partitions in this Slurm --"
R 'sinfo -o "%P %a %.11l %.6D %T" | grep -i guest' || true

# submission triple (verified 2026-09-22 on the granite scheduler).
# Override by exporting before running this script.
GPART="${MPT_GUEST_PART:-granite-guest}"
GACCT="${MPT_GUEST_ACCT:-sparks}"
GQOS="${MPT_GUEST_QOS:-granite-guest}"
echo "== will submit to partition=$GPART account=$GACCT qos=$GQOS =="

echo "== pseudos (GBRV PBE USPP; shared vast scratch, reused if present) =="
R "mkdir -p $LG/pseudos && cd $LG/pseudos && \
   for f in ti_pbe_v1.4.uspp.F.UPF zr_pbe_v1.uspp.F.UPF \
            hf_pbe_v1.uspp.F.UPF mo_pbe_v1.uspp.F.UPF \
            w_pbe_v1.2.uspp.F.UPF s_pbe_v1.4.uspp.F.UPF \
            se_pbe_v1.uspp.F.UPF te_pbe_v1.uspp.F.UPF; do \
     [ -f \$f ] || wget -q https://www.physics.rutgers.edu/gbrv/\$f; \
   done && echo pseudos=\$(ls *.UPF | wc -l)"

echo "== stage driver + inputs =="
R "mkdir -p $LG/inputs $LG/results"
scp -q $SSHOPT ../qe_retry.py guest_screen.py guest.sbatch "$G:$LG/"
scp -q $SSHOPT inputs/*.in inputs/manifest.json "$G:$LG/inputs/"
R "cd $LG && python3 -m py_compile guest_screen.py && echo COMPILE_OK" \
  || { echo "remote compile failed"; exit 1; }

echo "== dry-run sbatch (--test-only) =="
R "cd $LG && sbatch --test-only --account=$GACCT --partition=$GPART \
     --qos=$GQOS --export=ALL,MPT_GUEST_ROOT=$LG guest.sbatch" || \
  echo "(test-only rejected -- confirm the guest triple from the output above)"

if [ "${MPT_GUEST_SUBMIT:-0}" = "1" ]; then
  echo "== submit (free/guest, --requeue) =="
  JID=$(R "cd $LG && sbatch --account=$GACCT --partition=$GPART \
        --qos=$GQOS --export=ALL,MPT_GUEST_ROOT=$LG guest.sbatch" \
        | grep -o '[0-9]*')
  echo "SUBMITTED guest job=$JID part=$GPART"
  echo "$JID $GPART" > .guest_jobid
  R "squeue -u \$USER -o '%.12i %.14j %.12P %.2t %.10M %R'"
else
  echo "== NOT submitted: set MPT_GUEST_SUBMIT=1 to launch after the =="
  echo "== guest triple is confirmed against the sinfo/sacctmgr output =="
fi
