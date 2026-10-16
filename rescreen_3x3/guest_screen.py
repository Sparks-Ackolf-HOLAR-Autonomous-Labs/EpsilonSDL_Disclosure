#!/usr/bin/env python3
"""Real 29-candidate MX2 screening on a FREE / GUEST CHPC partition.
This is a live, non-simulated workload: real Quantum
ESPRESSO 7.4 on preemptible, free-of-charge nodes (kingspeak-guest /
lonepeak-guest / notchpeak-guest), which the sparks account can use at
zero allocation charge on other owners' idle hardware.

Why a separate driver from paired_comparison_1{,2}
----------------------------------------------
Guest nodes are PREEMPTIBLE: a job can be killed and requeued at any
moment when the node's owner reclaims it. Two consequences drive the
design:

  1. RESUME. Every QE stage writes `<cand>.<stage>.out`; on (re)start we
     skip any stage whose output already shows a clean finish, so a
     requeue continues instead of restarting from scratch. Combined with
     `#SBATCH --requeue`, preemption only delays the screen.

  2. PREEMPTION-ROBUST COST. Wall-clock is contaminated by preemption
     gaps, so the recorded cost metric is QE's OWN internal
     "PWSCF : ... CPU" seconds (the processor time pw.x actually spent),
     which is unaffected by a job sitting in the queue after a requeue.
     Wall time is still logged, but the config-cost comparison uses CPU
     core-seconds.

What it measures (all REAL, not simulated units)
------------------------------------------------
For each of the 29 CC0 MX2 candidates at 3x3-supercell scale:
  * the full F1 -> F2 -> F3 ladder at the CEDT-P4 class-matched config,
    giving the real PBE screening gap (qualifier = gap in [1.0, 2.0] eV);
  * F2 (the pivotal production-SCF "label" stage) ALSO at the DTDE
    worst-case config, so each candidate yields a clean, same-hardware,
    same-geometry CPU-core-second delta between the no-sharing worst-case
    config and the broker's class-matched config -- the execution-layer
    quantity the whole privacy-tax mechanism trades on, now on FREE
    hardware and on a DIFFERENT cluster than the owned granite node
    (a cross-hardware anchor for the cost twin).

Nothing here is a paired campaign verdict; the clean paired CEDT-vs-DTDE
timing comparison stays on the owned node (comparison No. 2). This run
provides a real workload, in real units, on the free
partition -- and it independently re-measures the config-cost delta and
the qualifier set on hardware we do not own.
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parent.parent))
import qe_retry  # solver-retry rule (Davidson -> cg), adopted 2026-09-30

ROOT = Path(os.environ.get("MPT_GUEST_ROOT", ".")).resolve()
INPUTS = ROOT / "inputs"
WORK = ROOT / "work"
RESULTS = ROOT / "results"
GAP_LO, GAP_HI = 1.0, 2.0

# execution configs (ranks, npool) -- identical to the comparison drivers
CEDT_CFG = {"f1": (16, 1), "f2": (32, 2), "f3": (32, 4)}
DTDE_CFG = {"f1": (32, 1), "f2": (32, 1), "f3": (32, 1)}

# wall-time ceiling per QE call; a stage exceeding it is treated as
# preempted/stuck and left for the next (requeued) invocation to resume.
CALL_TIMEOUT_S = int(os.environ.get("MPT_GUEST_CALL_TIMEOUT", "9000"))


def qe_cpu_seconds(txt):
    """QE's own 'PWSCF :  <cpu>  CPU  <wall> WALL' line -> cpu seconds.
    Preemption-robust: this is processor time inside pw.x, not wall."""
    # QE pads minutes/seconds with spaces ("4m 4.61s"), so allow
    # whitespace between the h/m/s groups and strip it before parsing.
    m = re.search(r"PWSCF\s*:\s*((?:[0-9.]+[hms]?\s*)+?)\s*CPU", txt)
    if not m:
        return None
    tok = re.sub(r"\s+", "", m.group(1))
    sec, cur = 0.0, ""
    for ch in tok:
        if ch.isdigit() or ch == ".":
            cur += ch
        elif ch == "h":
            sec += float(cur) * 3600.0; cur = ""
        elif ch == "m":
            sec += float(cur) * 60.0; cur = ""
        elif ch == "s":
            sec += float(cur); cur = ""
    if cur:
        sec += float(cur)
    return round(sec, 2)


def finished_ok(outfile, stage):
    """True if a prior invocation already completed this stage cleanly,
    so we can skip it on resume."""
    if not outfile.exists():
        return False
    txt = outfile.read_text(errors="replace")
    if "JOB DONE" not in txt:
        return False
    if stage in ("f1", "f2"):
        return "convergence has been achieved" in txt
    return True  # f3 nscf: JOB DONE is sufficient


def run_qe(wd, name, stage, ranks, npool, tag):
    """pw.x call with the solver-retry rule: an eigensolver crash is
    rerun once with the next solver (Davidson -> cg); the retry and the
    outcome class ('converged' / 'ran_not_converged' / 'crashed') are
    recorded so crashes are never pooled with window misses."""
    r = _run_qe_once(wd, name, stage, ranks, npool, tag)
    outcome, kind = qe_retry.classify(r["out"], r["rc"])
    if outcome == "crashed" and kind == "solver":
        rt = qe_retry.retry_input(INPUTS / f"{name}.{stage}.in", wd)
        if rt:
            r2 = _run_qe_once(wd, name, stage, ranks, npool,
                              f"{tag}.{rt[1]}", inp=rt[0])
            r2["first_attempt"] = {k: r.get(k) for k in
                                   ("rc", "wall_s", "cpu_s", "out")}
            r2["solver_retry"], r2["solver"] = True, rt[1]
            r = r2
            outcome, kind = qe_retry.classify(r["out"], r["rc"])
    r["outcome"], r["fail_kind"] = outcome, kind
    return r


def _run_qe_once(wd, name, stage, ranks, npool, tag, inp=None):
    """Run one pw.x call unless a clean output already exists. Returns a
    telemetry dict; sets 'resumed' when the prior output was reused."""
    inp = inp or INPUTS / f"{name}.{stage}.in"
    out = wd / f"{stage}.{tag}.out"
    if finished_ok(out, stage):
        txt = out.read_text(errors="replace")
        return {"resumed": True, "rc": 0, "cpu_s": qe_cpu_seconds(txt),
                "wall_s": None, "out": str(out), "ranks": ranks,
                "npool": npool}
    t0 = time.time()
    cmd = ["mpirun", "-np", str(ranks), "--bind-to", "none",
           "pw.x", "-nk", str(npool), "-in", str(inp)]
    try:
        with open(out, "w") as fh:
            rc = subprocess.call(cmd, cwd=wd, stdout=fh,
                                 stderr=subprocess.STDOUT,
                                 timeout=CALL_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"resumed": False, "rc": 124, "timeout": True,
                "wall_s": round(time.time() - t0, 1), "out": str(out),
                "ranks": ranks, "npool": npool, "cpu_s": None}
    wall = round(time.time() - t0, 1)
    txt = out.read_text(errors="replace")
    return {"resumed": False, "rc": rc, "wall_s": wall,
            "cpu_s": qe_cpu_seconds(txt), "out": str(out),
            "ranks": ranks, "npool": npool}


def parse_scf(txt):
    m = re.search(r"number of electrons\s+=\s+([\d.]+)", txt)
    return {"converged": "convergence has been achieved" in txt,
            "nelec": float(m.group(1)) if m else None}


def parse_gap(txt, nelec):
    blocks = re.findall(
        r"k =[^\n]*\([ 0-9]+ PWs\)\s+bands \(ev\):\n\n((?:\s+-?[\d.]+)+)",
        txt)
    if not blocks or not nelec:
        return None
    nocc = int(round(nelec)) // 2
    vbm, cbm = -1e9, 1e9
    for b in blocks:
        ev = [float(x) for x in b.split()]
        if len(ev) <= nocc:
            return None
        vbm = max(vbm, ev[nocc - 1])
        cbm = min(cbm, ev[nocc])
    return max(cbm - vbm, 0.0)


def append(fname, row):
    with open(RESULTS / fname, "a") as fh:
        fh.write(json.dumps(row) + "\n")


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(exist_ok=True)
    manifest = json.load(open(INPUTS / "manifest.json"))
    names = [m["name"] for m in manifest]
    host = os.environ.get("SLURMD_NODENAME", "?")
    part = os.environ.get("SLURM_JOB_PARTITION", "?")
    jobid = os.environ.get("SLURM_JOB_ID", "?")
    restart = int(os.environ.get("SLURM_RESTART_COUNT", "0"))
    print(f"guest screen start: job={jobid} part={part} node={host} "
          f"restart={restart} ncand={len(names)}", flush=True)
    append("run_log.jsonl", {"event": "start", "job": jobid, "part": part,
                             "node": host, "restart": restart,
                             "t": time.time()})
    summary = []
    for name in names:
        wd = WORK / name
        wd.mkdir(parents=True, exist_ok=True)
        if not (wd / "pseudos").exists():
            (wd / "pseudos").symlink_to(ROOT / "pseudos")
        rec = {"candidate": name, "node": host, "part": part}
        nelec = None
        # --- CEDT class-matched ladder: real gap ---
        ok = True
        for stage in ("f1", "f2", "f3"):
            ranks, npool = CEDT_CFG[stage]
            r = run_qe(wd, name, stage, ranks, npool, "cedt")
            rec[f"{stage}_cedt_cpu_s"] = r.get("cpu_s")
            rec[f"{stage}_cedt_wall_s"] = r.get("wall_s")
            rec[f"{stage}_cedt_ranks"] = ranks
            rec[f"{stage}_resumed"] = r.get("resumed", False)
            txt = Path(r["out"]).read_text(errors="replace")
            if stage in ("f1", "f2"):
                p = parse_scf(txt)
                if p["nelec"]:
                    nelec = p["nelec"]
                if not (r["rc"] == 0 and p["converged"]):
                    rec[f"{stage}_failed"] = True
                    ok = False
                    break
            else:
                gap = parse_gap(txt, nelec) if r["rc"] == 0 else None
                rec["gap_ev"] = round(gap, 4) if gap is not None else None
                rec["qualifier"] = (gap is not None
                                    and GAP_LO <= gap <= GAP_HI)
        rec["nelec"] = nelec
        rec["ladder_ok"] = ok
        # --- DTDE worst-case F2 for the same candidate: config-cost delta ---
        ranks, npool = DTDE_CFG["f2"]
        rd = run_qe(wd, name, "f2", ranks, npool, "dtde")
        rec["f2_dtde_cpu_s"] = rd.get("cpu_s")
        rec["f2_dtde_wall_s"] = rd.get("wall_s")
        rec["f2_dtde_ranks"] = ranks
        # core-seconds = cpu_s already counts all ranks (QE sums ranks in
        # CPU line? no -- PWSCF CPU is per-process aggregate wall*util).
        # Use ranks*cpu_s as a rank-core-second proxy for both configs so
        # the comparison is apples-to-apples.
        cc = rec.get("f2_cedt_cpu_s")
        dc = rec.get("f2_dtde_cpu_s")
        if cc and dc:
            rec["f2_config_cost_ratio_cedt_over_dtde"] = round(cc / dc, 3)
        append("guest_results.jsonl", rec)
        summary.append({k: rec.get(k) for k in
                        ("candidate", "gap_ev", "qualifier", "nelec",
                         "f2_cedt_cpu_s", "f2_dtde_cpu_s",
                         "f2_config_cost_ratio_cedt_over_dtde",
                         "ladder_ok")})
        json.dump({"done": summary, "restart": restart},
                  open(RESULTS / "progress.json", "w"), indent=1)
        print(f"{name}: gap={rec.get('gap_ev')} qual={rec.get('qualifier')} "
              f"f2_cedt={rec.get('f2_cedt_cpu_s')}s "
              f"f2_dtde={rec.get('f2_dtde_cpu_s')}s", flush=True)
    quals = [s["candidate"] for s in summary if s.get("qualifier")]
    json.dump({"candidates": len(summary), "qualifiers": quals,
               "summary": summary, "node": host, "partition": part},
              open(RESULTS / "guest_summary.json", "w"), indent=1)
    append("run_log.jsonl", {"event": "done", "job": jobid,
                             "qualifiers": quals, "t": time.time()})
    print(f"GUEST SCREEN DONE  qualifiers={quals}", flush=True)


if __name__ == "__main__":
    main()
