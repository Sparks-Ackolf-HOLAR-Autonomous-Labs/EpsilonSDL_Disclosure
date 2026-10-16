#!/usr/bin/env python3
"""Vacancy-immobility goal in the twin, graded against G1 to G4.

Registered beforehand in ../GOAL_CHANGE.md (P-2026-10-10-G, 10 Oct 2026); run after the
DFT NEB barriers were collected and N1 to N5 passed (../dft_neb/results_dft/grading.json).

Goal: a compound qualifies when it is in the 1.0 to 2.0 eV gap window, passes the
Gamma-phonon check, AND its chalcogen vacancy hop barrier is at least E_min = 1.5 eV
(85 C, 10 years, attempt frequency 1e13 s^-1).

Barriers (decision rule of ../dft_neb/PREDICTION.md):
  * the 7 compounds with a DFT NEB use the PBE climbing-image value, world-to-world
    sd 0.10 eV (NEB numerical spread);
  * the other 23 use the MACE-MP-0 value plus the measured mean DFT - MACE offset
    (registered rule, "mean"), world-to-world sd = sd of the 7 measured offsets.
    Sensitivity ("family"): offset and sd per (metal group, phase) family where at
    least 2 compounds were measured, the mean rule otherwise.
Twin changes (surface.IMMOBILE_FN, surface.PASSRATE_TRAIN; kMC rung from kmc_rung.py):
  * F3 is "F3 plus the vacancy anneal"; its cost factor uses the measured MACE kMC cost
    shifted to the DFT barrier at 1000 K, centred and clipped to 1 decade either way;
  * P2 classes are size bin x barrier bit, the bit being R's own MACE barrier above or
    below the median (R can compute MACE barriers itself; it cannot calibrate them);
  * qualification at F4 also needs immobility; the shared logbook records the
    immobility outcome of each F3 step per class and R weights value by the pass rate.
All campaign numbers are SIMULATED UNITS. Barriers and their spread are measured.
"""
import argparse
import json
import os
import sys
import zlib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FF = HERE.parent
MPT = HERE.parents[1]
sys.path.insert(0, str(MPT / "prior_predictive"))
sys.path.insert(0, str(MPT / "centralization_surface"))
sys.path.insert(0, str(HERE))
import simulator as S  # noqa: E402
import surface as SF  # noqa: E402
import kmc_rung as KR  # noqa: E402

E_MIN = 1.5
KT_1000 = 8.617333e-5 * 1000.0
CARDS = ["base", "strong_coupling", "adversarial"]
WINDOW9 = ["WS2_2H", "MoS2_2H", "WSe2_2H", "MoSe2_2H", "HfS2_1T", "ZrS2_1T",
           "MoTe2_2H", "WTe2_2H", "HfS2_2H"]   # measured 1x1 gap-window compounds

NAMES = S.CAND["names"]
MACE = np.array([KR.NEB[n]["E_hop_eV"] for n in NAMES])
DFT = json.loads((FF / "dft_neb" / "results_dft" / "grading.json").read_text())["table"]
OFF = {k: v["dft"] - v["mace"] for k, v in DFT.items() if v["converged"]}
OFF_MEAN = float(np.mean(list(OFF.values())))
OFF_SD = float(np.std(list(OFF.values()), ddof=1))


def _family(n):
    grp = "g6" if n.startswith(("Mo", "W")) else "g4"
    return f"{grp}_{n.split('_')[1]}"


def barrier_point(rule):
    """Point barrier and world-to-world sd per compound."""
    mu = np.empty(len(NAMES))
    sd = np.empty(len(NAMES))
    fam_off = {}
    if rule == "family":
        for n, o in OFF.items():
            fam_off.setdefault(_family(n), []).append(o)
    for c, n in enumerate(NAMES):
        if n in OFF:
            mu[c], sd[c] = DFT[n]["dft"], 0.10
            continue
        fo = fam_off.get(_family(n), [])
        if len(fo) >= 2:
            mu[c] = MACE[c] + float(np.mean(fo))
            sd[c] = max(float(np.std(fo, ddof=1)), 0.15)
        else:
            mu[c], sd[c] = MACE[c] + OFF_MEAN, OFF_SD
    return mu, sd


def install(rule, classes, clip=1.0):
    mu, sd = barrier_point(rule)
    info = KR.install(clip, classes)            # P2 classes + MACE kMC cost factor
    # shift the kMC cost factor to the DFT barrier (higher barrier, fewer events to the
    # 1 s anneal at 1000 K), re-centre, clip; replaces the MACE-only factor
    lg = {r["candidate"]: np.log10(r["cost_to_t_end_s"]) for r in KR.KMC if r["L"] == 48}
    z = np.array([lg[n] for n in NAMES]) - (mu - MACE) / (KT_1000 * np.log(10.0))
    z = np.clip(z - z.mean(), -clip, clip)
    kfac = 10.0 ** z
    base0 = KR._base_work
    S.base_work = lambda w, fid: base0(w, fid) * kfac if fid == 3 else base0(w, fid)
    orig = S.sample_world

    def sample_world(card, wid):
        w = orig(card, wid)
        rng = np.random.default_rng(zlib.crc32(f"barrier:{card}:{int(wid)}".encode()))
        w["E_hop"] = mu + sd * rng.standard_normal(len(NAMES))
        w["immobile"] = w["E_hop"] >= E_MIN
        return w

    S.sample_world = sample_world
    SF.IMMOBILE_FN = lambda w: w["immobile"]
    info.update(kfac_min=float(kfac.min()), kfac_max=float(kfac.max()))
    return mu, sd, info


def grade_g1(mu):
    hit = [n for n in WINDOW9 if mu[NAMES.index(n)] >= E_MIN]
    return {"window_compounds_immobile": hit, "n": len(hit), "pass": len(hit) >= 2}


def grade_g2(nworld):
    """R^2 for 'immobile or not': R's own size law vs class-keyed logbook asymptote."""
    rel = np.log((S.CAND["nelec"] / 38.0) ** 2.5)
    own, surr = [], []
    for i in range(nworld):
        w = S.sample_world(CARDS[i % 3], i)
        y = w["immobile"].astype(float)
        if y.var() < 1e-9:
            continue
        cls = S.world_classes(w, "P2")
        a = np.polyfit(rel, y, 1)
        own.append(1.0 - np.var(y - np.polyval(a, rel)) / y.var())
        cm = np.array([y[cls == cls[c]].mean() for c in range(len(y))])
        surr.append(1.0 - np.var(y - cm) / y.var())
    o, s_ = float(np.mean(own)), float(np.mean(surr))
    return {"own_size_law_r2": o, "logbook_r2": s_, "diff": s_ - o,
            "worlds_used": len(own), "pass": s_ - o >= 0.10}


def _task(arg):
    wid, passrate, pts = arg
    SF.PASSRATE_TRAIN = passrate
    w = S.sample_world(CARDS[wid % 3], wid)
    base4 = SF.run_mix(w, 0.0, 0.0, "P4")
    out = {}
    for (lvl, tau, eps) in pts:
        out[f"{lvl}|{tau}|{eps}"] = SF.eval_point(SF.run_mix(w, tau, eps, lvl), base4)
    return wid, passrate, out


KEYS = ("win_win", "leak_ok", "r_gain_pw60", "h_gain_package", "labels_ratio",
        "pw_rate", "found_rate", "mean_qual", "r_id_acc", "r_mi_auc", "h_rank_corr")


def transects(nworld, npts, procs):
    g = [round(float(x), 4) for x in np.linspace(0, 1, npts)]
    pts = ([("P2", t, 0.0) for t in g] + [("P2", t, 1.0) for t in g]
           + [("P4", 0.0, e) for e in g])
    tasks = [(wid, pr, pts) for pr in (True, False) for wid in range(nworld)]
    import multiprocessing as mp
    with mp.Pool(procs) as pool:
        res = pool.map(_task, tasks, chunksize=1)
    agg = {}
    for wid, pr, row in res:
        for k, d in row.items():
            agg.setdefault((pr, k), []).append(d)
    out = {}
    for (pr, k), lst in agg.items():
        lvl, tau, eps = k.split("|")
        out[f"{'passrate' if pr else 'no_passrate'}|{k}"] = {
            "level": lvl, "tau": float(tau), "eps": float(eps),
            **{q: float(np.mean([x[q] for x in lst])) for q in KEYS}}
    return out


def grade_g3_g4(tr, npts):
    g = [round(float(x), 4) for x in np.linspace(0, 1, npts)]
    ww = [tr[f"passrate|P2|{t}|0.0"]["win_win"] for t in g]
    best = int(np.argmax(ww))
    g3 = {"tau": g, "win_win": ww, "best_tau": g[best], "rise": ww[best] - ww[0]}
    g3["pass"] = g3["rise"] >= 0.05
    ww4 = [tr[f"passrate|P4|0.0|{e}"]["win_win"] for e in g]
    eps_slope = ww4[-1] - ww4[0]
    g4 = {"eps_slope_P4": eps_slope, "tau_slope_P2": g3["rise"],
          "pass": g3["rise"] <= 0.5 * eps_slope}
    return g3, g4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", choices=["mean", "family"], default="mean")
    ap.add_argument("--classes", choices=["sizebar", "bar"], default="sizebar")
    ap.add_argument("--worlds", type=int, default=120)
    ap.add_argument("--npts", type=int, default=11)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--e-min", type=float, default=1.5,
                    help="barrier floor in eV (1.5 = 85 C/10 y; 1.70 = 125 C/10 y)")
    a = ap.parse_args()
    global E_MIN
    E_MIN = a.e_min
    mu, sd, info = install(a.rule, a.classes)
    res = {"meta": {"rule": a.rule, "classes": a.classes, "worlds": a.worlds,
                    "npts": a.npts, "E_min": E_MIN, "offset_mean": OFF_MEAN,
                    "offset_sd": OFF_SD, "note": "SIMULATED UNITS; barriers measured",
                    **info},
           "barriers": {n: {"mace": float(MACE[c]), "point": float(mu[c]),
                            "sd": float(sd[c]), "dft": n in OFF}
                        for c, n in enumerate(NAMES)}}
    res["G1"] = grade_g1(mu)
    print("G1", res["G1"])
    res["G2"] = grade_g2(a.worlds)
    print("G2", res["G2"])
    tr = transects(a.worlds, a.npts, a.procs)
    res["transects"] = tr
    res["G3"], res["G4"] = grade_g3_g4(tr, a.npts)
    print("G3", {k: v for k, v in res["G3"].items() if k != "tau"})
    print("G4", res["G4"])
    tag = "" if E_MIN == 1.5 else f"_emin{E_MIN:.2f}"
    out = HERE / "results" / f"vacancy_goal_{a.rule}_{a.classes}{tag}.json"
    out.write_text(json.dumps(res, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
