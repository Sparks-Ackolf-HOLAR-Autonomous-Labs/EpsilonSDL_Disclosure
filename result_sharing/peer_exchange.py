#!/usr/bin/env python3
"""Peer exchange of scientific results among N research groups.

Predictions R1 to R6 were registered in PREDICTION.md before this file was written.

No party owns a resource here. N groups screen their own lists of MX2 compounds for the
same device goal (1.0-2.0 eV PBE gap and chalcogen vacancy barrier >= E_min) and may
exchange only what their calculations found:
  X0 nothing; X1 records (compound, value), unattributed; X2 verdicts (compound,
  qualifies or not); X3 pooled pass counts per family (metal group x phase), no names.
Measured inputs: 1x1 PBE gaps, DFT NEB barriers (7) and offset-corrected MACE barriers
(23), measured gap-step cost at 3x3 (comparison No. 1) and measured NEB cost.
Campaign numbers are SIMULATED UNITS anchored to those measurements.
"""
import argparse
import collections
import json
import sys
import zlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
MPT = HERE.parent
sys.path.insert(0, str(MPT / "vacancy_barriers" / "twin_kmc"))
import vacancy_goal as V  # noqa: E402  (barrier rules, compound names)

NAMES = V.NAMES
NC = len(NAMES)
LIST_K = 10
GAP_SD = 0.35          # a group's own gap estimate error (eV), per group and world
COST_SD = 0.10         # run-to-run lognormal noise on measured costs
BUDGET = 6.0           # node-hours per group (all gap steps on a list plus about 3 barriers)
K0 = 2.0               # strength of a group's prior on a family pass rate
LEVELS = ["X0", "X1", "X2", "X3", "X1c"]   # X1c: post hoc, see RESULTS.md


def family(n):
    return ("g6" if n.startswith(("Mo", "W")) else "g4") + "_" + n.split("_")[1]


FAMS = sorted({family(n) for n in NAMES})
FAM = np.array([FAMS.index(family(n)) for n in NAMES])


def load_measured():
    gap = {}
    for line in open(MPT / "dft_campaign" / "results" / "outcomes.jsonl"):
        r = json.loads(line)
        g = r["stages"].get("F3", {}).get("gap_ev")
        if g is not None:
            gap[r["candidate"]] = g          # later (repair) lines override
    gaps = np.array([gap.get(n, np.nan) for n in NAMES])
    per = collections.defaultdict(list)
    for line in open(MPT / "paired_comparison_1" / "results" / "campaigns.jsonl"):
        r = json.loads(line)
        acc = collections.defaultdict(float)
        for j in r["jobs"]:
            acc[j["candidate"]] += j["true_nh"]
        for c, v in acc.items():
            per[c].append(v)
    cg = {c: float(np.mean(v)) for c, v in per.items()}
    ph_med = {ph: float(np.median([v for c, v in cg.items() if c.endswith(ph)]))
              for ph in ("1T", "2H")}
    cgap = np.array([cg.get(n, ph_med[n.split("_")[1]]) for n in NAMES])
    neb = {}
    for n in V.DFT:
        d = json.loads((MPT / "vacancy_barriers" / "dft_neb" / "results_dft"
                        / f"{n}.json").read_text())
        neb[n] = (d["ini_wall_s"] + d["fin_wall_s"] + d["neb_wall_s"]) / 3600.0 \
            * d["ranks"] / 64.0                 # node-hours on a 64-core node
    gm = float(np.exp(np.mean(np.log(list(neb.values())))))
    cneb = np.array([neb.get(n, gm) for n in NAMES])
    return gaps, cgap, cneb, cg, neb


GAPS, CGAP, CNEB, CG_MEAS, NEB_MEAS = load_measured()
WINDOW = (GAPS >= 1.0) & (GAPS <= 2.0)
MU_PRIOR = V.MACE + V.OFF_MEAN               # uncalibrated barrier prior every group holds
SD_PRIOR = V.OFF_SD


def make_lists(rng, n, o):
    core_n = int(round(LIST_K * o))
    perm = rng.permutation(NC)
    core = perm[:core_n]
    rest = perm[core_n:]
    m = LIST_K - core_n
    return [np.concatenate([core, rest[i * m:(i + 1) * m]]) for i in range(n)]


def feasible(n, o):
    core_n = int(round(LIST_K * o))
    return core_n + n * (LIST_K - core_n) <= NC


class Group:
    def __init__(self, lst, gap_est, budget):
        self.lst = set(int(c) for c in lst)
        self.gap_est = gap_est
        self.budget = budget
        self.spend = 0.0
        self.first = np.inf
        self.gap = {}            # known gaps (own or received)
        self.bar = {}            # known barriers
        self.verdict = {}        # received verdicts
        self.fam_n = np.zeros(len(FAMS))
        self.fam_pass = np.zeros(len(FAMS))
        self.pool_n = np.zeros(len(FAMS))     # pooled counts received under X3
        self.pool_pass = np.zeros(len(FAMS))
        self.own_steps = []      # (compound, kind)

    def p_imm(self, c, e_min):
        p0 = 1.0 - norm.cdf(e_min, MU_PRIOR[c], SD_PRIOR)
        f = FAM[c]
        n = self.fam_n[f] + self.pool_n[f]
        k = self.fam_pass[f] + self.pool_pass[f]
        return (K0 * p0 + k) / (K0 + n)

    def status(self, c, e_min):
        """'q' qualifies, 'x' rejected, None open."""
        if c in self.verdict:
            return "q" if self.verdict[c] else "x"
        if c in self.gap and not (1.0 <= self.gap[c] <= 2.0):
            return "x"
        if c in self.bar:
            if c in self.gap or WINDOW[c]:
                return "q" if (self.bar[c] >= e_min and c in self.gap) else (
                    "x" if self.bar[c] < e_min else None)
        return None

    def check_first(self, e_min):
        if np.isfinite(self.first):
            return
        if any(self.status(c, e_min) == "q" for c in self.lst):
            self.first = self.spend

    def next_step(self, e_min, cost, claimed=()):
        best, best_v = None, -1.0
        for c in self.lst:
            if c in claimed or self.status(c, e_min) is not None:
                continue
            pim = 1.0 if c in self.bar else self.p_imm(c, e_min)
            if c in self.gap:                     # gap known, in window: barrier step
                v, step = pim / cost[1][c], (c, "bar")
            else:
                g = self.gap_est[c]
                pw = norm.cdf(2.0, g, GAP_SD) - norm.cdf(1.0, g, GAP_SD)
                v = pw * pim / (cost[0][c] + pw * cost[1][c])
                step = (c, "gap")
            if v > best_v:
                best, best_v = step, v
        return best


def run_campaign(level, lists, gap_ests, budgets, world, cost, e_min):
    bar_true = world
    gs = [Group(l, ge, b) for l, ge, b in zip(lists, gap_ests, budgets)]
    for rnd in range(200):
        pub = []                                   # (group, compound, kind, value)
        moved = False
        claimed = set()
        order = range(len(gs)) if rnd % 2 == 0 else reversed(range(len(gs)))
        for gi in order:
            g = gs[gi]
            st = g.next_step(e_min, cost, claimed if level == "X1c" else ())
            if st is None:
                continue
            c, kind = st
            ck = cost[0][c] if kind == "gap" else cost[1][c]
            if g.spend + ck > g.budget:
                continue
            moved = True
            claimed.add(c)
            g.spend += ck
            if kind == "gap":
                val = GAPS[c] if np.isfinite(GAPS[c]) else -1.0
                g.gap[c] = val
            else:
                val = bar_true[c]
                g.bar[c] = val
                g.fam_n[FAM[c]] += 1
                g.fam_pass[FAM[c]] += val >= e_min
            g.own_steps.append((c, kind))
            pub.append((gi, c, kind, val))
            g.check_first(e_min)
        if not moved:
            break
        if level == "X0":
            continue
        for gi, g in enumerate(gs):
            for gj, c, kind, val in pub:
                if gj == gi:
                    continue
                if level in ("X1", "X1c"):
                    if kind == "gap":
                        g.gap.setdefault(c, val)
                    else:
                        if c not in g.bar:
                            g.bar[c] = val
                            g.pool_n[FAM[c]] += 1
                            g.pool_pass[FAM[c]] += val >= e_min
                elif level == "X2":
                    final = (kind == "gap" and not (1.0 <= val <= 2.0)) or kind == "bar"
                    if final:
                        g.verdict.setdefault(c, kind == "bar" and val >= e_min
                                             and bool(WINDOW[c]))
                elif level == "X3" and kind == "bar":
                    g.pool_n[FAM[c]] += 1
                    g.pool_pass[FAM[c]] += val >= e_min
            g.check_first(e_min)
    return gs


def auc(scores, truth):
    pos, neg = scores[truth], scores[~truth]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    gt = (pos[:, None] > neg[None, :]).mean()
    eq = (pos[:, None] == neg[None, :]).mean()
    return float(gt + 0.5 * eq)


def leakage(level, gs, i, attackers):
    """Attacker = groups in `attackers` pooled; scores compound membership in group i."""
    g = gs[i]
    truth = np.zeros(NC, bool)
    truth[list(g.lst)] = True
    seen = np.zeros(NC)
    if level in ("X1", "X2", "X1c"):
        others_own = set()
        for a in attackers:
            others_own |= {c for c, _ in gs[a].own_steps}
        silent = [j for j in range(len(gs)) if j not in attackers]   # incl. i
        w = 1.0 / len(silent)
        for j in silent:
            for c, kind in gs[j].own_steps:
                if level == "X2" and kind == "gap" and 1.0 <= GAPS[c] <= 2.0:
                    continue                      # no verdict published yet
                seen[c] = max(seen[c], w)
    elif level == "X3":
        silent = [j for j in range(len(gs)) if j not in attackers]
        cnt = np.zeros(len(FAMS))
        for j in silent:
            for c, kind in gs[j].own_steps:
                if kind == "bar":
                    cnt[FAM[c]] += 1
        sizes = np.bincount(FAM, minlength=len(FAMS))
        seen = (cnt / sizes)[FAM] / len(silent)
    a = auc(seen, truth)
    fam_counts = np.bincount(FAM[list(g.lst)], minlength=len(FAMS))
    top = set(np.flatnonzero(fam_counts == fam_counts.max()))
    fam_score = np.array([seen[FAM == f].sum() for f in range(len(FAMS))])
    guess = int(np.argmax(fam_score)) if fam_score.max() > 0 else -1
    prior_guess = int(np.argmax(np.bincount(FAM, minlength=len(FAMS))))
    return a, float(guess in top), float(prior_guess in top)


def one_world(args):
    wid, n, o, e_min, asym, rule, nseed = args
    mu, sd = V.barrier_point(rule)
    rng_w = np.random.default_rng(zlib.crc32(f"pw:{rule}:{wid}".encode()))
    bar = mu + sd * rng_w.standard_normal(NC)
    out = {lv: {"first": [], "auc_pool": [], "auc_peer": [], "fam_pool": [],
                "fam_peer": [], "fam_prior": [], "q": []} for lv in LEVELS}
    for s in range(nseed):
        rng = np.random.default_rng(zlib.crc32(f"ps:{wid}:{n}:{o}:{s}".encode()))
        lists = make_lists(rng, n, o)
        g0 = np.where(np.isfinite(GAPS), GAPS, 0.0)
        gap_ests = [g0 + GAP_SD * rng.standard_normal(NC) for _ in range(n)]
        cost = (CGAP * np.exp(COST_SD * rng.standard_normal(NC)),
                CNEB * np.exp(COST_SD * rng.standard_normal(NC)))
        budgets = [BUDGET * (2.0 if (asym and i == 0) else 1.0) for i in range(n)]
        for lv in LEVELS:
            gs = run_campaign(lv, lists, gap_ests, budgets, bar, cost, e_min)
            out[lv]["first"].append([g.first for g in gs])
            out[lv]["q"].append([sum(g.status(c, e_min) == "q" for c in g.lst)
                                 for g in gs])
            ap, apeer, fpool, fpeer, fprior = [], [], [], [], []
            for i in range(n):
                others = [j for j in range(n) if j != i]
                a1, f1, f0 = leakage(lv, gs, i, others)
                a2, f2, _ = leakage(lv, gs, i, [others[0]])
                ap.append(a1); apeer.append(a2); fpool.append(f1); fpeer.append(f2)
                fprior.append(f0)
            out[lv]["auc_pool"].append(ap); out[lv]["auc_peer"].append(apeer)
            out[lv]["fam_pool"].append(fpool); out[lv]["fam_peer"].append(fpeer)
            out[lv]["fam_prior"].append(fprior)
    res = {}
    f0 = np.array(out["X0"]["first"])
    for lv in LEVELS:
        f = np.array(out[lv]["first"])
        win = (f < f0 - 1e-9).mean(axis=0)                 # per group paired win rate
        r = {"pw": win.tolist(),
             "found_rate": np.isfinite(f).mean(axis=0).tolist(),
             "q_mean": np.mean(out[lv]["q"], axis=0).tolist()}
        for key in ("auc_pool", "auc_peer"):
            r[key] = np.mean(out[lv][key], axis=0).tolist()
        pri = np.mean(out[lv]["fam_prior"], axis=0)
        r["famadv_pool"] = (np.mean(out[lv]["fam_pool"], axis=0) - pri).tolist()
        r["famadv_peer"] = (np.mean(out[lv]["fam_peer"], axis=0) - pri).tolist()
        res[lv] = r
    return res


def grade(worlds):
    agg = {}
    for lv in LEVELS:
        pw = np.array([w[lv]["pw"] for w in worlds])
        gain_all = (pw >= 0.60).all(axis=1)
        out = {"P_all_gain": float(gain_all.mean()),
               "P_each_gain": (pw >= 0.60).mean(axis=0).tolist(),
               "pw_mean": pw.mean(axis=0).tolist(),
               "found_rate": np.mean([w[lv]["found_rate"] for w in worlds], axis=0).tolist(),
               "q_mean": np.mean([w[lv]["q_mean"] for w in worlds], axis=0).tolist(),
               # spread over worlds of the group-averaged quantities (figure bands)
               "pw_world_p10_50_90": np.percentile(pw.mean(axis=1), [10, 50, 90]).tolist(),
               "q_world_p10_50_90": np.percentile(
                   [np.mean(w[lv]["q_mean"]) for w in worlds], [10, 50, 90]).tolist(),
               "auc_pool_world_p10_50_90": np.percentile(
                   [np.mean(w[lv]["auc_pool"]) for w in worlds], [10, 50, 90]).tolist()}
        for att in ("pool", "peer"):
            a = np.array([w[lv][f"auc_{att}"] for w in worlds])
            fa = np.array([w[lv][f"famadv_{att}"] for w in worlds])
            ok = ((a <= 0.60) & (fa <= 0.10)).all(axis=1)
            out[f"auc_{att}"] = a.mean(axis=0).tolist()
            out[f"famadv_{att}"] = fa.mean(axis=0).tolist()
            out[f"P_leak_ok_{att}"] = float(ok.mean())
            out[f"P_winwin_{att}"] = float((ok & gain_all).mean())
        agg[lv] = out
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", type=int, default=200)
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--out", default=str(HERE / "results" / "peer_exchange.json"))
    a = ap.parse_args()
    configs = []
    for n in (2, 3, 5):
        for o in (0.0, 0.25, 0.5, 1.0):
            if feasible(n, o):
                configs.append(dict(n=n, o=o, e_min=1.5, asym=False, rule="mean"))
    for o in (0.0, 0.5, 1.0):
        configs.append(dict(n=3, o=o, e_min=1.7, asym=False, rule="mean"))
        configs.append(dict(n=3, o=o, e_min=1.5, asym=False, rule="family"))
    for o in (0.0, 0.5):
        configs.append(dict(n=3, o=o, e_min=1.5, asym=True, rule="mean"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    results = {"inputs": {"names": NAMES, "gap_eV": [None if not np.isfinite(x) else float(x)
                                                     for x in GAPS],
                          "window": WINDOW.tolist(), "cost_gap_nh": CGAP.tolist(),
                          "cost_barrier_nh": CNEB.tolist(),
                          "gap_cost_measured": sorted(CG_MEAS),
                          "barrier_cost_measured": NEB_MEAS,
                          "budget_nh": BUDGET, "list_k": LIST_K, "gap_sd": GAP_SD,
                          "worlds": a.worlds, "seeds": a.seeds},
               "configs": []}
    with Pool(a.procs) as pool:
        for cf in configs:
            jobs = [(w, cf["n"], cf["o"], cf["e_min"], cf["asym"], cf["rule"], a.seeds)
                    for w in range(a.worlds)]
            worlds = pool.map(one_world, jobs)
            g = grade(worlds)
            results["configs"].append({**cf, "grade": g})
            print(cf, {lv: (round(g[lv]["P_all_gain"], 3), round(g[lv]["P_leak_ok_pool"], 3),
                            round(g[lv]["P_leak_ok_peer"], 3)) for lv in LEVELS}, flush=True)
            Path(a.out).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
