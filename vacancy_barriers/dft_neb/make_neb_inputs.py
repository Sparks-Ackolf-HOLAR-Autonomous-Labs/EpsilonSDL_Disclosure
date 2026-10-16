#!/usr/bin/env python3
"""Build the QE inputs for the DFT check of the chalcogen-vacancy hop barriers.

Per compound: the 3x3 supercell of the PBE-relaxed 1x1 cell (the same geometry as the
rescreen_3x3 F2 deck). One top-plane chalcogen i near the cell centre is removed; the final
state moves its in-plane nearest chalcogen neighbour j into site i (same hop as the MACE
test). Writes, per compound:
  <cand>.ini.in, <cand>.fin.in   fixed-cell 'relax' of the two end states (pw.x)
  <cand>.neb.tmpl                neb.x engine input with @FIRST@ / @LAST@ placeholders,
                                 filled by run_neb.py from the relaxed end states
Settings: PBE, GBRV 1.5 USPP, 40/320 Ry, cold smearing 0.015 Ry, 3x3x1 k-points,
5 images (3 moving), climbing image, path_thr 0.1 eV/A (the MACE NEB used fmax 0.1).
Run from the repo with ~/venvs/mace/bin/python (needs ASE only for the neighbour search).
"""
import json
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "rescreen_3x3" / "inputs"
OUT = HERE / "inputs"
CHALC = {"S", "Se", "Te"}

# Seven compounds spanning the MACE hop-barrier range (eV, MACE-MP-0, 4x4 cell):
# WS2 2H 1.01, MoS2 2H 0.90 (literature PBE anchor, Komsa 2012), HfS2 1T 0.86,
# TiS2 1T 0.72, ZrTe2 1T 0.48, TiTe2 1T 0.40, MoS2 1T 0.23 (unstable host, distorts to 1T').
CANDS = ["WS2_2H", "MoS2_2H", "HfS2_1T", "TiS2_1T", "ZrTe2_1T", "TiTe2_1T", "MoS2_1T"]


def parse_deck(txt):
    a = float(re.search(r"\ba\s*=\s*([0-9.]+)", txt).group(1))
    c = float(re.search(r"\bc\s*=\s*([0-9.]+)", txt).group(1))
    species = re.search(r"ATOMIC_SPECIES\n(.*?)ATOMIC_POSITIONS", txt, re.S).group(1)
    pos = re.search(r"ATOMIC_POSITIONS crystal\n(.*?)K_POINTS", txt, re.S).group(1)
    sym, frac = [], []
    for line in pos.strip().splitlines():
        t = line.split()
        sym.append(t[0]); frac.append([float(x) for x in t[1:4]])
    ntyp = int(re.search(r"ntyp\s*=\s*(\d+)", txt).group(1))
    return a, c, species.rstrip("\n"), sym, np.array(frac), ntyp


def cart(a, c, frac):
    cell = np.array([[a, 0, 0], [-a / 2, a * np.sqrt(3) / 2, 0], [0, 0, c]])
    return frac @ cell, cell


def header(name, calc, a, c, nat, ntyp, species, extra_ctrl=""):
    return f"""&CONTROL
  calculation = '{calc}'
  prefix = '{name}'
  pseudo_dir = './pseudos'
  outdir = './out_{name}'
  disk_io = 'low'
  forc_conv_thr = 1.0d-3
  etot_conv_thr = 1.0d-5
  nstep = 150{extra_ctrl}
/
&SYSTEM
  ibrav = 4
  a = {a:.6f}
  c = {c}
  nat = {nat}
  ntyp = {ntyp}
  ecutwfc = 40.0
  ecutrho = 320.0
  occupations = 'smearing'
  smearing = 'cold'
  degauss = 0.015
/
&ELECTRONS
  mixing_beta = 0.3
  conv_thr = 1.0d-7
  electron_maxstep = 150
/
&IONS
/
ATOMIC_SPECIES
{species}
"""


def positions(sym, frac):
    return "\n".join(f"  {s}  {x:.10f}  {y:.10f}  {z:.10f}" for s, (x, y, z) in zip(sym, frac))


KPTS = "K_POINTS automatic\n  3 3 1 0 0 0\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name in CANDS:
        a, c, species, sym, frac, ntyp = parse_deck((SRC / f"{name}.f2.in").read_text())
        xyz, cell = cart(a, c, frac)
        sym = np.array(sym)
        ch = np.where(np.isin(sym, list(CHALC)))[0]
        top = ch[np.isclose(xyz[ch, 2], xyz[ch, 2].max(), atol=0.3)]
        ctr = cell[:2, :2].sum(axis=0) / 2
        i = top[np.argmin(np.linalg.norm(xyz[top, :2] - ctr, axis=1))]
        # in-plane nearest neighbour of i, chosen without crossing the cell boundary
        d = np.linalg.norm(xyz[top] - xyz[i], axis=1)
        d[top == i] = 1e9
        j = top[np.argmin(d)]
        keep = [k for k in range(len(sym)) if k != i]
        ini = frac[keep].copy()
        jj = keep.index(j)
        fin = ini.copy(); fin[jj] = frac[i]
        s2 = sym[keep]
        nat = len(keep)
        (OUT / f"{name}.ini.in").write_text(
            header(f"{name}_ini", "relax", a, c, nat, ntyp, species)
            + "ATOMIC_POSITIONS crystal\n" + positions(s2, ini) + "\n" + KPTS)
        (OUT / f"{name}.fin.in").write_text(
            header(f"{name}_fin", "relax", a, c, nat, ntyp, species)
            + "ATOMIC_POSITIONS crystal\n" + positions(s2, fin) + "\n" + KPTS)
        engine = header(f"{name}_neb", "scf", a, c, nat, ntyp, species).replace(
            "  calculation = 'scf'\n", "").replace("&IONS\n/\n", "")
        tmpl = f"""BEGIN
BEGIN_PATH_INPUT
&PATH
  restart_mode = '@RESTART@'
  string_method = 'neb'
  nstep_path = 120
  num_of_images = 5
  opt_scheme = 'broyden'
  CI_scheme = 'auto'
  path_thr = 0.1
/
END_PATH_INPUT
BEGIN_ENGINE_INPUT
{engine}BEGIN_POSITIONS
FIRST_IMAGE
ATOMIC_POSITIONS crystal
@FIRST@
LAST_IMAGE
ATOMIC_POSITIONS crystal
@LAST@
END_POSITIONS
{KPTS}END_ENGINE_INPUT
END
"""
        (OUT / f"{name}.neb.tmpl").write_text(tmpl)
        manifest[name] = {"nat": nat, "removed_index": int(i), "moved_index_after_removal": jj,
                          "hop_distance_A": float(d.min()), "a_supercell_A": a}
        print(name, nat, round(float(d.min()), 3))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
