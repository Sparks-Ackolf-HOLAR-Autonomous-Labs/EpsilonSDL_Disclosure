# Accounting-model re-grade of the live comparison (future-work item 3)

**Question.** The live head-to-head verdict was "sharing bought +0.5%
where +5% was required," and the leading hypothesis was whole-node
billing (freeing cores saves nothing when the node is billed whole).
Does per-core accounting restore the gain?

**Method.** The wire log records ranks and measured wall for each of the
480 real QE calls, so the same physical runs can be re-priced exactly.
Two accountings: `node` (charge = wall × 1 node — what a dedicated
partition like grn061 actually bills) and `percore` (charge = wall ×
ranks/nodecores — shared/co-scheduled, condo fairshare, cloud vCPU).
Same frozen grading as `analyze_live.py`. Script: `regrade_billing.py`;
data: `billing_regrade.json`.

## Result 1 — the published verdict was *already* per-core

The recorded campaign node-hours match `wall × ranks / 64` to 7×10⁻⁵ —
the campaign driver charged per-core all along. So the published +0.5%
(labels ratio 1.005, PW 6/10) **is** the per-core number, and the
"whole-node billing explains it" hypothesis in
`paired_comparison_1/RESULTS.md` is wrong as an explanation of the recorded
grading. This supersedes that paragraph.

| accounting | PW (R metric) | labels/charge ratio (H, needs ≥ 1.05) | verdict |
| --- | --- | --- | --- |
| whole-node (what granite bills) | **0/10** — DTDE wins every pair | 0.909 (−9%) | sharing strictly *loses* |
| per-core (as recorded) | 6/10 (p = 0.38) | 1.005 (+0.5%) | parity |

Under true whole-node accounting CEDT-P4 is strictly worse: right-sizing
F1 to 16 ranks lengthens wall (89.6 s vs 56.5 s) with no billing offset,
and its F3 pooling choice adds wall too. Per-core billing is therefore
**necessary** for the mechanism — but at this scale it is not sufficient.

## Result 2 — where the per-core gain actually went

Mean measured wall by class and config:

| class | DTDE (32 ranks, nk1) | CEDT rate card | per-core effect |
| --- | ---: | ---: | --- |
| F1 | 56.5 s | 89.6 s @ 16 ranks | −21% charge (parallel efficiency ≈ 0.63) |
| F2 | 143.1 s | 139.2 s @ 32 ranks, nk2 | −3% |
| F3 | 225.0 s | 238.4 s @ 32 ranks, nk4 | **+6% — the rate card's nk4 was mis-tuned** |

F3 is 53–56% of all charge, so the mis-tuned F3 entry cancelled the F1
saving almost exactly — hence +0.5% net.

## Result 3 — the oracle ceiling at this scale is 4.8%, below the 5% margin

Re-pricing the DTDE workload with the best observed config per **class**
(fixable with P4-level information only): **−3.7%**. With the best config
per **candidate × class** (requires per-candidate disclosure): **−4.8%**.
The measured value of candidate-specific information at 3×3-supercell
scale is therefore **1.1% of spend** — and even a perfect broker with
perfect disclosure cannot reach the 1.05× H margin here.

## Conclusions

1. The vanished live gain was *not* an accounting artifact: the grading
   was already per-core. Two real causes: a mis-tuned rate-card entry
   (F3 nk4, −6% on half the spend — fixable) and an intrinsically small
   config spread at this task scale (oracle ceiling 4.8% — not fixable
   by any contract).
2. Whole-node/dedicated-partition billing kills the mechanism outright;
   any live follow-up must run under per-core or co-scheduled
   accounting, or the H-side gain cannot exist even in principle.
3. The path to a measurable positive: move to the scale where the config
   spread itself grows (memory-band jobs, `coupling_onset/`), fix the
   rate card empirically (a 20-job calibration would have caught nk4),
   and grade under per-core accounting. See `../memory_band_probe/`.
