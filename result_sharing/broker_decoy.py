#!/usr/bin/env python3
"""Brokered booking with decoy refusals (level Xb-d; prediction B4 in BROKER_PREDICTION.md).

Same campaigns as broker_exchange.py. With probability q, a booking of a calculation that
no other group holds is answered "booked" (once per group and calculation); the group
skips it that round. The attacker cannot tell decoys from real refusals.
"""
import argparse
import json
import zlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import broker_exchange as B
import peer_exchange as P

QS = [0.1, 0.2, 0.3, 0.5]
LEVELS = ["X0", "Xb"] + [f"Xb_d{q}" for q in QS]


def run_xbd(lists, gap_ests, budgets, world, cost, e_min, q, rng):
    gs = [P.Group(l, ge, b) for l, ge, b in zip(lists, gap_ests, budgets)]
    for g in gs:
        g.signals = []
    store, decoyed = {}, set()

    def receive(g, c, kind, val):
        if kind == "gap":
            g.gap.setdefault(c, val)
        elif c not in g.bar:
            g.bar[c] = val
            g.pool_n[P.FAM[c]] += 1
            g.pool_pass[P.FAM[c]] += val >= e_min

    holders = {}
    for gi, l in enumerate(lists):
        for c in l:
            holders.setdefault(int(c), set()).add(gi)
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
                if (c, kind) in store:
                    val, src = store[(c, kind)]
                    receive(g, c, kind, val); g.signals.append((c, src)); g.check_first(e_min)
                    continue
                if (c, kind) in booked:
                    waiting.append((gi, c, kind)); g.signals.append((c, booked[(c, kind)]))
                    skip.add(c)
                    continue
                if (holders[c] == {gi} and (gi, c, kind) not in decoyed
                        and rng.random() < q):
                    decoyed.add((gi, c, kind)); g.signals.append((c, -1))
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
                receive(gs[gi], c, kind, store[(c, kind)][0]); gs[gi].check_first(e_min)
        if not moved and not waiting and not any(
                g.next_step(e_min, cost) is not None and g.spend < g.budget for g in gs):
            break
        if not moved and not waiting:
            # only decoys stopped progress this round; continue to the next round
            if rnd > 150:
                break
    return gs


def leak_xbd(gs, i, attackers):
    g = gs[i]
    truth = np.zeros(P.NC, bool); truth[list(g.lst)] = True
    silent = [j for j in range(len(gs)) if j not in attackers]
    seen = np.zeros(P.NC)
    for a in attackers:
        for c, src in gs[a].signals:
            if src == -1 or src in silent:       # decoys look like real refusals
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
        budgets = [P.BUDGET] * n
        for lv in LEVELS:
            if lv == "X0":
                gs = P.run_campaign("X0", lists, gap_ests, budgets, bar, cost, e_min); lk = None
            elif lv == "Xb":
                gs = B.run_xb(lists, gap_ests, budgets, bar, cost, e_min); lk = B.leak_xb
            else:
                q = float(lv.split("_d")[1])
                drng = np.random.default_rng(zlib.crc32(f"dec:{wid}:{n}:{o}:{s}:{q}".encode()))
                gs = run_xbd(lists, gap_ests, budgets, bar, cost, e_min, q, drng); lk = leak_xbd
            out[lv]["first"].append([g.first for g in gs])
            out[lv]["q"].append([sum(g.status(c, e_min) == "q" for c in g.lst) for g in gs])
            ap, apeer, fpool, fpeer, fprior = [], [], [], [], []
            for i in range(n):
                others = [j for j in range(n) if j != i]
                f = lk or (lambda gs_, i_, at: P.leakage("X0", gs_, i_, at))
                a1, f1, f0 = f(gs, i, others); a2, f2, _ = f(gs, i, [others[0]])
                ap.append(a1); apeer.append(a2); fpool.append(f1); fpeer.append(f2); fprior.append(f0)
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
    ap.add_argument("--out", default=str(P.HERE / "results" / "broker_decoy.json"))
    a = ap.parse_args()
    P.LEVELS = LEVELS
    configs = [dict(n=3, o=o, e_min=1.5, asym=False, rule="mean") for o in (0.5, 1.0)]
    results = {"worlds": a.worlds, "seeds": a.seeds, "q": QS, "configs": []}
    with Pool(a.procs) as pool:
        for cf in configs:
            jobs = [(w, cf["n"], cf["o"], cf["e_min"], cf["asym"], cf["rule"], a.seeds)
                    for w in range(a.worlds)]
            g = P.grade(pool.map(one_world, jobs))
            results["configs"].append({**cf, "grade": g})
            print(cf["n"], cf["o"], {lv: (round(g[lv]["P_all_gain"], 3),
                                          round(g[lv]["P_leak_ok_pool"], 3),
                                          round(g[lv]["P_winwin_pool"], 3),
                                          round(float(np.mean(g[lv]["auc_pool"])), 3),
                                          round(float(np.mean(g[lv]["famadv_pool"])), 3))
                                     for lv in LEVELS}, flush=True)
            Path(a.out).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
