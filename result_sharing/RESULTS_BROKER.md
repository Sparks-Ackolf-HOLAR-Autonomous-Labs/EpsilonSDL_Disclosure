# Brokered booking among research groups: results and grading of B1 to B4

Run 2026-10-12 on the DGX: `broker_exchange.py` (all N and o, 200 worlds x 30 paired
seeds, 18 processes, about 25 min) and `broker_decoy.py` (N = 3, o = 0.5 and 1, same
worlds and seeds). Predictions B1 to B3 were committed in `BROKER_PREDICTION.md`
(ad0fdb6) before the broker run, and B4 (607396) before the decoy run. Inputs, groups,
lists, costs, worlds, seeds and grading are those of `peer_exchange.py`; X1c reproduces
its earlier value (all groups gain in 0.335 of worlds at N = 3, o = 1; earlier 0.34).
Campaign numbers are simulated units on measured inputs.

## What the broker does

Before running a gap or barrier calculation a group books it with a neutral broker. The
broker tells that group alone whether the calculation is free (the group runs it), booked
by another group this round (the group skips it and receives the result at the end of the
round) or already computed (the stored result is sent at no cost). Nothing is broadcast,
results reach only groups that hold the compound, and no group learns who computed what.
With decoys (Xb-d), the broker also answers "booked" with probability q when a group books
a calculation that no other group holds (once per group and calculation), so a refusal no
longer proves that someone else holds the compound.

## Grading

| Id | Prediction | Outcome | Verdict |
| --- | --- | --- | --- |
| B1 | at N = 3, o = 1, all groups gain under Xb as often as under X1c (within 0.10 of 0.34) | 0.995 under Xb against 0.335 under X1c | **fail** (the broker does far better) |
| B2 | Xb meets the limits in >= 80 % of worlds at o = 0.25 and 0.5, under 50 % at o = 1 | 0.95 at o = 0.25, 0.04 at o = 0.5, 0 at o = 1 | **fail** (o = 0.5 part) |
| B3 | Xb gives an all-party win-win in >= 10 % of worlds at some N, o | at most 0.03 (N = 5, o = 0.5) | **fail** |
| B4 | decoys give an all-party win-win in >= 10 % of worlds at some q, N = 3, o = 0.5 or 1 | 0.115 at q = 0.3 and 0.26 at q = 0.5 (o = 0.5) | **pass** |

## Numbers (N = 3)

| Level | o | paired win rate per group | all groups gain | qualifiers per group (X0 1.66) | membership AUC | family advantage | limits met | all-party win-win |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| X1c public claims | 0.5 | 0.39-0.48 | 0.01 | 1.90 | 0.85 | 0.31 | 0 | 0 |
| X1c public claims | 1 | 0.55-0.73 | 0.335 | 1.90 | 0.70 | 0.18 | 0 | 0 |
| Xb broker | 0.25 | 0.19 | 0 | 1.78 | 0.54 | -0.18 | 0.95 | 0 |
| Xb broker | 0.5 | 0.46-0.48 | 0.035 | 1.89 | 0.60 | 0.03 | 0.04 | 0 |
| Xb broker | 1 | 0.86-0.90 | 0.995 | 1.90 | 0.70 | 0.18 | 0 | 0 |
| Xb-d, q = 0.1 | 0.5 | 0.49-0.50 | 0.05 | 1.90 | 0.565 | -0.02 | 0.685 | 0.035 |
| Xb-d, q = 0.2 | 0.5 | 0.51-0.53 | 0.075 | 1.89 | 0.537 | -0.05 | 0.795 | 0.06 |
| Xb-d, q = 0.3 | 0.5 | 0.53-0.56 | 0.13 | 1.89 | 0.509 | -0.08 | 0.895 | 0.115 |
| Xb-d, q = 0.5 | 0.5 | 0.58-0.61 | 0.275 | 1.89 | 0.458 | -0.12 | 0.975 | 0.26 |

At o = 1 every list holds the same compounds, so no booking is ever answered with a decoy
and Xb-d equals Xb. With five groups Xb gives an all-party win-win in 0.03 of worlds at
o = 0.5 (limits met in 0.77).

## Diagnostic (`broker_diag.py`, 60 worlds x 30 seeds, N = 3, o = 0.5)

| Level | share of first three own calculations on common compounds | mean spend to first qualifier (nh) | results received per group |
| --- | --- | --- | --- |
| X0 | 0.50 | 2.08 | 0 |
| Xb | 0.34 | 1.54 | 4.17 |
| Xb-d, q = 0.3 | 0.38 | 1.42 | 4.26 |
| Xb-d, q = 0.5 | 0.42 | 1.34 | 4.27 |

## What it means

1. **The broker carries the gain that public claims only hinted at.** With identical lists,
   every group gains in 99.5 % of worlds under the broker against 33.5 % under public
   claims, with the same number of qualifiers found (1.90). The broker does not find more
   compounds; it removes the order effect of public claims (where the group moving second
   lost out) and hands each group the results of the calculations it was spared.
2. **A refusal is itself a disclosure.** Being told "booked" proves that another group
   holds the compound, so with half the list in common the broker's answers reveal the
   overlap (limits met in 4 % of worlds); with identical lists they reveal the whole
   list.
3. **Decoy refusals hide the overlap and add to the gain.** Refusing a fraction q of
   bookings that no one else holds makes a refusal uninformative (membership AUC falls to
   0.46-0.51) and, by deferring a group's private compounds, moves its early calculations
   onto the common part of the list, where the work is divided. Spend to the first
   qualifier falls from 1.54 to 1.34 nh and the all-party win-win reaches 26 % of worlds
   at q = 0.5. This is the first agreement among research groups in this programme under
   which every group gains with every leakage limit met, in a measurable share of worlds.
4. **Scope.** Simulated on measured gaps, barriers and costs; 23 of 30 barriers are
   offset-corrected MACE values; synchronous rounds; one goal. The membership attack
   does not use the attacker's own list as prior knowledge; with identical lists such an
   attacker would know every list in advance, so the o = 1 leakage numbers describe what
   the broker's answers add, not what the attacker could already guess.
