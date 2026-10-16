#!/usr/bin/env python3
"""Brokered booking among research groups (level Xb; predictions in BROKER_PREDICTION.md).

Reuses the groups, lists, measured inputs, worlds, seeds and grading of peer_exchange.py.
Runs X0 (baseline), X1c (public claims, for comparison) and Xb on the same campaigns.
"""
import argparse
import json
import zlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import peer_exchange as P

LEVELS = ["X0", "X1c", "Xb"]


def run_xb(lists, gap_ests, budgets, world, cost, e_min):
    gs = [P.Group(l, ge, b) for l, ge, b in zip(lists, gap_ests, budgets)]
    for g in gs:
        g.signals = []                       # (compound, group that computed it)
    store = {}                               # (c, kind) -> (value, group)

    def receive(g, c, kind, val):
        if kind == "gap":
            g.gap.setdefault(c, val)
        elif c not in g.bar:
            g.bar[c] = val
            g.pool_n[P.FAM[c]] += 1
            g.pool_pass[P.FAM[c]] += val >= e_min

    for rnd in range(200):
        moved, booked, waiting = False, {}, []
        order = range(len(gs)) if rnd % 2 == 0 else reversed(range(len(gs)))
        for gi in order:
            g = gs[gi]
            skip = set()
            for _ in range(2 * P.NC):
                st = g.next_step(e_min, cost, skip)
                if st is None:
                    break
                c, kind = st
                if (c, kind) in store:                       # already computed
                    val, src = store[(c, kind)]
                    receive(g, c, kind, val)
                    g.signals.append((c, src))
                    g.check_first(e_min)
                    continue
                if (c, kind) in booked:                      # booked this round
                    waiting.append((gi, c, kind))
                    g.signals.append((c, booked[(c, kind)]))
                    skip.add(c)
                    continue
                ck = cost[0][c] if kind == "gap" else cost[1][c]
                if g.spend + ck > g.budget:
                    break
                moved = True
                booked[(c, kind)] = gi
                g.spend += ck
                if kind == "gap":
                    val = P.GAPS[c] if np.isfinite(P.GAPS[c]) else -1.0
                    g.gap[c] = val
                else:
                    val = world[c]
                    g.bar[c] = val
                    g.fam_n[P.FAM[c]] += 1
                    g.fam_pass[P.FAM[c]] += val >= e_min
                store[(c, kind)] = (val, gi)
                g.own_steps.append((c, kind))
                g.check_first(e_min)
                break
        for gi, c, kind in waiting:
            if (c, kind) in store:
                receive(gs[gi], c, kind, store[(c, kind)][0])
                gs[gi].check_first(e_min)
        if not moved and not waiting:
            break
    return gs


def leak_xb(gs, i, attackers):
    g = gs[i]
    truth = np.zeros(P.NC, bool)
    truth[list(g.lst)] = True
    silent = [j for j in range(len(gs)) if j not in attackers]
    seen = np.zeros(P.NC)
    for a in attackers:
        for c, src in gs[a].signals:
            if src in silent:
                seen[c] = max(seen[c], 1.0 / len(silent))
    auc = P.auc(seen, truth)
    fam_counts = np.bincount(P.FAM[list(g.lst)], minlength=len(P.FAMS))
    top = set(np.flatnonzero(fam_counts == fam_counts.max()))
    fam_score = np.array([seen[P.FAM == f].sum() for f in range(len(P.FAMS))])
    guess = int(np.argmax(fam_score)) if fam_score.max() > 0 else -1
    prior_guess = int(np.argmax(np.bincount(P.FAM, minlength=len(P.FAMS))))
    return auc, float(guess in top), float(prior_guess in top)


def one_world(args):
    wid, n, o, e_min, asym, rule, nseed = args
    mu, sd = P.V.barrier_point(rule)
    rng_w = np.random.default_rng(zlib.crc32(f"pw:{rule}:{wid}".encode()))
    bar = mu + sd * rng_w.standard_normal(P.NC)
    out = {lv: {k: [] for k in ("first", "auc_pool", "auc_peer", "fam_pool", "fam_peer",
                                "fam_prior", "q")} for lv in LEVELS}
    for s in range(nseed):
        rng = np.random.default_rng(zlib.crc32(f"ps:{wid}:{n}:{o}:{s}".encode()))
        lists = P.make_lists(rng, n, o)
        g0 = np.where(np.isfinite(P.GAPS), P.GAPS, 0.0)
        gap_ests = [g0 + P.GAP_SD * rng.standard_normal(P.NC) for _ in range(n)]
        cost = (P.CGAP * np.exp(P.COST_SD * rng.standard_normal(P.NC)),
                P.CNEB * np.exp(P.COST_SD * rng.standard_normal(P.NC)))
        budgets = [P.BUDGET * (2.0 if (asym and i == 0) else 1.0) for i in range(n)]
        for lv in LEVELS:
            if lv == "Xb":
                gs = run_xb(lists, gap_ests, budgets, bar, cost, e_min)
            else:
                gs = P.run_campaign(lv, lists, gap_ests, budgets, bar, cost, e_min)
            out[lv]["first"].append([g.first for g in gs])
            out[lv]["q"].append([sum(g.status(c, e_min) == "q" for c in g.lst) for g in gs])
            ap, apeer, fpool, fpeer, fprior = [], [], [], [], []
            for i in range(n):
                others = [j for j in range(n) if j != i]
                lk = leak_xb if lv == "Xb" else (lambda gs_, i_, at: P.leakage(lv, gs_, i_, at))
                a1, f1, f0 = lk(gs, i, others)
                a2, f2, _ = lk(gs, i, [others[0]])
                ap.append(a1); apeer.append(a2); fpool.append(f1); fpeer.append(f2)
                fprior.append(f0)
            out[lv]["auc_pool"].append(ap); out[lv]["auc_peer"].append(apeer)
            out[lv]["fam_pool"].append(fpool); out[lv]["fam_peer"].append(fpeer)
            out[lv]["fam_prior"].append(fprior)
    res = {}
    f0 = np.array(out["X0"]["first"])
    for lv in LEVELS:
        f = np.array(out[lv]["first"])
        r = {"pw": (f < f0 - 1e-9).mean(axis=0).tolist(),
             "found_rate": np.isfinite(f).mean(axis=0).tolist(),
             "q_mean": np.mean(out[lv]["q"], axis=0).tolist()}
        for key in ("auc_pool", "auc_peer"):
            r[key] = np.mean(out[lv][key], axis=0).tolist()
        pri = np.mean(out[lv]["fam_prior"], axis=0)
        r["famadv_pool"] = (np.mean(out[lv]["fam_pool"], axis=0) - pri).tolist()
        r["famadv_peer"] = (np.mean(out[lv]["fam_peer"], axis=0) - pri).tolist()
        res[lv] = r
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", type=int, default=200)
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--out", default=str(P.HERE / "results" / "broker_exchange.json"))
    a = ap.parse_args()
    P.LEVELS = LEVELS                       # grade() iterates over these
    configs = [dict(n=n, o=o, e_min=1.5, asym=False, rule="mean")
               for n in (2, 3, 5) for o in (0.0, 0.25, 0.5, 1.0) if P.feasible(n, o)]
    results = {"worlds": a.worlds, "seeds": a.seeds, "configs": []}
    with Pool(a.procs) as pool:
        for cf in configs:
            jobs = [(w, cf["n"], cf["o"], cf["e_min"], cf["asym"], cf["rule"], a.seeds)
                    for w in range(a.worlds)]
            g = P.grade(pool.map(one_world, jobs))
            results["configs"].append({**cf, "grade": g})
            print(cf["n"], cf["o"], {lv: (round(g[lv]["P_all_gain"], 3),
                                          round(g[lv]["P_leak_ok_pool"], 3),
                                          round(g[lv]["P_winwin_pool"], 3),
                                          [round(x, 2) for x in g[lv]["auc_pool"]])
                                     for lv in LEVELS}, flush=True)
            Path(a.out).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
