#!/usr/bin/env python3
"""Test B, stage 1: chalcogen-vacancy hop barrier and divacancy binding (MACE-MP-0).

Per compound: 4x4 supercell of the MACE-relaxed 1x1 cell (a from results/ff_rung.jsonl,
positions relaxed at fixed cell). Vacancy at a top-plane chalcogen site i; the hop moves
the in-plane nearest-neighbour chalcogen j into i (climbing-image NEB, 3 images, IDPP
start). Divacancy binding E_b = E(V_i+V_j) + E(perfect) - 2 E(V_i); negative = attractive.
One JSON line per compound (resume-safe). Run with ~/venvs/mace/bin/python on the DGX GPU.
"""
import json
import time
from pathlib import Path

import numpy as np
from ase.io import read
from ase.mep import NEB
from ase.optimize import FIRE
from mace.calculators import mace_mp

HERE = Path(__file__).parent
CAND = HERE.parent / "prior_predictive" / "candidates"
FF = {json.loads(l)["candidate"]: json.loads(l)
      for l in (HERE / "results" / "ff_rung.jsonl").read_text().splitlines() if l.strip()}
OUT = HERE / "results" / "vacancy_neb.jsonl"
CHALC = {"S", "Se", "Te"}

calc = mace_mp(model="medium", device="cuda", default_dtype="float32")
done = set()
if OUT.exists():
    done = {json.loads(l)["candidate"] for l in OUT.read_text().splitlines() if l.strip()}


def relax(at, fmax=0.05, steps=300):
    at.calc = calc
    opt = FIRE(at, logfile=None)
    opt.run(fmax=fmax, steps=steps)
    return at.get_potential_energy(), opt.nsteps


for cif in sorted(CAND.glob("*.cif")):
    name = cif.stem
    if name in done or name not in FF:
        continue
    t0 = time.perf_counter()
    at = read(cif)
    cell = at.cell.array.copy()
    f = FF[name]["a_ff"] / np.linalg.norm(cell[0])
    cell[:2] *= f
    at.set_cell(cell, scale_atoms=True)
    sc = at.repeat((4, 4, 1))
    e_perf, _ = relax(sc)
    sym = np.array(sc.get_chemical_symbols())
    z = sc.positions[:, 2]
    ch = np.where(np.isin(sym, list(CHALC)))[0]
    top = ch[np.isclose(z[ch], z[ch].max(), atol=0.3)]
    # i near the cell centre; j its nearest neighbour in the same plane (minimum image)
    ctr = sc.cell.sum(axis=0) / 2
    i = top[np.argmin(np.linalg.norm(sc.positions[top, :2] - ctr[:2], axis=1))]
    d = sc.get_distances(i, top, mic=True)
    d[top == i] = 1e9
    j = top[np.argmin(d)]
    pos_i = sc.positions[i].copy()

    ini = sc.copy(); del ini[[i]]
    jj = j - (1 if j > i else 0)
    fin = ini.copy(); fin.positions[jj] = pos_i
    e_ini, s_ini = relax(ini)
    e_fin, s_fin = relax(fin)
    images = [ini] + [ini.copy() for _ in range(3)] + [fin]
    for im in images[1:-1]:
        im.calc = calc
    neb = NEB(images, climb=True, allow_shared_calculator=True)
    neb.interpolate("idpp", mic=True)
    opt = FIRE(neb, logfile=None)
    conv = opt.run(fmax=0.1, steps=250)
    energies = [im.get_potential_energy() for im in images]
    e_hop = max(energies) - e_ini

    div = sc.copy(); del div[sorted([i, j], reverse=True)]
    e_div, _ = relax(div)
    e_b = e_div + e_perf - 2 * e_ini
    rec = {"candidate": name, "phase": name.split("_")[1], "atoms_4x4": len(sc),
           "hop_distance_A": float(d.min()), "E_hop_eV": float(e_hop),
           "E_end_asym_eV": float(e_fin - e_ini), "neb_converged": bool(conv),
           "neb_steps": int(opt.nsteps), "E_bind_divac_eV": float(e_b),
           "wall_s": time.perf_counter() - t0}
    with OUT.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(name, round(e_hop, 3), round(e_b, 3), conv, opt.nsteps, round(rec["wall_s"], 1), flush=True)
