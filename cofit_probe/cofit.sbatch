#!/bin/bash
#SBATCH --job-name=mpt_cofit
#SBATCH --account=sparks
#SBATCH --partition=sparks-gpu-grn
#SBATCH --qos=sparks-gpu-grn
#SBATCH --nodes=1
#SBATCH --ntasks=64
#SBATCH --time=10:00:00
#SBATCH --output=cofit_%j.log
# Co-scheduling (packing) probe (comparison-No.-2 gate).
# CPU-only pw.x on grn061; the H100 is untouched. Guards:
# MPT_COFIT_NH_CAP=6 per-core nh; --time hard stop.
set -euo pipefail
module load openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3
cd "${MPT_COFIT_ROOT:?set MPT_COFIT_ROOT to the staged probe dir}"
export MPT_COFIT_NH_CAP="${MPT_COFIT_NH_CAP:-6}"
python3 cofit.py
