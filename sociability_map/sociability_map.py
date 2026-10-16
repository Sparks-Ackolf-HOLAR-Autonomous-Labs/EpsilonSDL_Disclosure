#!/usr/bin/env python3
"""Finding-4 study (2026-09-08): map "sociability" -- the
value of information exchange -- against its leakage price across task
scale, on the empirically calibrated twin (Stage-2 fit).

For each task-scale multiplier (x measured MX2 ladder cost) and each
contract, compute on paired worlds:

  * sociability value  - what sharing buys: labels/nh uplift vs DTDE-P4
    and node-hour saving to first qualifier vs DTDE-P4;
  * leakage price      - worst-channel utilization u = max_c L_c/limit_c
    (u > 1 means some preregistered limit is breached);
  * feasibility        - P(all six leakage limits hold).

The map answers: at which task scale does it pay to be more "sociable"
(disclose more), and where does the leakage price bite first.

Calibration: measured amplitudes/exponent from ../stage2_twin_fit/
twin_fit.json (p_e = 1.20, per-sbatch overhead 0.02 nh); unidentifiable
params (p_k, eff, contention, failure base) keep priors -- the 81-job
pilot measures those. All node-hours are simulated units.
"""
import json
import os
import sys
import zlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "prior_predictive"))
os.environ.setdefault("MPT_HARD_CAP", "1")
import simulator as sim  # noqa: E402

FIT = json.load(open(HERE.parent / "stage2_twin_fit" / "twin_fit.json"))
A_MEAS = FIT["measured_fit"]["A"]
AF_EMP = np.array([FIT["min_call_node_hours"], A_MEAS["F1"], A_MEAS["F2"],
                   A_MEAS["F3"], A_MEAS["F4"] + 0.1 * A_MEAS["F2"]])
P_E = FIT["measured_fit"]["p_e"]
SD_LOG = FIT["measured_fit"]["resid_sd_log"]
SCALE = 1.0

CONDS = [("DTDE_P4", "DTDE", "P4", None),
         ("CTDE_P2", "CTDE", "P2", None),
         ("CTDE_P3_eps2", "CTDE", "P3", 2.0),
         ("CTDE_P4", "CTDE", "P4", None),
         ("CEDT_P2", "CEDT", "P2", None),
         ("CEDT_P3_eps2", "CEDT", "P3", 2.0),
         ("CEDT_P4", "CEDT", "P4", None),
         ("CTCE_P0", "CTCE", "P0", None)]
CHANNELS = ["r_mi_auc", "r_comp_adv", "r_id_acc",
            "h_tel_auc", "h_hw_adv", "h_rank_corr"]
LIMVALS = dict(r_mi_auc=0.60, r_comp_adv=0.10, r_id_acc=1 / 30 + 0.05,
               h_tel_auc=0.60, h_hw_adv=0.10, h_rank_corr=0.20)
# chance floors per channel so utilization measures excess over chance
FLOOR = dict(r_mi_auc=0.50, r_comp_adv=0.0, r_id_acc=1 / 30,
             h_tel_auc=0.50, h_hw_adv=0.0, h_rank_corr=0.0)

_orig_sample = sim.sample_world


def sample_world_emp(card, wid):
    w = _orig_sample(card, wid)
    rng = np.random.default_rng(
        zlib.crc32(f"emp:{card}:{int(wid)}".encode()))
    w["A"] = AF_EMP * SCALE * np.exp(rng.normal(0, SD_LOG))
    w["p_e"] = np.clip(rng.normal(P_E, 0.1), 0.9, 1.5)
    w["memq"] = float(np.exp(rng.normal(0, 0.05)))
    w["rho"] = np.exp(rng.normal(0, 0.15, sim.C))
    return w


def mem_per_node_emp(w, fid):
    grow = (sim.NK[fid] / 36.0) ** 0.3
    m = (2.1 * (sim.CAND["nelec"][:, None] / 38.0) ** 0.5 * grow
         * w["memq"] * w["rho"][:, None]
         / (sim.C_NODES[None, :] * sim.C_POOLS[None, :] ** 0.4)) + 0.1
    return m * SCALE ** 0.5


def run_one(args):
    card, wid = args
    w = sim.sample_world(card, wid)
    res = {}
    for name, topo, lvl, eps in CONDS:
        contract = sim.Contract(lvl if lvl != "P0" else "P1", eps)
        if lvl == "P0":
            contract.level, contract.gamma, contract.cost_sd = "P0", 1.0, 0.0
            contract.classes, contract.nclasses = np.arange(sim.C), sim.C
        r = sim.run_campaign(w, topo, contract)
        res[name] = dict(
            labels_per_nh=float(np.mean(r["labels_per_nh"])),
            nh_first=float(np.mean(r["nh_first"])),
            found=float(np.mean(r["found"])),
            fail=float(np.mean(r["fail_rate"])),
            **{c: float(np.mean(r[c])) for c in CHANNELS})
    return res


def main():
    global SCALE
    worlds = int(os.environ.get("SOC_WORLDS", "150"))
    scales = [float(s) for s in os.environ.get(
        "SOC_SCALES", "1,3,10,30,100,300,1000").split(",")]
    sim.mem_per_node = mem_per_node_emp
    sim.sample_world = sample_world_emp
    sim.OVERHEAD_NH = 0.02
    out = {}
    for sc in scales:
        SCALE = sc
        with Pool(os.cpu_count()) as p:
            rows = p.map(run_one, [("base", wid) for wid in range(worlds)],
                         chunksize=4)
        agg = {}
        for name, *_ in CONDS:
            base = [r["DTDE_P4"] for r in rows]
            cond = [r[name] for r in rows]
            util = []
            leak_ok = []
            for c_ in cond:
                us = [(c_[ch] - FLOOR[ch])
                      / max(LIMVALS[ch] - FLOOR[ch], 1e-9)
                      for ch in CHANNELS]
                util.append(max(us))
                leak_ok.append(all(c_[ch] <= LIMVALS[ch]
                                   for ch in CHANNELS))
            agg[name] = dict(
                labels_ratio=float(np.mean(
                    [c["labels_per_nh"] / max(b["labels_per_nh"], 1e-9)
                     for c, b in zip(cond, base)])),
                nh_first_saving=float(np.mean(
                    [1 - c["nh_first"] / max(b["nh_first"], 1e-9)
                     for c, b in zip(cond, base)])),
                found=float(np.mean([c["found"] for c in cond])),
                fail=float(np.mean([c["fail"] for c in cond])),
                worst_leak_util=float(np.mean(util)),
                p_leak_ok=float(np.mean(leak_ok)),
                **{ch: float(np.mean([c[ch] for c in cond]))
                   for ch in CHANNELS})
        out[f"scale_{sc:g}"] = agg
        print(f"scale {sc:g}: " + " ".join(
            f"{n}:lr={d['labels_ratio']:.2f},u={d['worst_leak_util']:.2f}"
            for n, d in agg.items() if n in ("CEDT_P2", "CEDT_P4")),
            flush=True)
    json.dump(dict(worlds=worlds, scales=scales, results=out,
                   note="empirically calibrated twin; simulated units"),
              open(HERE / "sociability_map.json", "w"), indent=1)


if __name__ == "__main__":
    main()
