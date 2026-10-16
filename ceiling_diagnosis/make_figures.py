#!/usr/bin/env python3
"""Figures for the findings 1-2 re-evaluation, the finding-5 decision-maker
leakage study, the finding-4 sociability map, and the task-6 governance
re-grade. One script so styling stays consistent."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
MPT = HERE.parent

# ---------------------------------------------------------------- fig 1
d = json.load(open(HERE / "results" / "ceiling_diagnosis.json"))
rows = d["rows"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ax = axes[0]
parts = ["irreducible_frac", "science_gap_frac", "exec_gap_frac"]
labels = ["irreducible\n(oracle path)", "scientific uncertainty\n(not contractible)",
          "execution info\n(all a contract can sell)"]
data = [np.clip([r[p] for r in rows], 0, 1) for p in parts]
bp = ax.boxplot(data, tick_labels=labels, showmeans=True, whis=(10, 90))
ax.axhline(0.20, color="crimson", ls="--", lw=1,
           label="preregistered $g_R$ = 20%")
ax.set_ylabel("fraction of DTDE spend-to-first-qualifier")
ax.set_title("Where DTDE's node-hours actually go (300 worlds)")
ax.legend()
ax = axes[1]
er = np.sort([r["exec_gap_frac"] for r in rows])
ax.plot(er, np.linspace(0, 1, len(er)), lw=2)
ax.axvline(0.20, color="crimson", ls="--", lw=1, label="$g_R$=20%")
ax.axvline(0.10, color="orange", ls="--", lw=1, label="$g_R$=10%")
ax.set_xlabel("execution-information headroom (CTCE vs DTDE), per world")
ax.set_ylabel("cumulative fraction of worlds")
ax.set_title("P(headroom $\\geq$ 20%) = "
             f"{d['summary']['p_exec_gap_ge_20pct']:.2f}; "
             "$\\geq$ 10% = "
             f"{d['summary']['p_exec_gap_ge_10pct']:.2f}")
ax.legend()
ax.set_xlim(-0.6, 0.8)
fig.tight_layout()
fig.savefig(HERE / "results" / "fig_ceiling_decomposition.png", dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- fig 2
dm = json.load(open(MPT / "decision_maker_leakage" / "dm_leakage.json"))
conds = list(dm["audit"].keys())
pols = list(dm["audit"][conds[0]]["single_policy"].keys())
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
ax = axes[0]
x = np.arange(len(conds))
w = 0.14
for k, p in enumerate(pols):
    ax.bar(x + (k - 2) * w, [dm["audit"][c]["single_policy"][p]
                             for c in conds], w, label=p)
ax.bar(x + 3 * w, [dm["audit"][c]["policy_robust"] for c in conds], w,
       color="black", label="policy-robust")
ax.set_xticks(x)
ax.set_xticklabels(conds, fontsize=8)
ax.set_ylabel("P(all six leakage limits hold)")
ax.set_title("Single-policy audits vs the policy-robust audit")
ax.legend(fontsize=7, ncol=2)
ax = axes[1]
ch = "r_mi_auc"
for c in conds:
    vals = [dm["table"][p][c][ch] for p in pols]
    ax.plot(pols, vals, marker="o", label=c)
ax.axhline(0.60, color="crimson", ls="--", lw=1, label="limit 0.60")
ax.set_ylabel("membership-inference AUC (mean)")
ax.set_title("The same contract leaks differently per decision maker")
ax.tick_params(axis="x", labelsize=8)
ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig(MPT / "decision_maker_leakage" / "fig_dm_leakage.png", dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- fig 3
sm = json.load(open(MPT / "sociability_map" / "sociability_map.json"))
scales = sm["scales"]
res = sm["results"]
show = ["CTDE_P2", "CEDT_P2", "CTDE_P3_eps2", "CEDT_P3_eps2",
        "CTDE_P4", "CEDT_P4", "CTCE_P0"]
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
ax = axes[0]
for name in show:
    ax.plot(scales, [res[f"scale_{s:g}"][name]["labels_ratio"]
                     for s in scales], marker="o", label=name)
ax.set_xscale("log")
ax.axhline(1.0, color="gray", lw=0.8)
ax.set_xlabel("task scale (x measured MX$_2$ ladder cost)")
ax.set_ylabel("labels/nh vs DTDE-P4 (sociability value)")
ax.set_title("What sharing buys, by task scale")
ax.legend(fontsize=7)
ax = axes[1]
for name in show:
    if name == "CTCE_P0":
        continue
    xs = [res[f"scale_{s:g}"][name]["labels_ratio"] for s in scales]
    ys = [res[f"scale_{s:g}"][name]["worst_leak_util"] for s in scales]
    sc = ax.scatter(xs, ys, s=np.linspace(20, 140, len(scales)),
                    label=name, alpha=0.8)
    ax.plot(xs, ys, lw=0.6, color=sc.get_facecolor()[0], alpha=0.5)
ax.axhline(1.0, color="crimson", ls="--", lw=1,
           label="leakage limit (util = 1)")
ax.set_xlabel("sociability value (labels/nh vs DTDE)")
ax.set_ylabel("leakage price (worst-channel utilization)")
ax.set_title("Sociability frontier (marker size = task scale)")
ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig(MPT / "sociability_map" / "fig_sociability_map.png", dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- fig 4
gv = json.load(open(MPT / "governance_regrade" / "governance_regrade.json"))
scen = ["frozen", "optA_hlabels_1.10", "optA_hlabels_1.05",
        "optA_hlabels_1.00", "exec_gR20", "exec_gR10",
        "package_exec_gR10_hlabels_1.05"]
nice = ["frozen\n(0.041)", "H 10%", "H 5%", "H 0%", "exec $g_R$20%",
        "exec $g_R$10%", "package:\nexec 10% + H 5%"]
top_conds = ["CEDT_P4", "CEDT_P3_eps2", "CTDE_P3_eps1", "CEDT_P2"]
fig, ax = plt.subplots(figsize=(9.5, 4.2))
x = np.arange(len(scen))
w = 0.2
for k, c in enumerate(top_conds):
    ax.bar(x + (k - 1.5) * w,
           [gv[s].get(c, {}).get("p_win_win", 0) for s in scen], w, label=c)
for thr, col in ((0.90, "crimson"), (0.50, "orange")):
    ax.axhline(thr, color=col, ls="--", lw=1,
               label=f"acceptance threshold {thr}")
ax.set_xticks(x)
ax.set_xticklabels(nice, fontsize=8)
ax.set_ylabel("P(win-win)")
ax.set_title("Task 6: governance options A (margins) and B (thresholds)")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(MPT / "governance_regrade" / "fig_governance.png", dpi=140)
plt.close(fig)
print("wrote 4 figures")
