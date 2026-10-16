#!/bin/bash
#SBATCH --job-name=mpt_memband
#SBATCH --account=sparks
#SBATCH --partition=sparks-gpu-grn
#SBATCH --qos=sparks-gpu-grn
#SBATCH --nodes=1
#SBATCH --ntasks=64
#SBATCH --time=44:00:00
#SBATCH --output=probe_%j.log
# Memory-band probe (future-work item 4). CPU-only pw.x
# on grn061; the H100 is untouched. Guards: MPT_PROBE_NH_CAP=30
# per-core nh; --time hard stop well under the 20160-min node limit.
set -euo pipefail
module load openmpi/5.0.3 quantum-espresso/7.4 python/3.10.3
cd "${MPT_PROBE_ROOT:?set MPT_PROBE_ROOT to the staged probe dir}"
export MPT_PROBE_NH_CAP="${MPT_PROBE_NH_CAP:-30}"
python3 probe.py
