# Memory-band probe — results (job `1928420`, granite grn061)

Collected 2026-09-11. COMPLETED, exit 0, 25 h 50 m wall, **12.91 per-core
node-hours** (cap was 30). All 14 runs (7 candidate×size points × lean/fast)
converged. Raw data: `probe_results.jsonl` + `probe_1928420.log`; RAM
values below were re-parsed from the raw `run.out` files on scratch because
`probe.py`'s regex only matched "MB" and QE prints large estimates in GB
(regex now fixed in `probe.py`).

## The measured table

| candidate | electrons | lean (nk1) wall | fast (nk4) wall | fast/lean | lean RAM total | fast RAM total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TiS2_1T 5×5 | 600 | 442 s | 817 s | 1.85× | 18.2 GB | 38.2 GB |
| TiS2_1T 6×6 | 864 | 1,200 s | 2,542 s | 2.12× | 30.9 GB | 75.5 GB |
| MoSe2_2H 5×5 | 1,300 | 1,130 s | 2,238 s | 1.98× | 23.3 GB | 67.6 GB |
| WTe2_2H 5×5 | 1,300 | 1,671 s | 2,719 s | 1.63× | 30.8 GB | 65.9 GB |
| MoSe2_2H 6×6 | 1,872 | 3,777 s | 7,180 s | 1.90× | 42.6 GB | 137.2 GB |
| WTe2_2H 6×6 | 1,872 | 4,868 s | 9,615 s | 1.97× | 52.6 GB | 133.4 GB |
| MoSe2_2H 8×8 | 3,328 | 11,767 s | 43,014 s | 3.66× | 112.0 GB | **424.4 GB** |

(32 MPI ranks throughout; "fast" = `-nk 4`. Per-process RAM: lean
0.57–3.5 GB, fast 1.3–13.4 GB.)

## Findings

1. **The registered decision gate passes decisively — spread 63–266% vs the
   ~10% gate.** Config choice at 5×5–8×8 scale is worth 1.6–3.7× of wall
   time. The tradable execution surface that was 4.8% at 3×3 scale is an
   order of magnitude larger here.
2. **But the spread's sign is inverted vs the design assumption: lean
   (nk1) wins everywhere.** The driver is k-point parallelism mismatch:
   these large supercells carry tiny k-grids (2×2×1 → ~2 irreducible
   points; 8×8 is Γ-only), so 4 pools leave 2–4 pools idle — the ~2×
   (k2) and ~4× (k1, partially masked by memory pressure, see 3) ratios
   are exactly the idle-pool arithmetic. Optimal npool is determined by
   the k-grid, which is **class-level information** (the fidelity ladder
   fixes the k-grid) — P4 already discloses it.
3. **The memory wall is ≈4× closer than the electron^0.90 extrapolation
   claimed.** The extrapolation put node-memory pressure at ≈17,600 electrons.
   Measured: the fast config at 3,328 electrons already demands **424 GB
   total against grn061's 380 GB** — the 3.66× slowdown at 8×8 is partly
   memory pressure, not only idle pools. The wall is config-dependent:
   npool multiplies RAM (each pool duplicates wavefunction structures,
   measured factor ≈2.1–3.8× at nk4), so *for k-parallel configs the
   coupling band starts at ≈3,000–3,500 electrons (8×8), and even lean
   crosses 380 GB at roughly 6–7k electrons extrapolated.* The band is
   reachable at ~10–30 per-core nh per campaign, not the multi-day jobs
   the ×1000 extrapolation implied.
4. **The candidate-specific memory signal is real and measured: 23–32%
   iso-electron RAM spread** (WTe2 30.8 vs MoSe2 23.3 GB at 1,300 e;
   52.6 vs 42.6 GB at 1,872 e). Below the wall this spread is
   irrelevant to config choice (lean always wins, feasibility is slack).
   Near the wall — or whenever two jobs must **co-reside on a node**
   (per-core/co-scheduled billing, the billing_regrade prerequisite) —
   it decides what fits, which is exactly the Theorem-3 memory-bit
   regime. This reframes comparison No. 2: the memory bit prices
   *packing*, not npool choice.

## Gate verdict

Formally: **PASS** (≥10% spread by 8×8 → "the band is real and comparison
No. 2 has a genuine shot"). Substantively: the band is real but its
mechanism at this scale is (a) class-level npool matching — which P4
already supports and DTDE's conservative lean config accidentally gets
right, and (b) candidate-level memory-aware packing under co-scheduling —
which is the true per-candidate disclosure surface. Comparison No. 2 must
therefore be designed around co-residency (see
`../cofit_probe/` and `../paired_comparison_2/`), not around npool.
