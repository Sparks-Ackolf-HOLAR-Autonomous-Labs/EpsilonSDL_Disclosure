#!/usr/bin/env python3
"""Metric redesign study (2026-09-08):

  Does changing the metric fix the noise-to-signal ratio?

The ceiling diagnosis showed the preregistered R gain (20% fewer
node-hours to first qualifier) is priced against a quantity that is ~55%
scientific noise no contract can trade. This study asks whether a
*redesigned* R metric recovers the signal, two ways:

1. SNR, measured directly. For each world, DTDE-P4 (baseline) and
   CEDT-P4 (minimal viable contract) run on identical seeds/noise
   fields (CRN). For each candidate metric, the per-world paired
   t-statistic  t = mean_s(delta) / (sd_s(delta)/sqrt(S))  is the
   signal-to-noise the metric actually delivers with 30 paired seeds.
2. Feasibility. Each candidate R-metric design is graded into
   P(R gain), and into P(win-win) with the frozen and the renegotiated
   ("package") H margins + all six leakage limits, on:
     (a) the wide (base) prior at x1 task scale, and
     (b) the measurement-informed posterior card (Stage-2 + pilot fits)
         at x100 scale — the operating point the scale validation
         located in real units.

Candidate R metrics (all keep the validity guard >= base - 0.01):
  T20   frozen: mean nh-to-first <= 0.80 x base, found no worse
  T10   renegotiated: <= 0.90 x base
  REG20 oracle-regret: mean (nh_first - oracle) <= 0.80 x base regret —
        subtracts the irreducible spend a nature oracle would pay
  PW60  paired-seed win-rate: contract beats base on nh_first (any
        margin) in >= 60% of the 30 paired seeds — a sign test that
        cancels common scientific noise instead of demanding a margin
  EX10 / EX15  execution layer: labels/nh uplift >= 1.10 / 1.15
  QY05  qualifier yield: mean qualifiers at budget >= base + 0.5

All node-hours are simulated units.
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
sys.path.insert(0, str(HERE.parent / "ceiling_diagnosis"))
os.environ.setdefault("MPT_HARD_CAP", "1")
import simulator as sim  # noqa: E402
from diagnose_ceiling import oracle_nh_first  # noqa: E402

FIT = json.load(open(HERE.parent / "stage2_twin_fit" / "twin_fit.json"))
PFIT = json.load(open(HERE.parent / "pilot" / "results" /
                      "pilot_fit.json"))
A_MEAS = FIT["measured_fit"]["A"]
AF_EMP = np.array([FIT["min_call_node_hours"], A_MEAS["F1"], A_MEAS["F2"],
                   A_MEAS["F3"], A_MEAS["F4"] + 0.1 * A_MEAS["F2"]])
P_E = FIT["measured_fit"]["p_e"]
SD_LOG = FIT["measured_fit"]["resid_sd_log"]

sim.PRIOR_CARDS["posterior"] = dict(
    s_mu=PFIT["parallel_efficiency_exponent_s"], s_sd=0.05,
    quirk_sd=PFIT["quirk_sd_log"], pm_lo=0.05, pm_hi=0.30,
    burst_lo=0.05, burst_hi=0.25, beta0_mu=-4.2, beta0_sd=0.4, atk=1.0)

SCALE = 1.0
_orig_sample = sim.sample_world
_orig_mem = sim.mem_per_node


def sample_world_post(card, wid):
    w = _orig_sample(card, wid)
    rng = np.random.default_rng(
        zlib.crc32(f"post:{card}:{int(wid)}".encode()))
    w["A"] = AF_EMP * SCALE * np.exp(rng.normal(0, SD_LOG))
    w["p_e"] = np.clip(rng.normal(P_E, 0.1), 0.9, 1.5)
    w["memq"] = float(np.exp(rng.normal(0, 0.05)))
    w["rho"] = np.exp(rng.normal(0, 0.15, sim.C))
    return w


def mem_per_node_post(w, fid):
    grow = (sim.NK[fid] / 36.0) ** 0.3
    m = (2.1 * (sim.CAND["nelec"][:, None] / 38.0) ** 0.5 * grow
         * w["memq"] * w["rho"][:, None]
         / (sim.C_NODES[None, :] * sim.C_POOLS[None, :] ** 0.4)) + 0.1
    return m * SCALE ** 0.5


def ctce_p0():
    c = sim.Contract("P1")
    c.level, c.gamma, c.cost_sd = "P0", 1.0, 0.0
    c.classes, c.nclasses = np.arange(sim.C), sim.C
    return c


def tstat(delta):
    sd = delta.std(ddof=1)
    if sd < 1e-12:
        return 0.0
    return float(delta.mean() / (sd / np.sqrt(len(delta))))


def leak_ok(r):
    L = sim.LIMITS
    return bool(np.mean(r["r_mi_auc"]) <= L["r_mi_auc"]
                and np.mean(r["r_comp_adv"]) <= L["r_comp_adv"]
                and np.mean(r["r_id_acc"]) <= 1 / sim.C
                + L["r_id_acc_inc"]
                and np.mean(r["h_tel_auc"]) <= L["h_tel_auc"]
                and np.mean(r["h_hw_adv"]) <= L["h_hw_adv"]
                and np.mean(r["h_rank_corr"]) <= L["h_rank_corr"])


def run_one(args):
    card, wid = args
    w = sim.sample_world(card, wid)
    base = sim.run_campaign(w, "DTDE", sim.Contract("P4"))
    cedt = sim.run_campaign(w, "CEDT", sim.Contract("P4"))
    nh_o = oracle_nh_first(w)

    d = {"world": wid}
    # --- per-seed paired SNR (t-stats; sign: improvement > 0) ---
    d["t_nh_first"] = tstat(base["nh_first"] - cedt["nh_first"])
    d["t_regret"] = tstat((base["nh_first"] - nh_o)
                          - (cedt["nh_first"] - nh_o))  # == t_nh_first
    d["t_labels_nh"] = tstat(cedt["labels_per_nh"] - base["labels_per_nh"])
    d["t_qual"] = tstat(cedt["qual_count"] - base["qual_count"])
    d["t_fail"] = tstat(base["fail_rate"] - cedt["fail_rate"])
    # CRN noise cancellation: how much of the seed variance is shared
    if base["nh_first"].std() > 1e-9 and cedt["nh_first"].std() > 1e-9:
        d["rho_pair_nhfirst"] = float(np.corrcoef(
            base["nh_first"], cedt["nh_first"])[0, 1])
    else:
        d["rho_pair_nhfirst"] = 1.0
    # noise composition of the frozen metric (per-seed, this world)
    d["cv_nh_first_base"] = float(base["nh_first"].std(ddof=1)
                                  / max(base["nh_first"].mean(), 1e-9))
    d["oracle_frac"] = float(nh_o.mean()
                             / max(base["nh_first"].mean(), 1e-9))

    # --- metric battery grading ---
    v_ok = cedt["validity"].mean() >= base["validity"].mean() - 0.01
    f_ok = cedt["found"].mean() >= base["found"].mean() - 1e-9
    mb, mc = base["nh_first"].mean(), cedt["nh_first"].mean()
    reg_b = max(mb - nh_o.mean(), 1e-9)
    reg_c = mc - nh_o.mean()
    gains = {
        "T20": mc <= 0.80 * mb and f_ok,
        "T10": mc <= 0.90 * mb and f_ok,
        "REG20": reg_c <= 0.80 * reg_b and f_ok,
        "PW60": (cedt["nh_first"] < base["nh_first"]).mean() >= 0.60
        and f_ok,
        "EX10": cedt["labels_per_nh"].mean()
        >= 1.10 * base["labels_per_nh"].mean() and f_ok,
        "EX15": cedt["labels_per_nh"].mean()
        >= 1.15 * base["labels_per_nh"].mean() and f_ok,
        "QY05": cedt["qual_count"].mean()
        >= base["qual_count"].mean() + 0.5,
    }
    d["gains"] = {k: bool(v and v_ok) for k, v in gains.items()}
    # H margins on the same paired run
    lb = max(base["labels_per_nh"].mean(), 1e-9)
    lr = cedt["labels_per_nh"].mean() / lb
    dfail = cedt["fail_rate"].mean() - base["fail_rate"].mean()
    dmem = (np.percentile(cedt["memfail_rate"], 95)
            - np.percentile(base["memfail_rate"], 95))
    d["h_frozen"] = bool(lr >= 1.15 and dfail <= 0.02 and dmem <= 1e-9)
    d["h_package"] = bool(lr >= 1.05 and dfail <= 0.04 and dmem <= 1e-9)
    d["leak_ok"] = leak_ok(cedt)
    return d


def grade(rows):
    out = {}
    for m in rows[0]["gains"]:
        pr = np.mean([r["gains"][m] for r in rows])
        wwf = np.mean([r["gains"][m] and r["h_frozen"] and r["leak_ok"]
                       for r in rows])
        wwp = np.mean([r["gains"][m] and r["h_package"] and r["leak_ok"]
                       for r in rows])
        out[m] = dict(p_r_gain=float(pr), p_ww_frozen=float(wwf),
                      p_ww_package=float(wwp))
    out["_h"] = dict(
        p_h_frozen=float(np.mean([r["h_frozen"] for r in rows])),
        p_h_package=float(np.mean([r["h_package"] for r in rows])),
        p_leak_ok=float(np.mean([r["leak_ok"] for r in rows])))
    out["_snr"] = {k: dict(
        median=float(np.median([r[k] for r in rows])),
        q10=float(np.percentile([r[k] for r in rows], 10)),
        q90=float(np.percentile([r[k] for r in rows], 90)))
        for k in ("t_nh_first", "t_labels_nh", "t_qual", "t_fail",
                  "rho_pair_nhfirst", "cv_nh_first_base", "oracle_frac")}
    return out


def main():
    global SCALE
    worlds = int(os.environ.get("MRS_WORLDS", "300"))
    procs = int(os.environ.get("MRS_PROCS", os.cpu_count()))
    out = {"worlds": worlds}

    # (a) wide prior, x1, original twin
    with Pool(procs) as p:
        rows = p.map(run_one, [("base", i) for i in range(worlds)],
                     chunksize=4)
    out["wide_prior_x1"] = grade(rows)

    # (b) posterior card, x100 measured twin, per-sbatch overhead
    SCALE = 100.0
    sim.sample_world = sample_world_post
    sim.mem_per_node = mem_per_node_post
    sim.OVERHEAD_NH = 0.02
    with Pool(procs) as p:
        rows = p.map(run_one, [("posterior", i) for i in range(worlds)],
                     chunksize=4)
    out["posterior_x100"] = grade(rows)

    json.dump(out, open(HERE / "metric_study.json", "w"), indent=1)
    for setting in ("wide_prior_x1", "posterior_x100"):
        g = out[setting]
        print(f"\n== {setting} (CEDT-P4 vs DTDE-P4, {worlds} worlds) ==")
        print(f"{'metric':6s} {'P(Rgain)':>9} {'P(ww froz)':>11} "
              f"{'P(ww pkg)':>10}")
        for m in ("T20", "T10", "REG20", "PW60", "EX10", "EX15", "QY05"):
            v = g[m]
            print(f"{m:6s} {v['p_r_gain']:9.3f} {v['p_ww_frozen']:11.3f} "
                  f"{v['p_ww_package']:10.3f}")
        print("H: frozen %.3f package %.3f leak %.3f" % (
            g["_h"]["p_h_frozen"], g["_h"]["p_h_package"],
            g["_h"]["p_leak_ok"]))
        s = g["_snr"]
        print("SNR med t: nh_first %.2f labels/nh %.2f qual %.2f "
              "fail %.2f | rho_pair %.2f" % (
                  s["t_nh_first"]["median"], s["t_labels_nh"]["median"],
                  s["t_qual"]["median"], s["t_fail"]["median"],
                  s["rho_pair_nhfirst"]["median"]))


if __name__ == "__main__":
    main()
