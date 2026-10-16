#!/usr/bin/env python3
"""Test B, stage 2: run vac_kmc for every compound with MACE barriers, L = 24 and 48.

Fixed physical task for every compound: anneal at 1000 K for t_end = 1 s with 2 %
chalcogen vacancies. Runs stop at 200,000 events; when capped, the cost to reach t_end is
projected as wall * t_end / t_reached (BKL time is a sum of exponential waits, so the
projection is linear once the cluster fraction has settled). One JSON line per run.
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
EXE = "/tmp/vac_kmc"
subprocess.run(["gcc", "-O2", "-o", EXE, str(HERE / "vac_kmc.c"), "-lm"], check=True)
OUT = HERE / "results" / "kmc_runs.jsonl"
OUT.unlink(missing_ok=True)
T, CONC, T_END, CAP = 1000.0, 0.02, 1.0, 200000
for line in (HERE / "results" / "vacancy_neb.jsonl").read_text().splitlines():
    r = json.loads(line)
    for L in (24, 48):
        p = subprocess.run([EXE, f"{r['E_hop_eV']:.4f}", f"{r['E_bind_divac_eV']:.4f}", str(T),
                            str(L), str(CONC), str(T_END), str(CAP), "7"],
                           capture_output=True, text=True, check=True)
        k = json.loads(p.stdout)
        frac = min(1.0, k["t_reached_s"] / T_END) if k["t_reached_s"] > 0 else 0.0
        k.update(candidate=r["candidate"], L=L, T_K=T, t_end_s=T_END, cap_events=CAP,
                 E_hop_eV=r["E_hop_eV"], E_bind_eV=r["E_bind_divac_eV"],
                 capped=k["events"] >= CAP,
                 cost_to_t_end_s=k["wall_s"] / frac if frac > 0 else float("nan"),
                 events_to_t_end=k["events"] / frac if frac > 0 else float("nan"))
        with OUT.open("a") as f:
            f.write(json.dumps(k) + "\n")
        print(r["candidate"], L, k["events"], f"{k['cost_to_t_end_s']:.3g}", k["cluster_frac"], flush=True)
