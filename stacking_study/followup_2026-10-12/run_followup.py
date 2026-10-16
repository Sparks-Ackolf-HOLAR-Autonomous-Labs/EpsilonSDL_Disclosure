#!/usr/bin/env python3
"""Follow-up runs for the corrected 2H cells (2026-10-12).

Two modes, one SLURM job each (see followup.sbatch):

  relax   TiS2 single-layer 2H and ZrS2 3R bilayer, the two cells of job
          2088961 that did not finish relaxing. TiS2 mono2H cycled at BFGS
          step 8 until nstep = 100 (forces 0.002 Ry/bohr, energy noise);
          ZrS2 bi3R lost SCF convergence at BFGS step 1 (charge sloshing
          across the 30 A vacuum). Same PBE/GBRV F1-F3 ladder and DFT-D3 for
          the bilayer; changes: start a from the relaxed AA' bilayer of the
          same compound, mixing_mode = 'local-TF', conv_thr 1e-10 inside the
          relaxation, trust_radius_ini = 0.2 bohr, nstep = 300.
  socph   For the seven single-layer 2H cells in the 1.0-2.0 eV window
          (HfS2, MoS2, MoSe2, MoTe2, WS2, WSe2, WTe2): SOC gap (fully
          relativistic PSL PAW, ../../dft_campaign/soc/soc_campaign.py,
          60/400 Ry, 12x12 SCF + 18x18 NSCF) and Gamma-point ph.x on the
          scalar-relativistic GBRV ladder (F4SCF 1e-9 + ph.x, as in the 1x1
          campaign). Geometry frozen from 2088961 (outcomes.jsonl).

Gamma phonons are not a dynamical-stability proof; PBE and SOC gaps are
screening quantities. Results: results/{outcomes,phonon_outcomes,
soc_outcomes}.jsonl and followup_summary.json under $MPT_DFT_ROOT.
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent, HERE.parents[1] / "dft_campaign",
          HERE.parents[1] / "dft_campaign" / "soc"):
    sys.path.insert(0, str(p))
import run_stacking as rs  # noqa: E402  (patches rc for geometry + D3)
import soc_campaign as soc  # noqa: E402

rc = rs.rc
WINDOW_MONO = ["HfS2", "MoS2", "MoSe2", "MoTe2", "WS2", "WSe2", "WTe2"]
RELAX = ["TiS2_mono2H", "ZrS2_bi3R"]
SRC = Path(os.environ.get("MPT_STACK_OUTCOMES", "stack_outcomes.jsonl"))

_nl_stack = rc.namelists


def namelists_robust(meta, calc, *a, **kw):
    L = _nl_stack(meta, calc, *a, **kw)
    if not meta.get("robust"):
        return L
    L.insert(L.index("&ELECTRONS") + 1, "  mixing_mode = 'local-TF'")
    if calc == "vc-relax":
        L[L.index("  nstep = 100")] = "  nstep = 300"
        L = [("  conv_thr = 1.0d-10" if x == "  conv_thr = 1.0d-8" else x)
             for x in L]
        L.insert(L.index("&IONS") + 1, "  trust_radius_ini = 0.2")
    return L


rc.namelists = namelists_robust


def load_src():
    return {r["candidate"]: r
            for r in map(json.loads, SRC.read_text().splitlines())}


def archive_previous():
    """--requeue restarts from the top; keep a preempted attempt's records."""
    rc.RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    for f in rc.RESULTS.glob("*.jsonl"):
        f.rename(f.with_suffix(f".jsonl.preempted_{stamp}"))


def do_relax(src):
    metas = {m["name"]: m for m in rs.build_metas()}
    todo = []
    for name in RELAX:
        m = dict(metas[name], robust=True)
        bi2h = src.get(name.split("_")[0] + "_bi2H", {})
        if bi2h.get("a_relaxed_angstrom"):
            m["a_angstrom"] = bi2h["a_relaxed_angstrom"]
        todo.append(m)
    with ThreadPoolExecutor(max_workers=rc.WORKERS) as ex:
        return list(ex.map(rc.run_candidate, todo))


def phonon(name, rec):
    f2 = rec["stages"]["F2"]
    meta = {"name": name, "metal": rec["metal"],
            "chalcogen": rec["chalcogen"], "a_angstrom": f2["a_relaxed_angstrom"],
            "vacuum_angstrom": 20.0, "atoms_per_cell": 3}
    pos = f2["final_positions_crystal"]
    wd = rc.WORK / f"{name}_ph"
    wd.mkdir(parents=True, exist_ok=True)
    out = {"candidate": name, "pbe_gap_ev": rec["gap_ev"], "restarts": 0}
    for retry in (False, True):
        rc.stage_input(meta, "F4SCF", wd, positions=pos, retry=retry)
        r = rc.run_qe("pw.x", wd, None, "f4scf")
        p = rc.parse_pw(r["out"]) if r.get("ok") else {}
        if p.get("scf_converged") or r.get("skipped"):
            break
        out["restarts"] += 1
    out["F4SCF"] = {**r, **p}
    if p.get("scf_converged"):
        rc.ph_input(meta, wd)
        r = rc.run_qe("ph.x", wd, None, "f4")
        out["F4"] = {**r, **(rc.parse_ph(r["out"]) if r.get("ok") else {})}
    with rc.spent_lock:
        with open(rc.RESULTS / "phonon_outcomes.jsonl", "a") as fh:
            fh.write(json.dumps(out) + "\n")
    return out


def soc_meta(name, rec):
    f2 = rec["stages"]["F2"]
    return {"name": name, "metal": rec["metal"], "chalcogen": rec["chalcogen"],
            "phase": "2H-single-layer", "atoms_per_cell": 3,
            "vacuum_angstrom": 20.0,
            "a_relaxed_angstrom": f2["a_relaxed_angstrom"],
            "positions_crystal": f2["final_positions_crystal"],
            "pbe_gap_ev_scalar_rel": rec["gap_ev"]}


def do_socph(src):
    names = [f"{c}_mono2H" for c in WINDOW_MONO]
    jobs = []
    with ThreadPoolExecutor(max_workers=rc.WORKERS) as ex:
        for n in names:
            jobs.append(ex.submit(phonon, n, src[n]))
            jobs.append(ex.submit(soc.run_finalist, soc_meta(n, src[n])))
        return [j.result() for j in jobs]


def main():
    mode = sys.argv[1]
    archive_previous()
    src = load_src()
    t0 = time.time()
    recs = do_relax(src) if mode == "relax" else do_socph(src)
    summary = {"mode": mode, "records": recs,
               "node_hours": round(rc.STATE["node_hours"]
                                   + soc.STATE["node_hours"], 3),
               "qe_calls": rc.STATE["qe_calls"] + soc.STATE["qe_calls"],
               "wall_hours": round((time.time() - t0) / 3600, 3)}
    json.dump(summary, open(rc.RESULTS / f"followup_{mode}_summary.json", "w"),
              indent=1)
    print("FOLLOWUP DONE", mode, summary["node_hours"], summary["qe_calls"])


if __name__ == "__main__":
    sys.exit(main())
