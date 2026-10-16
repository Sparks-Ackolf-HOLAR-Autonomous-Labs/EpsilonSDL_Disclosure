# Live MX2 screening on a free / guest CHPC partition

This is the screening run in measured (not simulated) units, moved off the owned granite node onto a **free-of-charge, guest
(preemptible)** partition, where the sparks account pays no allocation
to use other owners' idle CPU nodes.

## What it does (all real Quantum ESPRESSO 7.4)

For each of the 29 CC0 MX2 candidates at 3x3-supercell scale (27-54
atoms, 216-468 electrons):

- runs the full **F1 -> F2 -> F3 ladder** at the CEDT-P4 class-matched
  execution config, producing the real PBE screening gap
  (qualifier = gap in [1.0, 2.0] eV); and
- reruns **F2** (the production-SCF "label" stage) at the DTDE worst-case
  config, so each candidate yields a same-hardware, same-geometry
  **CPU-core-second delta between the no-sharing worst-case config and
  the broker's class-matched config** -- the execution-layer quantity the
  privacy-tax mechanism trades on, now measured on hardware we do not own
  and on a different cluster than granite.

It is **not** a paired campaign verdict. The clean paired CEDT-vs-DTDE
timing comparison stays on the owned node (comparison No. 2).
This run answers a different question: does the real workload -- gaps,
qualifiers, and the config-cost delta -- reproduce on free, preemptible,
non-owned hardware, and what does the guest accounting regime look like.

## Preemption handling

Guest nodes can be reclaimed by their owner at any moment. Two mechanisms
make that a delay, not a data loss:

- `guest.sbatch` sets `--requeue` and `--open-mode=append`; a preempted
  job is requeued automatically.
- `guest_screen.py` **resumes**: every QE stage writes
  `<cand>.<stage>.<config>.out`, and on (re)start any stage whose output
  already shows a clean finish (`JOB DONE` + convergence) is skipped.
- The recorded cost metric is QE's own internal `PWSCF ... CPU` seconds,
  not wall clock, so a requeue's queue-wait does not contaminate the
  config-cost comparison.

## Running it

1. Open an authenticated SSH connection to the cluster (CHPC uses Duo
   two-factor login):
   `ssh -fNM -o ControlPath=~/.ssh/cm/%r@%h:%p "$CHPC_USERNAME@granite1.chpc.utah.edu"`
2. Discover + stage + dry-run:
   `bash stage_and_submit_guest.sh`
   It prints the guest partitions/QoS the account actually has
   (`sacctmgr`/`sinfo`), stages the driver + 29x3 inputs + GBRV
   pseudopotentials to `/scratch/general/vast/$USER/mpt_guest`, and runs
   `sbatch --test-only`.
3. Confirm the printed guest triple, then submit:
   `MPT_GUEST_SUBMIT=1 MPT_GUEST_PART=<part> MPT_GUEST_QOS=<qos> \
      MPT_GUEST_ACCT=<acct> bash stage_and_submit_guest.sh`

Verified guest triple (2026-09-22): `account=sparks partition=granite-guest
qos=granite-guest`. CHPC does **not** run a unified Slurm here -- the
granite login node's scheduler exposes only granite partitions, so
`kingspeak-guest` / `lonepeak-guest` / `notchpeak-guest` (which the
account also holds, per `sacctmgr`) are not submittable from it and would
need a login to those clusters' own schedulers. `granite-guest` is the
free/preemptible partition reachable here: `AllowQos=granite-guest`,
3-day wall, `PreemptMode=CANCEL`, 39 non-owned granite nodes, zero
allocation charge. Because it is a guest partition we are the ones who
get preempted; it never bumps another group's jobs, and running on a
non-owned node (e.g. grn068) leaves our owned grn061 comparison No. 2
untouched.

## Submitted run of record

Job **2048736** on `granite-guest` (node grn068), submitted 2026-09-22,
`--requeue`; scratch `/scratch/general/vast/<uNID>/mpt_guest`.

## Collecting results

`results/progress.json` updates after every candidate; `run_log.jsonl`
records each (re)start with its node and restart count so preemptions are
visible. When done, `results/guest_summary.json` holds the qualifier set
and the per-candidate config-cost ratios; fetching them requires an
authenticated SSH connection to the cluster.

## Rerun and final results (2026-09-30)

Job 2048736 was collected on 2026-09-30. Four F3 band calculations
(TiS2-1T, TiS2-2H, ZrS2-1T, ZrSe2-1T) failed in the Davidson eigensolver
and were rerun with the conjugate-gradient solver in guest job 2087605
(grn021, COMPLETED). `rebuild_summary.py` re-parses all raw outputs into
`results/guest_summary_final.json` and `results/GUEST_RESULTS.md`:
29 of 29 gaps, 3x3 gaps within 0.002 eV of the 1x1 gaps, the same nine
qualifiers, and a median F2 CPU-time ratio (k-pools over no pools) of
0.986. Scratch removed.
