#!/bin/bash -l
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --requeue
#SBATCH --output=followup_%x_%j.log
# Corrected 2H cells follow-up. MODE = relax | socph.
# CPU-only QE 7.4; account/partition/qos given at submission (notchpeak-guest).
set -euo pipefail
module load openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3
export OMP_NUM_THREADS=1 MPT_NPROC_PER_RUN=16 MPT_NPOOL=4 MPT_WORKERS=2
export MPT_NODE_HOUR_CAP=4
export MPT_SOC_ROOT="${MPT_DFT_ROOT:?}"
export MPT_STACK_OUTCOMES="$MPT_DFT_ROOT/stack_outcomes.jsonl"
cd "$MPT_DFT_ROOT"
python3 run_followup.py "${MODE:?}"
mkdir -p "$HOME/mpt_stackfu_results/$MODE"
cp -r results "$HOME/mpt_stackfu_results/$MODE/results_$SLURM_JOB_ID"
