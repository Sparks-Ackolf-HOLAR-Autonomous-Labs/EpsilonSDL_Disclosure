#!/usr/bin/env python3
"""Build pw.x inputs for the memory-band probe (future-work item 4).

The coupling-onset study located the regime where per-candidate
disclosure should finally pay -- the memory band, simulated at x300-
x3000 task scale with the real onset extrapolated to ~17,600 electrons
on grn061 (RAM/process ~ electrons^0.90 fitted on <= 832 e). The full
band is days of wall time per job; this probe climbs toward it
(5x5 / 6x6 / one 8x8 supercell, 1,300-3,300 electrons) and measures,
per candidate and execution config:

  * wall + QE's dynamical-RAM estimate  -> tighter RAM-law extrapolation
  * the config spread (nk4-fast vs nk1-lean) vs candidate  -> does the
    per-candidate optimal config start to diverge as memory pressure
    grows? (the live analogue of the simulated decision-regret band)

Inputs derive from ../pilot/inputs/*.pw.in exactly as in
../scale_validation/build_scale_inputs.py. K-grids are chosen so the
folded density stays production-like while cost stays within the cap.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "pilot" / "inputs"

# (candidate, supercell n, kgrid)
MATRIX = [
    ("TiS2_1T", 5, (2, 2, 1)),
    ("TiS2_1T", 6, (2, 2, 1)),
    ("MoSe2_2H", 5, (2, 2, 1)),
    ("MoSe2_2H", 6, (2, 2, 1)),
    ("WTe2_2H", 5, (2, 2, 1)),
    ("WTe2_2H", 6, (2, 2, 1)),
    ("MoSe2_2H", 8, (1, 1, 1)),   # 3,328 e: deepest affordable point
]


def parse_input(path):
    txt = path.read_text()
    a = float(re.search(r"^\s*a = ([\d.]+)", txt, re.M).group(1))
    c = float(re.search(r"^\s*c = ([\d.]+)", txt, re.M).group(1))
    ecut = float(re.search(r"ecutwfc = ([\d.]+)", txt).group(1))
    ecutrho = float(re.search(r"ecutrho = ([\d.]+)", txt).group(1))
    species = re.search(r"ATOMIC_SPECIES\n(.*?)\nATOMIC_POSITIONS",
                        txt, re.S).group(1).rstrip()
    pos = []
    for line in re.search(r"ATOMIC_POSITIONS crystal\n(.*?)\nK_POINTS",
                          txt, re.S).group(1).strip().splitlines():
        el, x, y, z = line.split()
        pos.append((el, float(x), float(y), float(z)))
    return a, c, ecut, ecutrho, species, pos


def build(cand, n, kgrid):
    a, c, ecut, ecutrho, species, pos = parse_input(PILOT / f"{cand}.pw.in")
    ntyp = len(species.splitlines())
    sup = [(el, (x + i) / n, (y + j) / n, z)
           for i in range(n) for j in range(n) for el, x, y, z in pos]
    name = f"{cand}_s{n}_k{kgrid[0]}"
    lines = [
        "&CONTROL", "  calculation = 'scf'", f"  prefix = '{name}'",
        "  pseudo_dir = './pseudos'", "  outdir = './out'",
        "  disk_io = 'nowf'", "/",
        "&SYSTEM", "  ibrav = 4", f"  a = {a * n:.6f}", f"  c = {c}",
        f"  nat = {len(sup)}", f"  ntyp = {ntyp}",
        f"  ecutwfc = {ecut}", f"  ecutrho = {ecutrho}",
        "  occupations = 'smearing'", "  smearing = 'cold'",
        "  degauss = 0.02", "/",
        "&ELECTRONS", "  mixing_beta = 0.3", "  conv_thr = 1.0d-6",
        "  diagonalization = 'david'", "  electron_maxstep = 60", "/",
        "ATOMIC_SPECIES", species,
        "ATOMIC_POSITIONS crystal",
    ]
    for el, x, y, z in sup:
        lines.append(f"  {el}  {x:.10f}  {y:.10f}  {z:.10f}")
    lines += ["K_POINTS automatic",
              f"  {kgrid[0]} {kgrid[1]} {kgrid[2]} 0 0 0", ""]
    (HERE / "inputs").mkdir(exist_ok=True)
    (HERE / "inputs" / f"{name}.pw.in").write_text("\n".join(lines))
    return name, len(sup)


if __name__ == "__main__":
    for cand, n, kg in MATRIX:
        name, nat = build(cand, n, kg)
        print(f"{name}: nat={nat}")
