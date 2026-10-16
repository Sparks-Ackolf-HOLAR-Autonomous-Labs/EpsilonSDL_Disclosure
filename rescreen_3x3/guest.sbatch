#!/bin/bash
#SBATCH --job-name=mpt_guest
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --time=12:00:00
#SBATCH --requeue
#SBATCH --open-mode=append
#SBATCH --output=guest_%j.log
# Real MX2 screening on a FREE / GUEST CHPC partition.
# --account / --partition / --qos are NOT hard-coded: they are supplied
# by stage_and_submit_guest.sh from the values it verifies live for the
# sparks account (guest QoS on kingspeak/lonepeak/notchpeak), because the
# exact guest triple must be read from `sacctmgr`, never invented.
#
# --requeue + --open-mode=append + the driver's resume logic mean a
# preemption (owner reclaims the node) requeues the job and it continues
# from the last cleanly finished QE stage instead of restarting.
#
# CPU-only pw.x. No allocation is charged on a guest partition.
set -euo pipefail
module load openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3
cd "${MPT_GUEST_ROOT:?set MPT_GUEST_ROOT to the staged rescreen_3x3 dir}"
echo "restart_count=${SLURM_RESTART_COUNT:-0} node=$SLURMD_NODENAME part=$SLURM_JOB_PARTITION"
python3 guest_screen.py
