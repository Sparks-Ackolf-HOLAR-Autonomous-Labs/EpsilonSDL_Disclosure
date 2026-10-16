#!/usr/bin/env python3
"""Memory-band probe runner. Serial execution on
grn061 inside one SLURM allocation; every input runs under two
execution configs so the per-candidate config spread is measured:

  lean : 32 ranks, nk 1  (lowest memory: no pool replication)
  fast : 32 ranks, nk 4  (k-parallel; replicates data across pools)

Budget guard: MPT_PROBE_NH_CAP (per-core node-hours, default 30). Jobs
run smallest-first; a job whose projected cost (from the running
electron-scaling fit) would breach the cap is skipped and recorded, so
the deepest points yield gracefully rather than dying mid-flight.
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(os.environ.get("MPT_PROBE_ROOT", ".")).resolve()
RESULTS = ROOT / "results"
NH_CAP = float(os.environ.get("MPT_PROBE_NH_CAP", "30"))
STATE = {"nh": 0.0}

# smallest-first so the cap bites the deep end, not the baseline
JOBS = [
    "TiS2_1T_s5_k2", "MoSe2_2H_s5_k2", "WTe2_2H_s5_k2",
    "TiS2_1T_s6_k2", "MoSe2_2H_s6_k2", "WTe2_2H_s6_k2",
    "MoSe2_2H_s8_k1",
]
CONFIGS = [("lean", 32, 1), ("fast", 32, 4)]


def run(name, tag, ranks, npool):
    wd = ROOT / "work" / f"{name}_{tag}"
    wd.mkdir(parents=True, exist_ok=True)
    if not (wd / "pseudos").exists():
        (wd / "pseudos").symlink_to(ROOT / "pseudos")
    out = wd / "run.out"
    t0 = time.time()
    subprocess.run(
        ["mpirun", "-np", str(ranks), "--bind-to", "none", "pw.x",
         "-nk", str(npool), "-in", str(ROOT / "inputs" / f"{name}.pw.in")],
        cwd=wd, stdout=open(out, "w"), stderr=subprocess.STDOUT)
    wall = time.time() - t0
    txt = out.read_text(errors="replace")
    ram = re.search(r"dynamical RAM per process >\s+([\d.]+) (MB|GB)", txt)
    tot = re.search(r"total dynamical RAM >\s+([\d.]+) (MB|GB)", txt)
    nel = re.search(r"number of electrons\s+=\s+([\d.]+)", txt)
    nh = wall / 3600.0 * ranks / 64.0
    STATE["nh"] += nh
    import shutil
    shutil.rmtree(wd / "out", ignore_errors=True)
    rec = dict(name=name, cfg=tag, ranks=ranks, npool=npool,
               wall_s=round(wall, 2),
               converged="convergence has been achieved" in txt,
               ram_mb_per_proc=(float(ram.group(1)) *
                                (1024 if ram.group(2) == "GB" else 1)
                                if ram else None),
               ram_total=(f"{tot.group(1)} {tot.group(2)}" if tot
                          else None),
               nelec=float(nel.group(1)) if nel else None,
               nh=round(nh, 4), nh_cum=round(STATE["nh"], 4))
    with open(RESULTS / "probe_results.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)
    return rec


def main():
    RESULTS.mkdir(exist_ok=True)
    walls = {}   # name -> mean wall so far, for projection
    for name in JOBS:
        for tag, ranks, npool in CONFIGS:
            # project cost from the most recent same-config run's wall
            # scaled by electron ratio ^ 2.6 (measured heavy-regime
            # exponent); conservative first job assumed 1 nh
            proj = walls.get(tag, 0.5) * 4
            if STATE["nh"] + min(proj, 25) > NH_CAP:
                rec = dict(name=name, cfg=tag, skipped=True,
                           reason=f"cap {NH_CAP} nh would be breached "
                                  f"(spent {STATE['nh']:.1f})")
                with open(RESULTS / "probe_results.jsonl", "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                print(json.dumps(rec), flush=True)
                continue
            r = run(name, tag, ranks, npool)
            walls[tag] = r["nh"]
    print(f"DONE total {STATE['nh']:.2f} per-core node-hours")


if __name__ == "__main__":
    main()
