# 125 C barrier floor (1.70 eV): grading of F1 to F4

CHPC job 16208959 (notchpeak-guest, 12 Oct 2026, about 4 min on 32 cores).
Predictions registered in `PREDICTION.md` before the run. Results:
`../twin_kmc/results/vacancy_goal_{mean,family}_sizebar_emin1.70.json`. Barriers measured
(PBE NEB for 7 compounds, corrected MACE for 23); campaign numbers are simulated units.

| Id | Prediction | Mean rule | Family rule | 1.5 eV run (mean / family) | Verdict |
| --- | --- | --- | --- | --- | --- |
| F1 | at least 2 of 9 window compounds keep the goal | 5 | 6 | 8 / 7 | pass |
| F2 | logbook R2 minus size-law R2 at least 0.10 | +0.126 (0.248 vs 0.122) | +0.153 (0.559 vs 0.407) | +0.100 / +0.0998 | **pass, both rules** |
| F3 | training axis gains at least 0.05 win-win (P2, eps = 0) | +0.005 (tau = 0.1) | +0.010 (tau = 0.2) | +0.005 / +0.010 | fail, as expected |
| F4 | tau slope at most half the eps slope (P4) | 0.005 vs 0.215 | 0.010 vs 0.245 | 0.005 / 0.010 vs 0.24 | pass |

## Reading

- **The stricter floor does what it was proposed for at the level of information.**
  With HfS2 2H, ZrS2 1T and HfS2 1T (and MoTe2 2H under the mean rule) removed, the
  shared record of anneal outcomes explains 0.13 to 0.15 more of the immobility verdict
  than the size law, against a borderline 0.10 at 1.5 eV. The barrier is now a property
  the gap screen does not already imply.
- **It does not change the decision value.** The win-win transect along the training
  axis is identical to the 1.5 eV run to three decimals (0.005 to 0.010 at tau = 0.1 to
  0.2, zero beyond), and the execution axis still carries the gain (CEDT-P4 0.215 to 0.265
  over eps = 0.5 to 1). Identification and membership limits still close the training
  axis near tau = 0.2 (at tau = 0.2: identity accuracy 0.055, membership AUC 0.57, leakage
  pass 0.905; both break by tau = 0.5).
- So the flat training axis is not caused by barrier and gap sharing chemistry alone:
  even when the shared record carries information the group lacks, the leakage price of
  sharing it arrives before its value does. The Janus runs (16208159) test the other
  route, a family where gap and barrier are not aligned.
