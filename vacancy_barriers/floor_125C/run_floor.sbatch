#!/bin/bash -l
#SBATCH --job-name=mpt_floor125
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --mem=48G
#SBATCH --time=6:00:00
#SBATCH --requeue
#SBATCH --output=floor_%j.log
# 125 C vacancy-barrier floor (1.70 eV) twin rerun.
# Code staged to $MPT_FLOOR_ROOT/code (prior_predictive, centralization_surface,
# vacancy_barriers); both offset rules run side by side, 16 processes each.
set -euo pipefail
module load python/3.10.3
cd "${MPT_FLOOR_ROOT:?}/code/vacancy_barriers/twin_kmc"
python3 vacancy_goal.py --rule mean   --e-min 1.70 --worlds 200 --npts 11 --procs 16 > ../../../mean.log 2>&1 &
python3 vacancy_goal.py --rule family --e-min 1.70 --worlds 200 --npts 11 --procs 16 > ../../../family.log 2>&1 &
wait
mkdir -p "$HOME/mpt_floor125_results"
cp results/vacancy_goal_*_emin1.70.json ../../../*.log "$HOME/mpt_floor125_results/"
echo FLOOR DONE
