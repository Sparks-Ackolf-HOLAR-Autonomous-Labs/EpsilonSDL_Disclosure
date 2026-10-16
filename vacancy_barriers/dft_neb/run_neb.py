#!/usr/bin/env python3
"""Run one compound's DFT vacancy-hop NEB on a CHPC guest node (resume-safe).

Task index = SLURM_ARRAY_TASK_ID into make_neb_inputs.CANDS (order in inputs/manifest.json).
Stages: pw.x relax of the initial and final vacancy states (fixed cell), then neb.x with the
relaxed end states. A requeue after preemption skips finished relaxations and restarts
neb.x from its .path file. Writes results/<cand>.json with the forward barrier, the
energy profile, convergence flags and QE CPU/wall seconds.
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(os.environ.get("MPT_NEB_ROOT", ".")).resolve()
INP = ROOT / "inputs"
RES = ROOT / "results"
NP = int(os.environ.get("SLURM_NTASKS", "32"))
NK = os.environ.get("MPT_NEB_NK", "2")
CANDS = list(json.loads((INP / "manifest.json").read_text()).keys())
name = CANDS[int(os.environ["SLURM_ARRAY_TASK_ID"])]
RES.mkdir(exist_ok=True)
log = {"candidate": name, "restart_count": int(os.environ.get("SLURM_RESTART_COUNT", "0")),
       "node": os.environ.get("SLURMD_NODENAME"), "ranks": NP, "npool": NK}


def run(exe, inp, out, flag="-in"):
    t0 = time.time()
    cmd = f"mpirun -np {NP} {exe} -nk {NK} {flag} {inp} > {out} 2>&1"
    rc = subprocess.call(cmd, shell=True, cwd=ROOT)
    return rc, time.time() - t0


def cpu_s(txt, tag):
    m = re.findall(tag + r"\s*:\s*((?:[0-9.]+[hms]?\s*)+?)\s*CPU", txt)
    if not m:
        return None
    tok, sec, cur = re.sub(r"\s+", "", m[-1]), 0.0, ""
    for ch in tok:
        if ch in "hms":
            sec += float(cur) * {"h": 3600, "m": 60, "s": 1}[ch]; cur = ""
        else:
            cur += ch
    return sec + (float(cur) if cur else 0.0)


def relaxed(out):
    p = ROOT / out
    if not p.exists():
        return None
    t = p.read_text(errors="ignore")
    if "End of BFGS Geometry Optimization" not in t or "JOB DONE" not in t:
        return None
    blk = t.split("Begin final coordinates")[1].split("End final coordinates")[0]
    lines = blk.split("ATOMIC_POSITIONS (crystal)")[1].strip().splitlines()
    e = float(re.findall(r"!\s+total energy\s+=\s+(-?[0-9.]+) Ry", t)[-1])
    sym = [l.split()[0] for l in lines]
    frac = [[float(x) for x in l.split()[1:4]] for l in lines]
    return sym, frac, e, cpu_s(t, "PWSCF")


for st in ("ini", "fin"):
    out = f"{name}.{st}.out"
    if relaxed(out) is None:
        rc, w = run("pw.x", f"inputs/{name}.{st}.in", out)
        log[f"{st}_rc"], log[f"{st}_wall_s"] = rc, w
    r = relaxed(out)
    if r is None:
        log["error"] = f"{st} relax did not finish"
        (RES / f"{name}.json").write_text(json.dumps(log, indent=1))
        raise SystemExit(1)
    log[f"{st}_E_Ry"], log[f"{st}_cpu_s"] = r[2], r[3]

sym, ini, _, _ = relaxed(f"{name}.ini.out")
_, fin, _, _ = relaxed(f"{name}.fin.out")
fin = [[f - round(f - i) for f, i in zip(rf, ri)] for rf, ri in zip(fin, ini)]  # same periodic image
fmt = lambda f: "\n".join(f"  {s}  {x:.10f}  {y:.10f}  {z:.10f}" for s, (x, y, z) in zip(sym, f))
restart = "restart" if (ROOT / f"{name}_neb.path").exists() else "from_scratch"
tmpl = (INP / f"{name}.neb.tmpl").read_text()
(ROOT / f"{name}.neb.in").write_text(
    tmpl.replace("@RESTART@", restart).replace("@FIRST@", fmt(ini)).replace("@LAST@", fmt(fin)))
log["neb_restart_mode"] = restart
rc, w = run("neb.x", f"{name}.neb.in", f"{name}.neb.out", flag="-inp")
t = (ROOT / f"{name}.neb.out").read_text(errors="ignore")
log["neb_rc"], log["neb_wall_s"] = rc, w
fw = re.findall(r"activation energy \(->\)\s*=\s*(-?[0-9.]+)\s*eV", t)
bw = re.findall(r"activation energy \(<-\)\s*=\s*(-?[0-9.]+)\s*eV", t)
log["E_hop_eV"] = float(fw[-1]) if fw else None
log["E_hop_back_eV"] = float(bw[-1]) if bw else None
log["neb_converged"] = "neb: convergence achieved" in t
log["neb_iterations"] = len(re.findall(r"-{10,} iteration", t))
log["neb_cpu_s"] = cpu_s(t, "NEB")
dat = ROOT / f"{name}_neb.dat"
if dat.exists():
    log["profile_eV"] = [[float(x) for x in l.split()[:2]]
                         for l in dat.read_text().splitlines() if l.strip()]
(RES / f"{name}.json").write_text(json.dumps(log, indent=1))
print(json.dumps({k: log[k] for k in ("candidate", "E_hop_eV", "neb_converged")}))
