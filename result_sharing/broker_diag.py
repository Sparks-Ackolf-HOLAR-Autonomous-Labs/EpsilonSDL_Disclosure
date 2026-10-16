#!/usr/bin/env python3
"""Diagnostic for the decoy level: how decoys change what each group computes first.

For N = 3, o = 0.5, reports the share of each group's own calculations (and of its first
three) that fall on compounds common to all lists, the mean spend to the first qualifier,
and the mean number of results received, under Xb and Xb-d (q = 0.3, 0.5).
"""
import json
import zlib

import numpy as np

import broker_decoy as D
import broker_exchange as B
import peer_exchange as P

N, O, WORLDS, SEEDS = 3, 0.5, 60, 30
stats = {k: {"common_all": [], "common_first3": [], "spend_first": [], "received": []}
         for k in ("X0", "Xb", "Xb_d0.3", "Xb_d0.5")}
for wid in range(WORLDS):
    mu, sd = P.V.barrier_point("mean")
    bar = mu + sd * np.random.default_rng(zlib.crc32(f"pw:mean:{wid}".encode())).standard_normal(P.NC)
    for s in range(SEEDS):
        rng = np.random.default_rng(zlib.crc32(f"ps:{wid}:{N}:{O}:{s}".encode()))
        lists = P.make_lists(rng, N, O)
        common = set.intersection(*[set(int(c) for c in l) for l in lists])
        g0 = np.where(np.isfinite(P.GAPS), P.GAPS, 0.0)
        ge = [g0 + P.GAP_SD * rng.standard_normal(P.NC) for _ in range(N)]
        cost = (P.CGAP * np.exp(P.COST_SD * rng.standard_normal(P.NC)),
                P.CNEB * np.exp(P.COST_SD * rng.standard_normal(P.NC)))
        bud = [P.BUDGET] * N
        for k in stats:
            if k == "X0":
                gs = P.run_campaign("X0", lists, ge, bud, bar, cost, 1.5)
            elif k == "Xb":
                gs = B.run_xb(lists, ge, bud, bar, cost, 1.5)
            else:
                q = float(k.split("_d")[1])
                drng = np.random.default_rng(zlib.crc32(f"dec:{wid}:{N}:{O}:{s}:{q}".encode()))
                gs = D.run_xbd(lists, ge, bud, bar, cost, 1.5, q, drng)
            for g in gs:
                own = [c for c, _ in g.own_steps]
                stats[k]["common_all"].append(np.mean([c in common for c in own]) if own else 0)
                stats[k]["common_first3"].append(np.mean([c in common for c in own[:3]]) if own else 0)
                if np.isfinite(g.first):
                    stats[k]["spend_first"].append(g.first)
                stats[k]["received"].append(len([1 for c, src in getattr(g, "signals", [])
                                                 if src != -1]))
out = {k: {m: float(np.mean(v)) for m, v in d.items()} for k, d in stats.items()}
print(json.dumps(out, indent=1))
json.dump(out, open(P.HERE / "results" / "broker_diag.json", "w"), indent=1)
