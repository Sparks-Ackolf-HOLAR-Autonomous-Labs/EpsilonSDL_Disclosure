# Changing the screening goal so that a shared logbook can carry property information

Prepared 2026-10-10, before any DFT NEB barrier exists (array 16179771, 7 tasks,
started on notchpeak-guest about 23:35 UTC 10 Oct). Nothing in this note has been
run; it fixes the goal, the threshold and the predictions so that the twin run after
the DFT barriers arrive is a test, not a fit.

## Why the training axis has been flat

In every test so far the target was a PBE gap window (1.0 to 2.0 eV). The quantity a
shared performance logbook records is job cost. Cost decides how much a step costs,
not which compound qualifies, so the logbook can only reorder jobs of equal promise.
The kMC rung (`RESULTS_KMC_RUNG.md`) confirmed this: the logbook explains the kMC cost
well (R^2 0.94) and still adds at most 1.5 % throughput.

## Proposed goal

A compound qualifies when it is in the 1.0 to 2.0 eV window **and** its chalcogen
vacancies are immobile at device operating temperature. "Immobile" means the
single-vacancy hop rate, nu exp(-E_hop / kT) with attempt frequency nu = 1e13 s^-1,
is below one hop per service life. This gives a threshold barrier

E_min = kT ln(nu t_life)

| operating condition | service life | E_min (eV) |
| --- | --- | ---: |
| 85 C (consumer electronics) | 1 year | 1.46 |
| 85 C | 10 years | 1.53 |
| 125 C (automotive grade) | 1 year | 1.62 |
| 125 C | 10 years | 1.70 |

Proposed default: 85 C, 10 years, E_min = 1.5 eV (rounded). It is a cold-start
choice and can be moved; the predictions below are stated for this value.

With this goal the vacancy barrier is both part of the target and the main cost of
the kMC step, so a shared barrier logbook records information about qualification,
not only about cost. That is the first setting in which the theory predicts a slope
along the training axis.

## What the MACE barriers already show

MACE-MP-0 barriers (`results/vacancy_neb.jsonl`, 4x4 cells) run from 0 to 1.01 eV.
None reaches 1.5 eV, so with MACE barriers the new goal has **no qualifiers at all**;
the goal can only be evaluated on DFT barriers. The literature PBE value for MoS2 2H
is about 2.3 eV (Komsa et al. 2012) against 0.90 eV from MACE, so MACE underestimates
by more than 1 eV there (registered as N1 and N2 in `dft_neb/PREDICTION.md`).

The six highest MACE barriers (WSe2, WS2, MoSe2, MoS2 2H; HfS2 1T; WTe2 2H) are all
in the gap window. Barrier and gap therefore share chemistry: group-6 2H sulfides and
selenides are high on both. This matters for the test, because a logbook that only
repeats what the gap already says would again add nothing.

## Registered predictions for the twin run (P-2026-10-10-G)

Run after `analyze_neb.py` grades N1 to N5; barriers for the 23 compounds without a
DFT NEB are the MACE values shifted by the measured mean DFT correction, as in the
decision rule of `dft_neb/PREDICTION.md`.

| Id | Prediction | Pass condition |
| --- | --- | --- |
| G1 | The new goal is not empty | at least 2 of the 9 window compounds reach E_hop >= 1.5 eV after the DFT correction |
| G2 | The logbook carries property information | at P2, R^2 of the class-keyed logbook for "immobile or not" exceeds R^2 of R's own size law by >= 0.10 |
| G3 | The training axis gains a slope | at P2 and eps = 0, win-win rises by >= 0.05 from tau = 0 to the best tau within the leakage limits |
| G4 | The overlap with the gap limits the slope | the slope in G3 is at most half of the slope along eps at P4 |

If G1 fails, the goal is empty at this threshold and the run is not made; the
threshold table above gives the alternatives. If G2 fails, the flat training axis is a
property of this compound family (barrier follows gap), not of the goal.

## Twin change needed (not yet written)

`twin_kmc/kmc_rung.py` already makes the kMC step cost depend on the barrier and keys
P2 classes on the barrier bit. Two more changes are needed: (1) qualification at F4
also requires E_hop >= E_min, revealed when the kMC step completes; (2) in the
training channel, R's value for a compound is multiplied by the class pass rate seen
in the shared logbook (prior 0.5 when the class has no record). Estimated run time on
the DGX: minutes.
