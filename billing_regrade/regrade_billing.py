#!/usr/bin/env python3
"""Item 3 (accounting-model test), analytical half: re-grade the REAL
live comparison (jobs 1919944/1919945, 480 measured QE calls) under
per-core accounting instead of whole-node accounting.

Motivation (paired_comparison_1/RESULTS.md): the live head-to-head found a
+0.5% throughput gain vs the required +5%. The leading hypothesis was
that grn061 is charged as a whole node, so CEDT-P4's main lever --
running F1 on 16 ranks instead of 32 -- frees cores but saves zero
node-hours. The wire log records ranks per job, so the SAME measured
wall times can be re-priced under per-core billing (the accounting used
by shared/co-scheduled partitions, cloud on-demand vCPUs, and most
academic condo "fairshare core-hour" schemes), where freed cores are
real money.

Accounting schemes (charge per job, in 32-core node-hour equivalents so
the DTDE arm is identical across schemes -- it always runs 32 ranks):

  node    : wall_s / 3600                      (what granite actually bills)
  percore : wall_s * ranks / 32 / 3600         (per-core / co-scheduled)

Charge-to-first-qualifier is recomputed by walking each campaign's jobs
in submission order and accumulating charge until the first successful
F3 whose measured PBE gap lands in the preregistered 1.0-2.0 eV window.
The grading is the SAME frozen package as analyze_live.py (PW60 for R;
labels/charge >= 1.05x and fail-rate <= +0.04 for H).

IMPORTANT caveat, stated up front: this is a re-pricing of measured
walls, not a new experiment. It assumes the freed cores are worth their
pro-rata price (true under per-core billing with backfill) and that
walls would be unchanged (true: these are the same physical runs).
What it cannot capture is second-order co-tenant contention on the
freed cores (measured elsewhere at 6-11%, contention_transfer_bench/RESULTS.md).
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
RES = HERE.parent / "paired_comparison_1" / "results"

GAP_LO, GAP_HI = 1.0, 2.0


def charge(job, scheme):
    if scheme == "node":
        return job["wall_s"] / 3600.0
    if scheme == "percore":
        return job["wall_s"] * job["ranks"] / 32.0 / 3600.0
    raise ValueError(scheme)


def campaign_metrics(camp, scheme):
    jobs = sorted(camp["jobs"], key=lambda j: j["t_start"])
    tot = 0.0
    first_q = None
    labels = 0
    fails = 0
    for j in jobs:
        tot += charge(j, scheme)
        if not j["ok"]:
            fails += 1
            continue
        if j["cls"] in ("f2", "f3"):
            labels += 1 if j["cls"] == "f2" else 0
        g = j.get("gap_ev")
        if (first_q is None and j["cls"] == "f3" and g is not None
                and GAP_LO <= g <= GAP_HI):
            first_q = tot
    # match analyze_live.py: no-qualifier campaigns score total spend
    return dict(arm=camp["arm"], seed=camp["seed"], charge=tot,
                first_q=first_q if first_q is not None else tot,
                labels_f2=camp["labels_f2"], fails=camp["fails"],
                calls=camp["calls"])


def grade(pairs):
    wins = sum(c["first_q"] < d["first_q"] for d, c in pairs)
    n = len(pairs)
    pw = wins / n
    p = sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n
    dl = sum(d["labels_f2"] for d, _ in pairs)
    dn = sum(d["charge"] for d, _ in pairs)
    cl = sum(c["labels_f2"] for _, c in pairs)
    cn = sum(c["charge"] for _, c in pairs)
    lr = (cl / cn) / (dl / dn)
    df = sum(d["fails"] for d, _ in pairs) / sum(d["calls"] for d, _ in pairs)
    cf = sum(c["fails"] for _, c in pairs) / sum(c["calls"] for _, c in pairs)
    mean_first_ratio = (sum(c["first_q"] for _, c in pairs)
                        / sum(d["first_q"] for d, _ in pairs))
    return dict(n_pairs=n, pw_rate=pw, wins=wins, sign_test_p=round(p, 4),
                r_pass=bool(pw >= 0.60),
                labels_per_charge_ratio=round(lr, 4),
                mean_first_qual_charge_ratio=round(mean_first_ratio, 4),
                fail_dtde=round(df, 4), fail_cedt=round(cf, 4),
                h_pass=bool(lr >= 1.05 and cf <= df + 0.04),
                dtde_total_charge=round(dn, 4),
                cedt_total_charge=round(cn, 4))


def main():
    camps = [json.loads(x) for x in open(RES / "campaigns.jsonl")]
    out = {}
    for scheme in ("node", "percore"):
        m = {(c["arm"], c["seed"]): campaign_metrics(c, scheme)
             for c in camps}
        seeds = sorted({s for (_, s) in m})
        pairs = [(m[("DTDE", s)], m[("CEDT_P4", s)]) for s in seeds]
        g = grade(pairs)
        g["preregistered_success"] = bool(g["r_pass"] and g["h_pass"])
        out[scheme] = g
        print(f"--- {scheme} accounting ---")
        print(json.dumps(g, indent=1))
    # sanity: what accounting did the recorded campaign "nh" use?
    # (hypothesis: wall_s * ranks / 64 / 3600, i.e. per-core on the
    # 64-core grn061 -- meaning the published live grading was ALREADY
    # per-core, not whole-node)
    chk = max(abs(sum(j["wall_s"] * j["ranks"] / 64 / 3600
                      for j in c["jobs"]) - c["nh"]) for c in camps)
    out["recorded_nh_matches_percore64_max_abs_diff"] = round(chk, 5)
    # decomposition: charge share by class + oracle right-sizing headroom
    for scheme in ("node", "percore"):
        share = {}
        for arm in ("DTDE", "CEDT_P4"):
            tot = sum(charge(j, scheme) for c in camps if c["arm"] == arm
                      for j in c["jobs"])
            share[arm] = {cl: round(sum(
                charge(j, scheme) for c in camps if c["arm"] == arm
                for j in c["jobs"] if j["cls"] == cl) / tot, 4)
                for cl in ("f1", "f2", "f3")}
        out[f"class_charge_share_{scheme}"] = share
    # per-class rank/wall table for the mechanism explanation
    from collections import defaultdict
    tab = defaultdict(list)
    for c in camps:
        for j in c["jobs"]:
            tab[(j["arm"], j["cls"], j["ranks"], j["npool"])].append(
                j["wall_s"])
    out["config_table"] = [
        dict(arm=a, cls=cl, ranks=r, npool=np_, n=len(v),
             mean_wall_s=round(sum(v) / len(v), 1))
        for (a, cl, r, np_), v in sorted(tab.items())]
    # oracle right-sizing bounds (per-core accounting). Two observed
    # configs exist per class (DTDE's 32/nk1 and CEDT's rate card). For
    # the DTDE workload composition, price three counterfactual configs:
    #   class-best : per class, the config with lower median per-core
    #                charge across all candidates -- achievable with P4
    #                info only (calc class is disclosed).
    #   job-best   : per (candidate, class), the cheaper of the two
    #                observed configs -- requires per-candidate
    #                disclosure; the gap over class-best is the measured
    #                value of candidate-specific information here.
    med = defaultdict(dict)   # (cand, cls) -> {arm: median percore charge}
    for c in camps:
        for j in c["jobs"]:
            med[(j["candidate"], j["cls"])].setdefault(
                c["arm"], []).append(charge(j, "percore"))
    med = {k: {a: sorted(v)[len(v) // 2] for a, v in d.items()}
           for k, d in med.items()}
    counts = defaultdict(int)  # DTDE workload composition
    for c in camps:
        if c["arm"] != "DTDE":
            continue
        for j in c["jobs"]:
            counts[(j["candidate"], j["cls"])] += 1
    base = sum(n * med[k]["DTDE"] for k, n in counts.items()
               if "DTDE" in med[k])
    # class-best decision from pooled medians
    cls_tot = defaultdict(lambda: defaultdict(float))
    for (cand, cl), d in med.items():
        for a, v in d.items():
            cls_tot[cl][a] += v
    cls_best = {cl: min(d, key=d.get) for cl, d in cls_tot.items()}
    cb = sum(n * med[k].get(cls_best[k[1]], med[k]["DTDE"])
             for k, n in counts.items())
    jb = sum(n * min(med[k].values()) for k, n in counts.items())
    out["oracle_percore"] = dict(
        dtde_charge=round(base, 4),
        class_best_config=cls_best,
        class_best_charge=round(cb, 4),
        class_best_saving_pct=round(100 * (1 - cb / base), 2),
        job_best_charge=round(jb, 4),
        job_best_saving_pct=round(100 * (1 - jb / base), 2),
        candidate_info_extra_pct=round(100 * (cb - jb) / base, 2))
    print(json.dumps(out["oracle_percore"], indent=1))
    json.dump(out, open(HERE / "billing_regrade.json", "w"), indent=1)
    print("wrote", HERE / "billing_regrade.json")


if __name__ == "__main__":
    main()
