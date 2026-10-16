#!/usr/bin/env python3
"""Findings 1-2 re-evaluation (question of 2026-09-08):

  "If even the full-information ceiling rarely achieves the demanded
   speedup, something in the setup is wrong."

This script tests that hypothesis by decomposing DTDE's node-hour spend to
first qualifying candidate into three parts:

  nh_first(DTDE) = irreducible + science_gap + exec_gap

  * irreducible  — a NATURE ORACLE that knows the true world (which
    candidates qualify, true costs, true failure draws) and runs the
    minimum admissible ladder (F1->F4, sequential-fidelity rule) on the
    cheapest true qualifier with per-attempt optimal configs. No
    information contract can beat this: it prices what is left when ALL
    uncertainty (both parties' AND nature's) is gone.
  * science_gap  — nh_first(CTCE-P0) - nh_first(oracle): spend caused by
    scientific uncertainty (not knowing which candidate qualifies).
    CTCE-P0 shares everything R and H know, but neither party knows
    nature, so NO R<->H contract can recover this part.
  * exec_gap     — nh_first(DTDE) - nh_first(CTCE-P0): spend caused by
    the parties not sharing what they DO know (config choice, cost
    estimates). This is the ONLY part an information contract can sell.

If exec_gap / nh_first(DTDE) < g_R = 20% in most worlds, the preregistered
R reservation gain demands savings from a component larger than the whole
tradable surface -- a metric-calibration fact, not a simulator bug.

Also grades alternative R-gain metric designs on the same worlds
(execution-layer metrics vs discovery-time metrics) to show which metric
family the contract CAN move. All node-hours are simulated units.
"""
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "prior_predictive"))
os.environ.setdefault("MPT_HARD_CAP", "1")
import simulator as sim  # noqa: E402


def oracle_nh_first(w):
    """Minimum admissible spend to first qualifier per seed (S,).

    Knows w['qual'], true costs, and the failure noise fields. Must still
    obey the ladder rules: F1..F4 sequential, one job per round, retries
    consume the same per-(cand,fid,attempt) noise draws as the campaigns,
    OVERHEAD_NH per attempt, dead after 4 failed attempts at one fidelity.
    """
    qual_idx = np.where(w["qual"])[0]
    out = np.full(sim.S, sim.BUDGET_NH)
    if len(qual_idx) == 0:
        return out
    wk = np.stack([sim.base_work(w, f) for f in range(sim.FIDS)])
    eff = np.stack([sim.eff_matrix(w, f) for f in range(sim.FIDS)])
    mem = np.stack([sim.mem_per_node(w, f) for f in range(sim.FIDS)])
    hard = mem > sim.NODE_MEM_GB
    headroom = np.clip(sim.NODE_MEM_GB / mem, 0.2, 20.0)
    for s in range(sim.S):
        best = sim.BUDGET_NH
        for i in qual_idx:
            nh, t, failed_out = 0.0, 0, False
            for f in (1, 2, 3, 4):
                for att in range(4):
                    kap = w["kappa"][s, min(t, sim.T - 1)]
                    pf = 1.0 / (1.0 + np.exp(-(w["beta0"]
                          + 1.2 * (kap - 0.3) + 0.8 * sim.C_AGG
                          - 1.5 * np.log(headroom[f, i]))))
                    true_nh = (wk[f, i] / eff[f, i]
                               * (1 + kap * sim.C_IO))
                    score = true_nh * (1 + 2 * pf) + 1e3 * hard[f, i]
                    j = int(np.argmin(score))
                    noise = w["nh_noise"][s, i, f, min(att, 3)]
                    cost = true_nh[j] * noise
                    fail = (w["fail_u"][s, i, f, min(att, 3)] < pf[j]) \
                        or hard[f, i, j]
                    nh += (0.45 * cost if fail else cost) + sim.OVERHEAD_NH
                    t += 1
                    if not fail:
                        break
                else:
                    failed_out = True
                if failed_out or nh >= best:
                    break
            if not failed_out and nh < best:
                best = nh
        out[s] = best
    return out


def run_one(args):
    card, wid = args
    w = sim.sample_world(card, wid)
    ctce = sim.Contract("P1")
    ctce.level, ctce.gamma, ctce.cost_sd = "P0", 1.0, 0.0
    ctce.classes, ctce.nclasses = np.arange(sim.C), sim.C
    r_ctce = sim.run_campaign(w, "CTCE", ctce)
    r_dtde = sim.run_campaign(w, "DTDE", sim.Contract("P4"))
    nh_o = oracle_nh_first(w)
    d = {}
    d["oracle"] = float(nh_o.mean())
    d["ctce"] = float(r_ctce["nh_first"].mean())
    d["dtde"] = float(r_dtde["nh_first"].mean())
    d["exec_gap_frac"] = float(np.clip(
        (d["dtde"] - d["ctce"]) / max(d["dtde"], 1e-9), -1, 1))
    d["science_gap_frac"] = float(np.clip(
        (d["ctce"] - d["oracle"]) / max(d["dtde"], 1e-9), -1, 1))
    d["irreducible_frac"] = float(d["oracle"] / max(d["dtde"], 1e-9))
    # per-seed paired win (metric-design alternative to the mean ratio)
    d["paired_seed_winrate"] = float(
        (r_ctce["nh_first"] <= 0.8 * r_dtde["nh_first"]).mean())
    # spend decomposition of the DTDE campaign
    d["overhead_frac_dtde"] = float(
        (r_dtde["attempts"] * sim.OVERHEAD_NH
         / np.maximum(r_dtde["nh_used"], 1e-9)).mean())
    # execution-layer metrics the contract CAN move
    d["labels_per_nh_ratio"] = float(
        r_ctce["labels_per_nh"].mean()
        / max(r_dtde["labels_per_nh"].mean(), 1e-9))
    d["fail_dtde"] = float(r_dtde["fail_rate"].mean())
    d["fail_ctce"] = float(r_ctce["fail_rate"].mean())
    d["found_dtde"] = float(r_dtde["found"].mean())
    d["found_ctce"] = float(r_ctce["found"].mean())
    d["n_true_qual"] = int(w["qual"].sum())
    # original preregistered gainA on this world
    d["gainA_ctce"] = float(d["ctce"] <= 0.8 * d["dtde"]
                            and d["found_ctce"] >= d["found_dtde"] - 1e-9)
    return d


def main():
    worlds = int(os.environ.get("DIAG_WORLDS", "300"))
    procs = os.cpu_count()
    tasks = [("base", wid) for wid in range(worlds)]
    with Pool(procs) as p:
        rows = p.map(run_one, tasks, chunksize=4)
    K = list(rows[0].keys())
    agg = {k: dict(mean=float(np.mean([r[k] for r in rows])),
                   median=float(np.median([r[k] for r in rows])),
                   q10=float(np.percentile([r[k] for r in rows], 10)),
                   q90=float(np.percentile([r[k] for r in rows], 90)))
           for k in K}
    summary = dict(
        worlds=worlds, card="base",
        p_exec_gap_ge_20pct=float(np.mean(
            [r["exec_gap_frac"] >= 0.20 for r in rows])),
        p_exec_gap_ge_10pct=float(np.mean(
            [r["exec_gap_frac"] >= 0.10 for r in rows])),
        p_gainA_ctce=float(np.mean([r["gainA_ctce"] for r in rows])),
        p_labels_ratio_ge_115=float(np.mean(
            [r["labels_per_nh_ratio"] >= 1.15 for r in rows])),
        agg=agg)
    (HERE / "results").mkdir(exist_ok=True)
    json.dump(dict(summary=summary, rows=rows),
              open(HERE / "results" / "ceiling_diagnosis.json", "w"),
              indent=1)
    for k in ("irreducible_frac", "science_gap_frac", "exec_gap_frac",
              "overhead_frac_dtde", "labels_per_nh_ratio",
              "paired_seed_winrate"):
        a = agg[k]
        print(f"{k:22s} mean={a['mean']:.3f} med={a['median']:.3f} "
              f"[q10 {a['q10']:.3f}, q90 {a['q90']:.3f}]")
    print(f"P(exec_gap >= 20%) = {summary['p_exec_gap_ge_20pct']:.3f}")
    print(f"P(exec_gap >= 10%) = {summary['p_exec_gap_ge_10pct']:.3f}")
    print(f"P(preregistered gainA, CTCE) = {summary['p_gainA_ctce']:.3f}")
    print(f"P(labels/nh ratio >= 1.15, CTCE) = "
          f"{summary['p_labels_ratio_ge_115']:.3f}")


if __name__ == "__main__":
    main()
