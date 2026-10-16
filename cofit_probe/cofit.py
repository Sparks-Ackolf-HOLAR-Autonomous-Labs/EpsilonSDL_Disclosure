#!/usr/bin/env python3
"""Co-scheduling (packing) probe. Measures the three quantities the
revised live comparison No. 2 design rests on:

  1. wall(16 ranks) for the two heaviest committed 6x6 candidates
     (solo) -> the co-scheduling half-node efficiency curve;
  2. the same two jobs run CONCURRENTLY at 16+16 ranks on one node ->
     co-tenant contention at coupling-band size and the measured
     makespan vs the sequential 32-rank baseline (known from probe
     1928420: MoSe2 3,777 s + WTe2 4,868 s = 8,645 s);
  3. per-process RAM at 16 ranks -> the packing feasibility arithmetic
     for memory-aware co-residency (the Theorem-3 memory bit).

Budget guard: MPT_COFIT_NH_CAP per-core node-hours (default 6).
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(os.environ.get("MPT_COFIT_ROOT", ".")).resolve()
RESULTS = ROOT / "results"
NH_CAP = float(os.environ.get("MPT_COFIT_NH_CAP", "6"))
STATE = {"nh": 0.0}

PAIR = ["MoSe2_2H_s6_k2", "WTe2_2H_s6_k2"]


def launch(name, tag, ranks):
    wd = ROOT / "work" / f"{name}_{tag}"
    wd.mkdir(parents=True, exist_ok=True)
    if not (wd / "pseudos").exists():
        (wd / "pseudos").symlink_to(ROOT / "pseudos")
    out = wd / "run.out"
    p = subprocess.Popen(
        ["mpirun", "-np", str(ranks), "--bind-to", "none", "pw.x",
         "-nk", "1", "-in", str(ROOT / "inputs" / f"{name}.pw.in")],
        cwd=wd, stdout=open(out, "w"), stderr=subprocess.STDOUT)
    return p, out, time.time()


def harvest(name, tag, ranks, out, t0, t1):
    wall = t1 - t0
    txt = out.read_text(errors="replace")
    ram = re.search(r"dynamical RAM per process >\s+([\d.]+) (MB|GB)", txt)
    tot = re.search(r"total dynamical RAM >\s+([\d.]+) (MB|GB)", txt)
    nh = wall / 3600.0 * ranks / 64.0
    STATE["nh"] += nh
    import shutil
    shutil.rmtree(ROOT / "work" / f"{name}_{tag}" / "out",
                  ignore_errors=True)
    rec = dict(name=name, tag=tag, ranks=ranks, wall_s=round(wall, 2),
               converged="convergence has been achieved" in txt,
               ram_mb_per_proc=(float(ram.group(1)) *
                                (1024 if ram.group(2) == "GB" else 1)
                                if ram else None),
               ram_total=(f"{tot.group(1)} {tot.group(2)}" if tot
                          else None),
               nh=round(nh, 4), nh_cum=round(STATE["nh"], 4))
    with open(RESULTS / "cofit_results.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)
    return rec


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)

    # phase 1: solo 16-rank runs (sequential)
    for name in PAIR:
        if STATE["nh"] > NH_CAP:
            print(f"CAP {NH_CAP} nh reached - skipping {name} solo")
            continue
        p, out, t0 = launch(name, "solo16", 16)
        p.wait()
        harvest(name, "solo16", 16, out, t0, time.time())

    # phase 2: concurrent 16+16 on the same node
    if STATE["nh"] <= NH_CAP:
        procs = [launch(name, "co16", 16) for name in PAIR]
        t_start = time.time()
        for name, (p, out, t0) in zip(PAIR, procs):
            p.wait()
            harvest(name, "co16", 16, out, t0, time.time())
        makespan = time.time() - t_start
        with open(RESULTS / "cofit_results.jsonl", "a") as fh:
            fh.write(json.dumps({"tag": "co16_makespan",
                                 "makespan_s": round(makespan, 2)}) + "\n")
        print(f"co16 makespan {makespan:.0f} s", flush=True)
    else:
        print(f"CAP {NH_CAP} nh reached - skipping concurrent phase")

    print(f"DONE total {STATE['nh']:.2f} per-core node-hours", flush=True)


if __name__ == "__main__":
    main()
