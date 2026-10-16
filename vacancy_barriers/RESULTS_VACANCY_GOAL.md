# Vacancy-immobility goal with DFT barriers: grading of G1 to G4

Run 2026-10-12 on the DGX, after the DFT NEB array (16179771) passed N1 to N5. Goal,
threshold and predictions were registered on 10 Oct in `GOAL_CHANGE.md` before any DFT
barrier existed. Code: `twin_kmc/vacancy_goal.py`; twin hooks `surface.IMMOBILE_FN` and
`surface.PASSRATE_TRAIN` (both off by default, so all earlier results are unchanged;
`validate_continuity.py` corners still exact). Results: `twin_kmc/results/vacancy_goal_*.json`.
Barriers are measured (PBE NEB for 7 compounds, MACE plus measured offset for 23);
campaign numbers are simulated units.

## Set-up

- **Goal.** A compound qualifies when it is in the 1.0 to 2.0 eV PBE gap window, passes
  the Gamma-phonon check, and its chalcogen vacancy hop barrier is at least 1.5 eV
  (85 C, 10 years). The barrier verdict reaches the materials group at F4.
- **Barriers.** Registered rule ("mean"): MACE value plus the mean of the 7 measured
  DFT minus MACE offsets (+0.86 eV); world-to-world spread 0.52 eV (sd of the offsets) for
  the 23 corrected compounds, 0.10 eV for the 7 with a DFT NEB. Sensitivity ("family"):
  offset per metal group and phase where two or more compounds were measured (group-6 2H
  +1.45 eV, group-4 1T +0.46 eV), the mean rule elsewhere.
- **Shared logbook.** At P2 the logbook is keyed by size bin x barrier bit (the group's
  own MACE barrier above or below the median; MACE ranks barriers well, Spearman 0.64,
  but sits 0.4 to 1.6 eV low, so the group cannot calibrate it alone). It records the
  immobility outcome of each completed anneal step (F3) per class, and the group weights
  a compound's value by the class pass rate in proportion to tau. A second class
  definition (barrier bit alone) is reported as a check.
- 200 worlds x 30 paired seeds; P2 transects in tau at eps = 0 and 1, P4 transect in eps.

## Grading

| Id | Prediction | Registered rule (mean) | Family offsets | Verdict |
| --- | --- | --- | --- | --- |
| G1 | goal not empty: at least 2 of the 9 window compounds reach 1.5 eV | 8 of 9 (HfS₂ 1T short at 1.36 eV, measured) | 7 of 9 (ZrS₂ 1T also short) | **pass** |
| G2 | logbook R² for "immobile or not" exceeds the size law by at least 0.10 | 0.212 vs 0.111, +0.100 | 0.479 vs 0.379, +0.0998 | **at the threshold** (pass by 0.0004 under the registered rule, fail by 0.0002 under the family rule) |
| G3 | training axis gains at least 0.05 in win-win (P2, eps = 0) | +0.005 (at tau = 0.1) | +0.010 (at tau = 0.2) | **fail** |
| G4 | the tau slope is at most half the eps slope at P4 | 0.005 vs 0.24 | 0.010 vs 0.245 | pass (trivially, since G3 is near zero) |

With the barrier bit alone as the class key, G2 fails outright (logbook R² 0.09 and
0.05, below the size law) and G3 is exactly zero.

## Why the training axis is still flat

1. **Barrier follows gap in this compound family.** Across the prior worlds, 77 % (mean
   rule) to 82 % (family rule) of the gap-window compounds are immobile, against 33 to
   39 % outside the window. The new requirement removes only 16 to 24 % of the
   qualifiers, and mostly where the gap already said "unlikely". The group-6 2H
   sulfides and selenides are high on both counts.
2. **The pass-rate term barely moves the choices.** With and without the pass-rate
   term the P2 transects agree within 0.02 on every component (win rate 0.39 to 0.40,
   discovery rate 0.87). The logbook knows which classes pass, but the gap prior has
   already pointed the group at those classes.
3. **Leakage closes the axis at tau of about 0.2.** As before, the size x barrier-bit
   logbook breaks the identification limit by tau = 0.5 (accuracy 0.088, then 0.143 at
   tau = 1; limit 0.083) and the membership limit by tau = 0.2 to 0.5 (AUC 0.57 to
   0.85; limit 0.60). The only tau points with any win-win (0.005 to 0.01) sit below 0.2.
4. **The execution axis is unaffected.** CEDT-P4 reaches win-win 0.27 at eps = 0.5 and
   0.24 at eps = 1 under the new goal (gap goal on the same cards: 0.21 to 0.26).

By the rule registered in `GOAL_CHANGE.md`, a failing (here borderline) G2 means the flat
training axis is a property of this compound family, where barrier and gap share
chemistry, not of the goal itself.

## Reading for materials work

Requiring immobile vacancies is a sound device criterion, and the DFT barriers show it
is satisfiable: seven or eight of the nine window compounds meet a 10-year, 85 C floor.
For the information question, however, the requirement adds little: in the group-4 and
group-6 dichalcogenides the compounds with the right gap are mostly the ones with high
vacancy barriers, so a shared record of anneal outcomes tells the materials group what
its gap screen already implies. A shared logbook should pay where the second property
is uncorrelated with, or opposed to, the first. Two candidates within this programme:
(a) a stricter floor (125 C, 10 years, 1.70 eV), which removes the window compounds
whose barriers sit between 1.5 and 1.7 eV (HfS₂ 2H, ZrS₂ 1T, and under the mean rule
MoTe₂ 2H and WTe₂ 2H) and so makes the barrier decision-relevant; (b) a compound family where gap and barrier are not aligned (for
example Janus MXY layers or alloyed chalcogenides). Both are low-cost twin
reruns; (b) also needs new NEB calculations.

## Limits

- 23 of 30 barriers are corrected MACE values; the measured offsets split by family
  (+0.45 for group-4 1T, +1.2 to +1.65 for group-6), so the registered mean rule
  overstates barriers of group-4 1T compounds. The family rule is the better estimate;
  both rules give the same verdicts except the knife-edge G2.
- The logbook learns only from in-campaign anneal steps (one research party). With N
  parties pooling records the pass rate would converge faster; the leakage crowding
  measured in the multi-party study would act against it.
- The kMC cost factor uses the MACE kMC cost shifted to the DFT barrier at 1000 K and is
  clipped to one decade; earlier runs showed the clip does not change the tau result.
