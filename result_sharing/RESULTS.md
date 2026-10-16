# Peer exchange of scientific results: results and grading of R1 to R6

Run 2026-10-12 on the DGX (`peer_exchange.py`, 200 worlds x 30 paired seeds per
configuration, 16 processes, 7 min). Predictions were registered in `PREDICTION.md` and
committed (67c6657) before the simulator existed. Results: `results/peer_exchange.json`.
Gaps, barriers and per-step costs are measured (1x1 PBE gaps; 7 DFT NEB barriers and 23
offset-corrected MACE barriers; gap-step node-hours from comparison No. 1 at 3x3; NEB
node-hours from array 16179771). Campaign numbers are simulated units.

## Set-up in one paragraph

Two, three or five research groups screen their own 10-compound lists of MX2 layers for
the same device goal: a PBE gap in 1.0 to 2.0 eV and a chalcogen vacancy barrier of at
least 1.5 eV (85 C, 10 years). No group owns anything the others need; each spends its
own 6 node-hours on two kinds of calculation, a gap calculation (0.02 to 0.12 nh) and a
vacancy-barrier NEB (1.0 to 2.2 nh). Lists share a common core of 10 o compounds
(o = 0, 0.25, 0.5, 1). The groups may exchange: nothing (X0); unattributed records of
each finished calculation with the compound named (X1); only the final verdict per
named compound (X2); or pooled pass counts per family (metal group x phase), with no
compound named (X3). A group gains when, over 30 paired seeds in a world, it reaches its
first qualifying compound at lower spend than under X0 in at least 60 % of the pairs.
Leakage is graded against an attacker that pools all other groups (registered) and,
as a check, a single peer: membership AUC <= 0.60 and family-inference advantage <= 0.10.

## Grading

| Id | Prediction | Outcome | Verdict |
| --- | --- | --- | --- |
| R1 | X1/X2 give every group a gain in >= 90 % of worlds at o >= 0.5 | no group gains in any world; mean paired win rate 0.11 to 0.18 | **fail** |
| R2 | at o = 0 no level gives all groups a gain in > 20 % of worlds | 0 % at every level, N = 2 and 3 | pass |
| R3 | X1/X2 breach the membership limit for every group at every N | pooled attacker AUC 0.74 to 0.91 everywhere (limit 0.60) | pass |
| R4 | X3 meets the limits at N >= 3 in >= 80 % of worlds, fails at N = 2 | 87 to 98 % at N >= 3, but also 93 to 96 % at N = 2 | **partial** (second half fails) |
| R5 | X3 gains more at o = 0 with E_min = 1.7 eV than 1.5 eV | mean paired win rate 0.07 vs 0.06 | **fail** |
| R6 | under X1, the group with twice the budget gains less | equal paired win rates (0.15); on qualifiers found, the large group gains nothing (1.92 to 1.92) while the others gain 1.65 to 1.82 | **fail on the registered metric**, supported on qualifiers |

All-party win-win (every group gains and every leakage limit holds): **0 % of worlds
for every registered level at every N and o.** The registered consequence therefore does
not hold as written: no exchange level gives an all-party gain even without leakage
limits.

## What happened (main configuration N = 3)

| Level | o | mean paired win rate | qualifiers per group (X0: 1.66) | membership AUC (pooled) | leakage limits met |
| --- | --- | --- | --- | --- | --- |
| X1 record | 0.5 | 0.15 | 1.81 | 0.86 | 0 % |
| X1 record | 1.0 | 0.14 | 1.67 | 0.78 | 0 % |
| X2 verdict | 0.5 | 0.12 | 1.85 | 0.85 | 0 % |
| X2 verdict | 1.0 | 0.12 | 1.81 | 0.78 | 0 % |
| X3 family counts | 0.5 | 0.05 | 1.68 | 0.53 | 90 % |
| X3 family counts | 1.0 | 0.02 | 1.66 | 0.53 | 98 % |
| X1c record + claim (post hoc) | 1.0 | 0.66 | 1.90 | 0.70 | 0 % |

1. **The first qualifier comes too early for exchange to change it.** A group's own gap
   estimate points it at a window compound in its first or second step, and 77 % of
   window compounds pass the barrier floor (barrier follows gap in this family). The
   first qualifier usually arrives with the group's first NEB, before any other group's
   result has been published.
2. **Shared values make peers duplicate work.** With overlapping lists, groups receiving
   each other's gaps converge on the same most promising compound and run the same NEB
   in the same round. Named records (X1) at full overlap add only 0.02 qualifiers per
   group, less than verdicts alone (X2, +0.16), because the gap values synchronize the
   next choice. The exchanged result helps only if the groups also divide the next
   calculations among themselves.
3. **Dividing the work is what pays, and it requires naming compounds.** A post hoc
   variant, added after the registered run and labelled exploratory (X1c), lets each
   group claim the compound it is about to run, so later movers in the round skip it.
   At full overlap it raises every group's paired win rate to 0.55 to 0.73 and the
   qualifiers per group to 1.90 (+15 %); every group gains together in 34 % of worlds
   (N = 3) and 34 % (N = 5). At o = 0 it changes nothing, because there is nothing to
   divide. The gain is uneven: the group that moves second in each round's order gains
   least (0.55), a fairness term the agreement would have to settle.
4. **Naming compounds reveals the list; pooling hides it but carries nothing.** Every
   named exchange (X1, X2, X1c) breaches the membership limit (AUC 0.68 to 0.91) and the
   family limit (advantage 0.14 to 0.40). Family counts (X3) meet both limits in 87 to
   98 % of worlds, even between two groups (the subtracted counts identify the family a
   peer tested, not its compounds), but they give no gain because the family pass rates
   only repeat what the gap screen already implies. A stricter 125 C floor (1.7 eV) does
   not change this.

## Reading for the disclosure article

With no resource owner, the conditions N1 (compound-specific demand on a capacity) and
N2 (charging for reserved capacity) have no object; what replaces them, in this
family, is (a) overlapping targets, (b) a division of the next calculations, which is a
disclosure of plans, and (c) result content that the receiver's own screen does not
already imply. N3 (masking) and N4 (paired grading) carry over: the claim and the
record name the compound, as completion times did. In MX2 screening for a 1.0 to 2.0 eV
gap and a vacancy-barrier floor, (c) fails for anonymised content and the named
exchanges that work breach the leakage limits, so no exchange gives an all-party
win-win. A family in which the second property does not follow the first (for example
Janus MXY layers) is where pooled results could carry value; that needs new NEB
calculations.

## Limits

- Lists are fixed per group; groups do not adapt their lists to what others publish.
- Rounds are synchronous; with staggered starts some duplication would disappear
  without claims. The claim order alternates each round, and the middle group of three
  still gains least.
- 23 of 30 barriers are corrected MACE values (registered "mean" rule; the "family"
  rule gives the same verdicts).
- X1c was added after the registered run; its numbers are exploratory.
