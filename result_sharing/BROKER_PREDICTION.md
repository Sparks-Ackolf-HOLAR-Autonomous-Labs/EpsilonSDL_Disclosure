# Brokered booking among research groups: registered predictions

Registered 2026-10-12, before `broker_exchange.py` was run. Follows the failed R1 of
`PREDICTION.md` (no registered exchange of results gave every group a gain) and the
exploratory claim level X1c, which showed that the gain comes from dividing the next
calculations, but whose public claims revealed each group's list (membership AUC 0.68 to
0.72, limit 0.60).

## Level Xb: a neutral booking broker

Same groups, lists, goal, costs, budgets, worlds and seeds as `peer_exchange.py`.
Before a group starts a calculation (compound c, gap step or barrier step) it books it
with a broker, who answers only that group:

- "free": the group runs the calculation; the broker holds the result.
- "booked this round by another group": the group skips c this round and the broker
  sends it the result at the end of the round.
- "already computed": the broker sends the stored result at no cost.

Nothing is broadcast. A group only ever learns about compounds on its own list, and never
which group computed a result. The attacker pools the other groups and records each
compound for which one of them received a booking refusal or a stored result coming from
group i.

## Predictions

| Id | Prediction | Pass condition |
| --- | --- | --- |
| B1 | Dividing the work, not broadcasting results, carries the gain | at N = 3, o = 1, the share of worlds in which every group gains under Xb is within 0.10 of X1c (0.34) |
| B2 | The broker hides lists when they overlap partly | at N = 3, Xb meets both leakage limits for every group in at least 80 % of worlds at o = 0.25 and 0.5, and in under 50 % at o = 1 |
| B3 | An all-party win-win exists among research groups | at some N and o the all-party win-win (every group gains and every limit holds) occurs in at least 10 % of worlds under Xb |

If B3 passes, the disclosure article states the condition under which exchange among research groups is
a win-win (a broker that divides the work), in place of the statement that no exchange
is one. If B3 fails, the statement stands and Xb is reported as the closest agreement.

## Addendum, registered 2026-10-12 before the decoy run (B4)

A first look at the Xb run (N = 2, o = 0.5 and 1) showed booking refusals revealing the
overlap of lists (membership AUC 0.63 and 0.80). Level Xb-d adds decoy refusals: when a
group books a calculation that no other group holds, the broker answers "booked" with
probability q, once per group and calculation; the group skips it that round and may
book it in a later round (nothing is delivered). An attacker cannot tell a decoy from a
real refusal.

| Id | Prediction | Pass condition |
| --- | --- | --- |
| B4 | Decoy refusals open an all-party win-win | for some q in {0.1, 0.2, 0.3, 0.5}, at N = 3 and o = 0.5 or 1, the all-party win-win occurs in at least 10 % of worlds |
