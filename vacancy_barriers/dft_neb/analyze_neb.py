#!/usr/bin/env python3
"""Grade predictions N1 to N5 (PREDICTION.md) from the collected DFT NEB results.

Reads results_dft/<cand>.json (written by run_neb.py on CHPC, fetched by collect_neb.sh)
and the MACE barriers in ../results/vacancy_neb.jsonl. Writes results_dft/grading.json.
N5 uses the hop rate ratio exp(dE / kT) at 1000 K between the stable compounds with the
lowest and highest DFT barrier: the kMC event count to a fixed anneal time scales with it.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RD = HERE / "results_dft"
KT = 8.617333e-5 * 1000.0
mace = {json.loads(l)["candidate"]: json.loads(l)["E_hop_eV"]
        for l in (HERE.parent / "results" / "vacancy_neb.jsonl").read_text().splitlines() if l.strip()}
cands = list(json.loads((HERE / "inputs" / "manifest.json").read_text()))
dft = {}
for c in cands:
    p = RD / f"{c}.json"
    if p.exists():
        r = json.loads(p.read_text())
        if r.get("E_hop_eV") is not None:
            dft[c] = r
stable = [c for c in cands if c != "MoS2_1T" and c in dft]
g = {"n_done": len(dft), "n_planned": len(cands),
     "table": {c: {"mace": mace[c], "dft": dft[c]["E_hop_eV"] if c in dft else None,
                   "converged": dft[c].get("neb_converged") if c in dft else None}
               for c in cands}}
if len(stable) == 6:
    g["N1"] = all(dft[c]["E_hop_eV"] > mace[c] for c in stable)
if "MoS2_2H" in dft:
    g["N2"] = 2.0 <= dft["MoS2_2H"]["E_hop_eV"] <= 2.6
if len(dft) >= 4:
    ks = sorted(dft)
    rm = np.argsort(np.argsort([mace[k] for k in ks]))
    rd = np.argsort(np.argsort([dft[k]["E_hop_eV"] for k in ks]))
    g["spearman"] = float(np.corrcoef(rm, rd)[0, 1])
    g["N3"] = g["spearman"] >= 0.6 if len(dft) == len(cands) else None
if len(stable) >= 2:
    e = [dft[c]["E_hop_eV"] for c in stable]
    g["stable_spread_eV"] = float(max(e) - min(e))
    g["rate_ratio_1000K"] = float(np.exp(g["stable_spread_eV"] / KT))
    if len(stable) == 6:
        g["N4"] = g["stable_spread_eV"] >= 0.3
        g["N5"] = g["rate_ratio_1000K"] >= 100
(RD / "grading.json").write_text(json.dumps(g, indent=1))
print(json.dumps(g, indent=1))
