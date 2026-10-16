# Multi-node strong-scaling bench — results (kingspeak `28272521–3`)

Collected 2026-09-11. All three jobs COMPLETED, exit 0 (13–25 min each,
well under the ~1.5 nh/job estimate). Same two fixed problems (TiS2_1T
and MoSe2_2H 3×3 supercells, 6×6×1 k-grid) at 1×16, 2×32, 4×64
nodes×ranks on the kingspeak general allocation.

| problem | 1 node | 2 nodes | 4 nodes | eff(2) | eff(4) |
| --- | ---: | ---: | ---: | ---: | ---: |
| TiS2_1T 3×3 | 383 s | 409 s | 230 s | 0.47 | 0.42 |
| MoSe2_2H 3×3 | 873 s | 1,067 s | 557 s | 0.41 | 0.39 |

(eff(N) = wall(1) / (N × wall(N)), i.e. per-core-hour efficiency at
matched physics.)

## Findings

1. **Two nodes is slower than one in wall time** for both problems
   (409 vs 383 s; 1,067 vs 873 s): at 3×3-supercell size the inter-node
   communication penalty eats the entire rank doubling. Four nodes
   recovers wall speed (1.7× faster than 1 node) but at 4× the core
   cost — ~40% efficiency.
2. **The single-box parallel-efficiency exponent transfers.** s = 0.425
   was fitted on grn061 alone; it predicts eff ≈ 0.44 at 4× the ranks —
   measured 0.39–0.47 across a different cluster and interconnect. The
   twin's parallel-efficiency prior needs no multi-node correction term
   at these sizes.
3. **Policy consequence:** below ~10⁴ electrons, multi-node QE is never
   per-core-cost-effective for this workload — the granite-first,
   single-node-lean recipe is optimal, and the DTDE worst-case
   provisioning question is entirely about *within-node* packing (see
   `../memory_band_probe/results/RESULTS.md`), not node counts.

Scratch (`mpt_multinode`) cleaned after collection.
