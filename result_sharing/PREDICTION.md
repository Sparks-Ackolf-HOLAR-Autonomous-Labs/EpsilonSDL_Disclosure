# Peer exchange of scientific results: registered predictions

Registered 2026-10-12, before `peer_exchange.py` was written or run.

## Why this experiment

Every earlier agreement in this programme had one party owning a resource (computing
node) and the other owning the science. This experiment provides a
result in the disclosure article in which the shared item is a scientific result and every party is a
research group. Here no party sells capacity: N groups screen their own MX2 candidate
lists for the same device goal, and the only thing that may cross between them is what
their calculations found.

## Set-up (fixed before running)

- **Goal.** A compound qualifies for a group when it is on that group's list, its
  measured 1x1 PBE gap is in 1.0 to 2.0 eV, and its chalcogen vacancy hop barrier is at
  least E_min = 1.5 eV (85 C, 10 years; registered rule "mean" of
  `vacancy_barriers/twin_kmc/vacancy_goal.py`). Sensitivity: E_min = 1.7 eV
  (125 C floor).
- **Measured inputs.** Gaps: 1x1 campaign (`dft_campaign/results/outcomes.jsonl`).
  Barriers: 7 DFT NEB values, 23 MACE values plus the measured mean offset, redrawn per
  world with the measured spread. Costs: gap step = mean measured node-hours of F1+F2+F3
  per compound at 3x3 (comparison No. 1); barrier step = measured NEB node-hours (7
  compounds), power law in electron count for the rest; 10 % lognormal run-to-run noise.
- **Groups.** N in {2, 3, 5}; each list has 10 compounds; a common core of
  round(10 o) compounds is on every list and the rest are disjoint; o in {0, 0.25, 0.5,
  1}; infeasible (N, o) pairs skipped. Each group ranks its list by its own prior: its
  own gap estimate (true gap plus N(0, 0.35 eV), drawn per group and world) and the
  uncalibrated barrier prior (MACE plus mean offset, sd 0.52 eV). Equal budgets
  (asymmetric variant: group 1 has twice the budget).
- **Exchange levels.**
  - X0: nothing.
  - X1 record: each finished calculation (compound, gap or barrier value) is published
    to all groups at the end of the round, without saying which group ran it.
  - X2 verdict: only "compound c qualifies / does not", with the compound name.
  - X3 class: pooled pass counts per family (metal group x phase), no compound names;
    each group reweights its prior by a Beta posterior on the family rates.
- **Grading per world** (200 worlds x 30 paired seeds, same lists and noise on both
  sides of each pair): a group gains when its paired win rate (lower spend to its first
  qualifier than under X0) is at least 0.60. Leakage per group, against an attacker who
  pools all other groups and subtracts their own contributions: membership AUC on "c is
  on group i's list" at most 0.60; family-inference advantage (guessing the family most
  represented on group i's list) at most 0.10 over the prior. **All-party win-win**: every
  group gains and every group's leakage limits hold.

## Predictions

| Id | Prediction |
| --- | --- |
| R1 | X1 and X2 give every group a gain (PW >= 0.60) in at least 90 % of worlds when o >= 0.5; the all-group PW rises with o. |
| R2 | At o = 0 (no common compounds) no exchange level gives all groups a gain in more than 20 % of worlds, because barrier follows gap in this family (G3 of the vacancy-goal run). |
| R3 | X1 and X2 breach the membership limit for every group at every N (named results reveal the list). |
| R4 | X3 meets both leakage limits at N >= 3 in at least 80 % of worlds and fails at N = 2 (the peer subtracts its own counts). |
| R5 | With E_min = 1.7 eV, X3 gains more at o = 0 than with E_min = 1.5 eV. |
| R6 | In the asymmetric variant the group with twice the budget gains less than the others under X1 (it gives more results than it receives). |

Consequence registered with the predictions: if R1 and R3 both pass and R4 passes, the
all-party win-win exists only for named-result exchange with no leakage limits, or for
class-pooled exchange among at least three groups whose value is limited by R2. In that
case the four conditions of the disclosure article's proposition do not transfer directly; the
resource conditions N1 and N2 are replaced by "the groups' lists overlap or the second
property does not follow the first" and "at least three contributors per pooled
record".
