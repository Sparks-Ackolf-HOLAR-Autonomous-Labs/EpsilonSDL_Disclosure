#!/usr/bin/env python3
"""Task 6 (2026-09-08): re-grade the 1,000-world hard-cap
grid under both governance options:

  Option A - relax the H reservation margin (labels/nh uplift 15% ->
             10% / 5% / 0%, and failure tolerance 0.02 -> 0.04).
  Option B - lower the 0.90 win-win acceptance threshold (report, per
             contract, the highest threshold at which it would be
             accepted, at 0.80/0.70/0.60/0.50).

Plus the combination package suggested by the ceiling diagnosis
(../ceiling_diagnosis/): re-express the R gain on the execution layer
(labels/nh, the metric information exchange CAN move) instead of
discovery time (dominated by scientific noise no contract can trade).

Pure re-analysis of prior_predictive/results/raw_results_hardcap.json.gz
(per-world condition summaries); no new simulation. Simulated units.
"""
import gzip
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RAW = HERE.parent / "prior_predictive" / "results" / \
    "raw_results_hardcap.json.gz"
C_CANDS = 30
LIMITS = dict(r_mi_auc=0.60, r_comp_adv=0.10, r_id_acc_inc=0.05,
              h_tel_auc=0.60, h_hw_adv=0.10, h_rank_corr=0.20)


def load():
    recs = json.load(gzip.open(RAW))
    worlds = {}
    for r in recs:
        worlds.setdefault((r["card"], r["world"]), {})[r["condition"]] = r
    return worlds


def leak_ok(r):
    return (r["r_mi_auc"] <= LIMITS["r_mi_auc"]
            and r["r_comp_adv"] <= LIMITS["r_comp_adv"]
            and r["r_id_acc"] <= 1 / C_CANDS + LIMITS["r_id_acc_inc"]
            and r["h_tel_auc"] <= LIMITS["h_tel_auc"]
            and r["h_hw_adv"] <= LIMITS["h_hw_adv"]
            and r["h_rank_corr"] <= LIMITS["h_rank_corr"])


def grade(worlds, g_r_time=0.80, h_labels=1.15, h_fail=0.02,
          r_metric="time"):
    """Recompute per-condition P(win-win) under modified margins.
    r_metric='time' -> preregistered gainA/gainB on nh-to-first;
    r_metric='exec' -> R gain on labels/nh uplift >= (1 - g_r_time)
    interpretation is: g_r_time is the required ratio (0.80 = 20% less).
    """
    counts = {}
    for (card, wid), conds in worlds.items():
        base = conds.get("DTDE_P4")
        if base is None:
            continue
        for name, r in conds.items():
            if r_metric == "time":
                gainA = (r["mean_nh_first"] <= g_r_time
                         * base["mean_nh_first"]
                         and r["found_rate"] >= base["found_rate"] - 1e-9)
                gainB = r["mean_qual"] >= base["mean_qual"] + 1.0
                r_ok = ((gainA or gainB)
                        and r["validity"] >= base["validity"] - 0.01)
            else:  # execution-layer R gain: cheaper valid science per nh
                uplift = 2.0 - g_r_time  # 0.80 -> 1.20 required ratio
                r_ok = (r["labels_per_nh"] >= uplift * base["labels_per_nh"]
                        and r["found_rate"] >= base["found_rate"] - 1e-9
                        and r["validity"] >= base["validity"] - 0.01)
            h_ok = (r["labels_per_nh"] >= h_labels * base["labels_per_nh"]
                    and r["fail_rate"] <= base["fail_rate"] + h_fail
                    and r["memfail_p95"] <= base["memfail_p95"] + 1e-9)
            ww = r_ok and h_ok and leak_ok(r)
            c = counts.setdefault(name, dict(n=0, ww=0, r=0, h=0, leak=0))
            c["n"] += 1
            c["ww"] += ww
            c["r"] += r_ok
            c["h"] += h_ok
            c["leak"] += leak_ok(r)
    return {name: dict(p_win_win=c["ww"] / c["n"], p_r=c["r"] / c["n"],
                       p_h=c["h"] / c["n"], p_leak=c["leak"] / c["n"],
                       n=c["n"])
            for name, c in counts.items()}


def main():
    worlds = load()
    out = {}
    # frozen baseline for reference
    out["frozen"] = grade(worlds)
    # Option A sweeps
    for hl in (1.10, 1.05, 1.00):
        out[f"optA_hlabels_{hl:.2f}"] = grade(worlds, h_labels=hl)
    out["optA_hfail_0.04"] = grade(worlds, h_fail=0.04)
    out["optA_hlabels_1.05_hfail_0.04"] = grade(
        worlds, h_labels=1.05, h_fail=0.04)
    # combination package: execution-layer R metric + relaxed margins
    out["exec_gR20"] = grade(worlds, r_metric="exec", g_r_time=0.80)
    out["exec_gR10"] = grade(worlds, r_metric="exec", g_r_time=0.90)
    out["package_exec_gR10_hlabels_1.05"] = grade(
        worlds, r_metric="exec", g_r_time=0.90, h_labels=1.05,
        h_fail=0.04)
    # Option B: acceptance-threshold table over the frozen grading
    thresholds = [0.90, 0.80, 0.70, 0.60, 0.50]
    accept = {}
    for name, d in out["frozen"].items():
        accept[name] = dict(
            p_win_win=d["p_win_win"],
            accepted_at=[t for t in thresholds if d["p_win_win"] >= t])
    out["optB_threshold_table"] = accept
    json.dump(out, open(HERE / "governance_regrade.json", "w"), indent=1)

    def top(d, k=4):
        return sorted(((n, v["p_win_win"]) for n, v in d.items()
                       if n != "CTCE_P0"), key=lambda t: -t[1])[:k]

    for key in out:
        if key == "optB_threshold_table":
            continue
        print(f"{key}: " + ", ".join(f"{n}={p:.3f}"
                                     for n, p in top(out[key])))


if __name__ == "__main__":
    main()
