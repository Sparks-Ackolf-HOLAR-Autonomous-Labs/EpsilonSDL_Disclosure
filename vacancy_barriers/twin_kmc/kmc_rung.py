#!/usr/bin/env python3
"""kMC rung in the twin and the training-axis transects (provisional).

Change to the twin (applied by patching simulator.py functions at import, nothing else
edited):
  * the F3 rung becomes "F3 plus a vacancy-anneal kMC run": its cost per candidate is the
    base F3 cost times a compound factor k_c = 10^clip(z_c, -CLIP, CLIP), where z_c is the
    measured log10 kMC cost (L = 48 lattice, MACE barriers, results/kmc_runs.jsonl) of
    that compound minus the mean. CLIP bounds the factor (default 1 decade either way) so
    a single compound cannot consume the 500 node-hour budget.
  * the P2/P3 descriptor classes become size bin x barrier bit (hop barrier above or
    below the median) instead of size bin x memory bit. This is the one-bit barrier
    disclosure graded in disclosure_probe.py (identity accuracy 0.067, limit 0.083).
Measured on the unchanged twin and on the kMC twin, same worlds:
  B. cost-information R^2 (own size law vs the class-keyed logbook asymptote)
  C. dense tau transects at P2 for eps in {0, 0.5, 1}
Barriers are MACE values; the DFT NEB check (../dft_neb) decides whether this stands.
All campaign numbers are SIMULATED UNITS.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MPT = HERE.parents[1]
sys.path.insert(0, str(MPT / "prior_predictive"))
sys.path.insert(0, str(MPT / "centralization_surface"))
import simulator as S  # noqa: E402
import tau_diagnostic as TD  # noqa: E402
import surface as SF  # noqa: E402

KMC = [json.loads(l) for l in (HERE.parent / "results" / "kmc_runs.jsonl").read_text().splitlines()
       if l.strip()]
NEB = {json.loads(l)["candidate"]: json.loads(l)
       for l in (HERE.parent / "results" / "vacancy_neb.jsonl").read_text().splitlines() if l.strip()}
_base_work = S.base_work
_world_classes = S.world_classes


def install(clip, classes="sizebar"):
    names = S.CAND["names"]
    lg = {r["candidate"]: np.log10(r["cost_to_t_end_s"]) for r in KMC if r["L"] == 48}
    z = np.array([lg[n] for n in names])
    z = np.clip(z - z.mean(), -clip, clip)
    kfac = 10.0 ** z
    eb = np.array([NEB[n]["E_hop_eV"] for n in names])
    bbit = (eb > np.median(eb)).astype(int)

    def base_work(w, fid):
        b = _base_work(w, fid)
        return b * kfac if fid == 3 else b

    def world_classes(w, level):
        if level in ("P2", "P3"):
            return bbit if classes == "bar" else S.EQUIV["P2"] * 2 + bbit
        return _world_classes(w, level)

    S.base_work = base_work
    S.world_classes = world_classes
    return {"kfac_min": float(kfac.min()), "kfac_max": float(kfac.max()),
            "barrier_bit_ones": int(bbit.sum())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["base", "kmc"], required=True)
    ap.add_argument("--clip", type=float, default=1.0)
    ap.add_argument("--classes", choices=["sizebar", "bar"], default="sizebar",
                    help="P2 classes: size bin x barrier bit, or the barrier bit alone")
    ap.add_argument("--size-adj", action="store_true",
                    help="size-adjusted shared logbook (surface.SURR_SIZE_ADJ)")
    ap.add_argument("--worlds", type=int, default=60)
    ap.add_argument("--npts", type=int, default=11)
    ap.add_argument("--procs", type=int, default=8)
    a = ap.parse_args()
    meta = {"variant": a.variant, "classes": a.classes, "clip_decades": a.clip, "worlds": a.worlds,
            "npts": a.npts, "note": "SIMULATED UNITS; kMC factors from measured MACE-barrier kMC"}
    SF.SURR_SIZE_ADJ = a.size_adj
    meta["size_adjusted_logbook"] = a.size_adj
    if a.variant == "kmc":
        meta.update(install(a.clip, a.classes))
    b = TD.part_b(a.worlds)
    c = TD.part_c(a.worlds, a.npts, a.procs)
    tag = a.variant if a.variant == "base" else f"kmc_clip{a.clip:g}_{a.classes}"
    tag += "_sizeadj" if a.size_adj else ""
    out = HERE / "results" / f"transects_{tag}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "info_r2": b, "transects": c}, indent=1))
    print("R2", {k: round(v["mean"], 3) for k, v in b.items()})
    for eps in (0.0, 0.5, 1.0):
        r0, r1 = c[f"{eps}|0.0"], c[f"{eps}|1.0"]
        print(f"eps={eps}: labels_ratio {r0['labels_ratio']:.3f} -> {r1['labels_ratio']:.3f}, "
              f"pw {r0['pw_rate']:.3f} -> {r1['pw_rate']:.3f}, id {r0['r_id_acc']:.3f} -> "
              f"{r1['r_id_acc']:.3f}, winwin {r0['win_win']:.3f} -> {r1['win_win']:.3f}")


if __name__ == "__main__":
    main()
