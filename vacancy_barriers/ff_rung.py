#!/usr/bin/env python3
"""Test A: a force field suited to the solids (MACE-MP-0 medium) as a rung below F1.

Per compound: in-plane relaxation of the 1x1 prototype (c and vacuum fixed), then a
200-step NVT MD run on 2x2, 3x3, 4x4 supercells. Records wall time, steps and the
relaxed lattice constant / energy. Writes one JSON line per compound as it finishes
(resume-safe). Run with ~/venvs/mace/bin/python on the DGX GPU.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from ase import units
from ase.filters import FrechetCellFilter
from ase.io import read
from ase.md.langevin import Langevin
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
from ase.optimize import FIRE
from mace.calculators import mace_mp

HERE = Path(__file__).parent
CAND = HERE.parent / "prior_predictive" / "candidates"
OUT = HERE / "results" / "ff_rung.jsonl"
OUT.parent.mkdir(exist_ok=True)

calc = mace_mp(model="medium", device="cuda", default_dtype="float32")
done = set()
if OUT.exists():
    done = {json.loads(l)["candidate"] for l in OUT.read_text().splitlines() if l.strip()}

# warm-up so CUDA initialisation is not billed to the first compound
w = read(CAND / "MoS2_1T.cif"); w.calc = calc; w.get_forces()

for cif in sorted(CAND.glob("*.cif")):
    name = cif.stem
    if name in done:
        continue
    at = read(cif)
    at.calc = calc
    nfu = 1 if name.endswith("_1T") else 2
    filt = FrechetCellFilter(at, mask=[1, 1, 0, 0, 0, 1])
    opt = FIRE(filt, logfile=None)
    t0 = time.perf_counter()
    conv = opt.run(fmax=0.02, steps=400)
    relax_s = time.perf_counter() - t0
    rec = {"candidate": name, "phase": name.split("_")[1], "n_atoms_1x1": len(at),
           "relax_converged": bool(conv), "relax_steps": int(opt.nsteps),
           "relax_wall_s": relax_s,
           "a_ff": float(np.linalg.norm(at.cell[0])),
           "e_per_fu_ev": float(at.get_potential_energy() / nfu),
           "md": []}
    base = at.copy()
    for n in (2, 3, 4):
        sc = base.repeat((n, n, 1))
        sc.calc = calc
        MaxwellBoltzmannDistribution(sc, temperature_K=300, rng=np.random.default_rng(0))
        dyn = Langevin(sc, 2 * units.fs, temperature_K=300, friction=0.02,
                       rng=np.random.default_rng(1))
        t0 = time.perf_counter()
        dyn.run(200)
        rec["md"].append({"n": n, "atoms": len(sc), "steps": 200,
                          "wall_s": time.perf_counter() - t0,
                          "T_end_K": float(sc.get_temperature())})
    with OUT.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(name, rec["relax_steps"], round(relax_s, 2), round(rec["a_ff"], 4),
          [round(m["wall_s"], 2) for m in rec["md"]], flush=True)
