#!/bin/bash
# Stage code + inputs to notchpeak scratch and submit the follow-up jobs
# (run from the repo root). Requires an authenticated SSH connection to
# notchpeak (CHPC uses Duo two-factor login), shared through an SSH
# control socket in ~/.ssh/cm/.
set -euo pipefail
S=$(ls ~/.ssh/cm/*notchpeak* | head -1)
M=.
PSL=${PSL_DIR:?directory with the 7 PSL rel UPFs listed in dft_campaign/soc/PSEUDOS.md}
R=/scratch/general/vast/\$USER
ssh -S "$S" x "bash -l -c 'mkdir -p $R/mpt_stackfu/relax/pseudos $R/mpt_stackfu/socph/pseudos $R/mpt_floor125/code'"
for mode in relax socph; do
  tar cf - -C $M/dft_campaign run_campaign.py -C soc soc_campaign.py \
      -C ../../stacking_study run_stacking.py \
      -C followup_2026-10-12 run_followup.py followup.sbatch \
    | ssh -S "$S" x "bash -l -c 'cd $R/mpt_stackfu/$mode && tar xf - && cp $R/mpt_stack/pseudos/*.UPF pseudos/'"
  ssh -S "$S" x "bash -l -c 'cat > $R/mpt_stackfu/$mode/stack_outcomes.jsonl'" \
    < $M/stacking_study/results_2088961/outcomes.jsonl
done
tar cf - -C "$PSL" . | ssh -S "$S" x "bash -l -c 'cd $R/mpt_stackfu/socph/pseudos && tar xf - && sha256sum *rel*.UPF'"
tar cf - -C $M prior_predictive centralization_surface vacancy_barriers \
  | ssh -S "$S" x "bash -l -c 'cd $R/mpt_floor125/code && tar xf -'"
G="-A owner-guest -p notchpeak-guest --qos=notchpeak-guest"
ssh -S "$S" x 'bash -l -s' <<EOS
cd /scratch/general/vast/\$USER/mpt_stackfu/relax && sbatch $G -J stackfu_relax --export=ALL,MODE=relax,MPT_DFT_ROOT=\$PWD followup.sbatch
cd ../socph && sbatch $G -J stackfu_socph --export=ALL,MODE=socph,MPT_DFT_ROOT=\$PWD followup.sbatch
cd ../../mpt_floor125 && cp code/vacancy_barriers/floor_125C/run_floor.sbatch . && sbatch $G --export=ALL,MPT_FLOOR_ROOT=\$PWD run_floor.sbatch
EOS
