# 125 C barrier floor (1.70 eV): registered predictions

Registered 2026-10-12, before the run. The 125 C barrier floor (1.70 eV) was set aside
when the Janus family was chosen and is tested here. Option (a) of `../RESULTS_VACANCY_GOAL.md`, "Reading for materials work".

## What changes

Only the floor. The vacancy-immobility goal of `../GOAL_CHANGE.md` is rerun with
E_min = 1.70 eV (125 C, 10 years) instead of 1.5 eV (85 C, 10 years). Barriers, offset
rules, classes, worlds (200 x 30 paired seeds), transects and code are the same as the
1.5 eV run (`../twin_kmc/vacancy_goal.py --e-min 1.70`, both offset rules, size x barrier
bit classes). Campaign numbers are simulated units; barriers are the measured PBE NEB
values (7 compounds) and corrected MACE values (23).

## Known before the run (deterministic, from the point barriers)

Window compounds that keep the goal at 1.70 eV: mean rule 5 of 9 (WS2 2H, MoS2 2H,
WSe2 2H, MoSe2 2H, WTe2 2H); family rule 6 of 9 (adds MoTe2 2H). HfS2 2H (1.51 eV),
ZrS2 1T and HfS2 1T drop out under both rules. So the stricter floor removes three or
four of the nine gap-window compounds, against one or two at 1.5 eV.

## Predictions

| Id | Prediction | Threshold (same as at 1.5 eV) | Expectation |
| --- | --- | --- | --- |
| F1 | goal not empty | at least 2 of the 9 window compounds reach 1.70 eV | pass (known: 5 and 6) |
| F2 | the shared record of anneal outcomes now carries information the size law does not | logbook R2 minus size-law R2 at least 0.10, both rules | pass under both rules (at 1.5 eV it sat at +0.100 / +0.0998) |
| F3 | the training axis gains win-win | rise of at least 0.05 at P2, eps = 0 | fail: leakage still closes the axis near tau = 0.2 |
| F4 | tau slope at most half the eps slope at P4 | as at 1.5 eV | pass |

F2 is the test the floor was proposed for: a barrier criterion that no longer follows the
gap should make a shared anneal record decision-relevant. F3 is expected to fail for the
reason measured at 1.5 eV (identification and membership limits break by tau = 0.2 to
0.5), so a pass would be the surprise.

Run: `run_floor.sbatch` on CHPC notchpeak-guest (CPU only, about 30 min).
Collect: `collect_floor.sh`.
