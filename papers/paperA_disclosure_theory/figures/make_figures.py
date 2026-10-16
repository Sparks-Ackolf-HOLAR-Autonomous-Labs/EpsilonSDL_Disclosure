#!/usr/bin/env python3
"""Figures for the disclosure article (minimal reciprocal disclosure).

Every number plotted is read from a committed result file under
; nothing is typed in by hand except the plotting
thresholds that the preregistrations fixed (1.05 margin, 0.60 AUC limit,
identity limits read from the attack JSONs). Figures are drawn at their
printed size (text width 153 mm in iopjournal.cls) with 7-8 pt fonts.

Uncertainty conventions
- Simulated probabilities P(win-win): Wilson 95% interval with n = number
  of prior worlds behind the cell.
- Measured throughput ratios: paired bootstrap over seeds (10 000 draws).
"""
import json
import math
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # repository root
MM = 1 / 25.4
FULL = 153 * MM

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "savefig.dpi": 300, "font.family": "DejaVu Sans",
})
C_D = "#5B6770"   # no sharing (DTDE), slate
C_C = "#C8553D"   # broker (CEDT), brick
C_B = "#2E86AB"   # blue accent
C_G = "#8AA05B"   # green accent
GREY = "0.55"


def load(p):
    return json.load(open(ROOT / p))


def wilson(p, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def panel(ax, s):
    ax.text(-0.02, 1.04, s, transform=ax.transAxes, fontweight="bold",
            fontsize=8.5, ha="right", va="bottom")


# ---------------------------------------------------------------- figure 1
def fig_contracts():
    fig = plt.figure(figsize=(FULL, 58 * MM))
    ax = fig.add_axes([0.06, 0.16, 0.36, 0.76])
    ax.set_xlim(-0.3, 1.3); ax.set_ylim(-0.42, 1.3)
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, lw=0.8, ec="0.3"))
    corners = {
        (0, 0): ("DTDE", "no sharing"),
        (1, 0): ("CEDT", "per-job broker"),
        (0, 1): ("CTDE", "shared logbook"),
        (1, 1): ("CTCE", "all merged"),
    }
    for (x, y), (n, d) in corners.items():
        ax.plot(x, y, "o", ms=5, color=C_C if (x, y) == (1, 0) else C_D)
        dy = -0.07 if y == 0 else 0.07
        va = "top" if y == 0 else "bottom"
        ha = "left" if x == 0 else "right"
        ax.text(x + (0.02 if x == 0 else -0.02), y + dy, f"{n}\n{d}",
                ha=ha, va=va, fontsize=6.5, linespacing=1.1,
                fontweight="normal")
    ax.plot(0.5, 0.5, "s", ms=4, mfc="white", mec=C_B)
    ax.text(0.53, 0.47, "mixture\n(τ, ε)", fontsize=6.3, color=C_B,
            va="top")
    ax.annotate("", xy=(1.18, -0.3), xytext=(-0.05, -0.3),
                arrowprops=dict(arrowstyle="->", lw=0.6, color="0.3"))
    ax.text(0.56, -0.335, "execution centralization ε", ha="center",
            va="top", fontsize=7)
    ax.annotate("", xy=(-0.22, 1.18), xytext=(-0.22, -0.05),
                arrowprops=dict(arrowstyle="->", lw=0.6, color="0.3"))
    ax.text(-0.255, 0.56, "training centralization τ", ha="right",
            va="center", rotation=90, fontsize=7)
    ax.axis("off")
    panel(ax, "(a)")

    ax2 = fig.add_axes([0.50, 0.08, 0.49, 0.84])
    ax2.set_xlim(0, 1); ax2.set_ylim(0, 1); ax2.axis("off")
    rows = [
        ("P0", "raw structures, costs and telemetry"),
        ("P1", "exact descriptors (electron count, cutoff, lattice)"),
        ("P2", "coarse bins with minimum group sizes"),
        ("P3", "opaque IDs + differentially private aggregates"),
        ("P4", "opaque ID, calculation class, success bit, charge"),
        ("P4+1", "P4 plus one bit: memory above or below median"),
    ]
    h = 0.13
    for i, (k, t) in enumerate(rows):
        y = 0.86 - i * (h + 0.02)
        col = C_C if k == "P4+1" else ("0.93" if k != "P4" else "#F2D9D3")
        box = FancyBboxPatch((0.0, y - h), 1.0, h,
                             boxstyle="round,pad=0.0,rounding_size=0.015",
                             fc=col if k != "P4+1" else "white",
                             ec=C_C if k == "P4+1" else "0.75", lw=0.7)
        ax2.add_patch(box)
        ax2.text(0.03, y - h / 2, k, va="center", fontweight="bold",
                 fontsize=7, color=C_C if k == "P4+1" else "0.15")
        ax2.text(0.17, y - h / 2, t, va="center", fontsize=6.8)
    ax2.annotate("", xy=(-0.03, 0.02), xytext=(-0.03, 0.86),
                 arrowprops=dict(arrowstyle="->", lw=0.6, color="0.3"))
    ax2.text(-0.05, 0.44, "less disclosed", rotation=90, ha="right",
             va="center", fontsize=7)
    panel(ax2, "(b)")
    fig.savefig(HERE / "fig1_contracts.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- figure 2
def fig_metric():
    cd = load("ceiling_diagnosis/results/ceiling_diagnosis.json")
    rows = cd["rows"]
    comp = {
        "irreducible": [r["irreducible_frac"] for r in rows],
        "scientific\nluck": [r["science_gap_frac"] for r in rows],
        "tradable\nexecution gap": [r["exec_gap_frac"] for r in rows],
    }
    ms = load("metric_redesign/metric_study.json")
    n = ms["worlds"]
    order = ["T20", "T10", "REG20", "EX15", "EX10", "QY05", "PW60"]
    lab = {"T20": "20% faster", "T10": "10% faster", "REG20": "regret 0.8×",
           "EX15": "labels 1.15×", "EX10": "labels 1.10×",
           "QY05": "+0.5 qualifier", "PW60": "paired win rate"}

    fig, ax = plt.subplots(1, 2, figsize=(FULL, 56 * MM),
                           gridspec_kw={"width_ratios": [1, 1.35]})
    a = ax[0]
    data = list(comp.values())
    parts = a.violinplot(data, positions=range(3), showextrema=False,
                         widths=0.8)
    for pc, c in zip(parts["bodies"], [GREY, C_B, C_C]):
        pc.set_facecolor(c); pc.set_alpha(0.35); pc.set_edgecolor("none")
    for i, d in enumerate(data):
        q10, q50, q90 = np.percentile(d, [10, 50, 90])
        a.plot([i, i], [q10, q90], color="0.2", lw=0.8)
        a.plot(i, np.mean(d), "o", ms=3.5, color="0.1")
    a.axhline(0.20, color="0.3", ls="--", lw=0.6)
    a.text(2.45, 0.21, "20% target", fontsize=6.3, ha="right", va="bottom")
    a.axhline(0, color="0.8", lw=0.5)
    a.set_xticks(range(3), list(comp))
    a.set_ylabel("share of spend to first qualifier")
    a.set_ylim(-0.8, 1.2)
    panel(a, "(a)")

    a = ax[1]
    y = np.arange(len(order))
    for off, key, col, name in [(0.17, "wide_prior_x1", GREY, "wide prior, ×1"),
                                (-0.17, "posterior_x100", C_C,
                                 "measured prior, ×100")]:
        v = [ms[key][m]["p_ww_package"] for m in order]
        lo = [v[i] - wilson(v[i], n)[0] for i in range(len(v))]
        hi = [wilson(v[i], n)[1] - v[i] for i in range(len(v))]
        a.barh(y + off, v, height=0.32, color=col, alpha=0.85, label=name)
        a.errorbar(v, y + off, xerr=[lo, hi], fmt="none", ecolor="0.15",
                   elinewidth=0.6, capsize=1.5)
    a.axvline(0.90, color="0.3", ls="--", lw=0.6)
    a.text(0.89, len(order) - 0.45, "0.90", fontsize=6.3, ha="right")
    a.set_yticks(y, [lab[m] for m in order])
    a.set_xlim(0, 1.0)
    a.set_xlabel("P(both gain and all leakage limits hold)")
    a.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.58, 1.0),
             ncol=2)
    panel(a, "(b)")
    fig.tight_layout(w_pad=1.5)
    fig.savefig(HERE / "fig2_metric.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- figure 3
def grid_from(level):
    d = load(f"centralization_surface/results/surface_{level}.json")
    g = d["meta"]["grid"]
    Z = np.full((g, g), np.nan)
    L = np.full((g, g), np.nan)
    ticks = np.round(np.linspace(0, 1, g), 2)
    for k, v in d["surface"].items():
        if "|" not in k or not isinstance(v["tau"], (int, float)):
            continue
        i = int(round(v["tau"] * (g - 1)))
        j = int(round(v["eps"] * (g - 1)))
        Z[i, j] = v["win_win"]
        L[i, j] = v["leak_ok"]
    return Z, L, ticks, d["meta"]["worlds"]


def fig_surface():
    fig = plt.figure(figsize=(FULL, 58 * MM))
    gs = fig.add_gridspec(1, 5, width_ratios=[1, 1, 0.06, 0.28, 1.35],
                          wspace=0.3, left=0.07, right=0.98, bottom=0.2,
                          top=0.9)
    vmax = 0.30
    for idx, lvl in enumerate(["P4", "P2"]):
        Z, L, ticks, nw = grid_from(lvl)
        a = fig.add_subplot(gs[0, idx])
        im = a.imshow(Z, origin="lower", extent=[-0.05, 1.05, -0.05, 1.05],
                      cmap="Reds", vmin=0, vmax=vmax, aspect="equal")
        a.contour(np.linspace(0, 1, Z.shape[1]), np.linspace(0, 1, Z.shape[0]),
                  L, levels=[0.5], colors=["0.15"], linewidths=0.7,
                  linestyles="--")
        a.set_xlabel("execution ε")
        if idx == 0:
            a.set_ylabel("training τ")
        a.set_xticks([0, 0.5, 1]); a.set_yticks([0, 0.5, 1])
        a.set_title(f"disclosure {lvl}", fontsize=7.5, pad=3)
        for s in a.spines.values():
            s.set_visible(False)
        panel(a, "(a)" if idx == 0 else "(b)")
    cax = fig.add_subplot(gs[0, 2])
    cb = fig.colorbar(im, cax=cax)
    cax.set_title("P(win-win)", fontsize=6.8, pad=4)
    cb.ax.tick_params(labelsize=6.5)

    a = fig.add_subplot(gs[0, 4])
    sc = load("centralization_surface/results/surface_scale.json")
    nw = sc["meta"]["worlds"]
    eps = [0.0, 0.25, 0.5, 0.75, 1.0]
    styles = {1: (GREY, "o", "×1"), 10: (C_B, "s", "×10"),
              100: (C_C, "^", "×100")}
    for s, (col, mk, name) in styles.items():
        v = np.array([sc["cells"][f"x{s}|P4|0.0|{e}"]["win_win"] for e in eps])
        ci = np.array([wilson(x, nw) for x in v])
        a.fill_between(eps, ci[:, 0], ci[:, 1], color=col, alpha=0.18, lw=0)
        a.plot(eps, v, marker=mk, ms=3, lw=1.0, color=col, label=name)
    a.axhline(0.90, color="0.3", ls="--", lw=0.6)
    a.set_xlabel("execution ε (at τ = 0, P4)")
    a.set_ylabel("P(win-win)")
    a.set_ylim(0, 1.02); a.set_xticks([0, 0.5, 1])
    a.legend(title="task scale", frameon=False, loc="upper left",
             bbox_to_anchor=(0.0, 0.84), title_fontsize=6.8)
    panel(a, "(c)")
    fig.savefig(HERE / "fig3_surface.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- figure 4
def boot_ratio(labels_c, charge_c, labels_d, charge_d, B=10000, seed=0):
    rng = np.random.default_rng(seed)
    n = len(labels_c)
    idx = rng.integers(0, n, size=(B, n))
    rc = labels_c[idx].sum(1) / charge_c[idx].sum(1)
    rd = labels_d[idx].sum(1) / charge_d[idx].sum(1)
    r = rc / rd
    return np.percentile(r, [2.5, 97.5])


def no1_arrays(rule):
    recs = [json.loads(l) for l in open(ROOT / "paired_comparison_1/results/campaigns.jsonl")]
    out = {}
    for arm in ["DTDE", "CEDT_P4"]:
        rs = sorted([r for r in recs if r["arm"] == arm], key=lambda r: r["seed"])
        lab = np.array([r["labels_f2"] for r in rs], float)
        ch = np.array([sum(j["wall_s"] / 3600 * (1 if rule == "node" else j["ranks"] / 64)
                           for j in r["jobs"]) for r in rs])
        out[arm] = (lab, ch)
    return out


def no2_arrays(key):
    rep = load("paired_comparison_2/f3_repair/results/repair_graded.json")
    out = {}
    for arm in ["DTDE", "CEDT_P4"]:
        rs = sorted([c for c in rep["campaigns"] if c["arm"] == arm],
                    key=lambda c: c["seed"])
        out[arm] = (np.array([c["labels_f2"] for c in rs], float),
                    np.array([c[key] for c in rs]))
    return out, rep


def fig_cases():
    bil = load("billing_regrade/billing_regrade.json")
    fig, ax = plt.subplots(1, 2, figsize=(FULL, 60 * MM),
                           gridspec_kw={"width_ratios": [1.15, 1]})
    a = ax[0]
    items = []
    for rule, name in [("node", "3×3, whole-node"), ("pc", "3×3, per-core")]:
        arr = no1_arrays(rule)
        (lc, cc), (ld, cdd) = arr["CEDT_P4"], arr["DTDE"]
        r = (lc.sum() / cc.sum()) / (ld.sum() / cdd.sum())
        lo, hi = boot_ratio(lc, cc, ld, cdd)
        items.append((name, r, lo, hi, C_D))
    orc = bil["oracle_percore"]
    items.append(("3×3, best config per class",
                  orc["dtde_charge"] / orc["class_best_charge"], None, None, GREY))
    items.append(("3×3, best config per job",
                  orc["dtde_charge"] / orc["job_best_charge"], None, None, GREY))
    arr, rep = no2_arrays("billed_asrun")
    (lc, cc), (ld, cdd) = arr["CEDT_P4"], arr["DTDE"]
    lo, hi = boot_ratio(lc, cc, ld, cdd)
    items.append(("8×8, reservation", rep["h_ratio_asrun"], lo, hi, C_C))
    y = np.arange(len(items))[::-1]
    for yy, (name, r, lo, hi, col) in zip(y, items):
        g = (r - 1) * 100
        if lo is None:
            a.plot(g, yy, "D", mfc="white", mec=col, ms=4.5, zorder=3)
            continue
        a.plot(g, yy, "o", color=col, ms=4.5, zorder=3)
        a.plot([(lo - 1) * 100, (hi - 1) * 100], [yy, yy], color=col, lw=1.4)
    a.set_yticks(y, [it[0] for it in items])
    a.axvline(5, color="0.3", ls="--", lw=0.6)
    a.axvline(0, color="0.8", lw=0.5)
    a.text(5.4, y[0] + 0.35, "required +5%", fontsize=6.3, va="center")
    a.set_xlabel("computing-centre gain in valid labels per charge (%)")
    panel(a, "(a)")

    a = ax[1]
    mk = load("timing_masking/mask_results.json")
    q = [r for r in mk["sweep"] if r["mask"] == "quant" and r["param"] > 0]
    qs = np.array([r["param"] for r in q])
    ida = np.array([r["worst_identity_acc"] for r in q])
    cost = np.array([r["cost_inflation"] for r in q]) * 100
    a.plot(qs, ida, "o-", ms=3, lw=1.0, color=C_D, label="identity accuracy, 3×3")
    a.axhline(mk["identity_limit"], color=C_D, ls="--", lw=0.6)
    a.text(qs.min(), mk["identity_limit"] + 0.02, "limit 3×3", fontsize=6.2,
           color=C_D)
    w2 = load("paired_comparison_2/results/wire_attack_results.json")
    a.plot(600, w2["CEDT_P4"]["identity_acc"], "D", ms=4.5, color=C_C,
           label="identity accuracy, 8×8", zorder=4)
    a.set_xscale("log")
    a.set_xlabel("completion-time quantum (s)")
    a.set_ylabel("identity accuracy")
    a.set_ylim(0, 1.05)
    b = a.twinx()
    b.plot(qs, cost, "s:", ms=2.5, lw=0.9, color=C_B, label="added cost, 3×3")
    b.set_ylabel("added compute cost (%)", color=C_B)
    b.tick_params(axis="y", colors=C_B)
    b.spines["right"].set_visible(True); b.spines["right"].set_color(C_B)
    b.spines["top"].set_visible(False)
    a.text(0.03, 0.45, "identity\naccuracy,\n3\u00d73", color=C_D,
           transform=a.transAxes,
           fontsize=6.5, va="center")
    a.text(600, 0.66, "8\u00d78 at 600 s", color=C_C, fontsize=6.5,
           va="bottom", ha="center")
    b.text(0.80, 0.92, "added cost", color=C_B, fontsize=6.5, ha="right",
           transform=b.transAxes,
           va="center")
    panel(a, "(b)")
    fig.tight_layout(w_pad=2.0)
    fig.savefig(HERE / "fig4_cases.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- figure 5
def fig_live2():
    arr, rep = no2_arrays("billed_asrun")
    fig, ax = plt.subplots(1, 2, figsize=(FULL, 58 * MM))
    a = ax[0]
    ld, cd_ = arr["DTDE"]; lc, cc = arr["CEDT_P4"]
    seeds = np.arange(len(ld))
    ed = cd_ / ld; ec = cc / lc
    for s in seeds:
        a.plot([0, 1], [ed[s], ec[s]], color="0.75", lw=0.6, zorder=1)
    a.scatter(np.zeros_like(ed), ed, s=10, color=C_D, zorder=2)
    a.scatter(np.ones_like(ec), ec, s=10, color=C_C, zorder=2)
    a.set_xticks([0, 1], ["no sharing\n(DTDE)", "broker + 1 bit\n(CEDT-P4)"])
    a.set_xlim(-0.4, 1.4)
    a.set_ylabel("per-core node-hours\nper valid label")
    lo, hi = boot_ratio(lc, cc, ld, cd_)
    print("fig5 CI", rep["h_ratio_asrun"], lo, hi)

    panel(a, "(a)")

    a = ax[1]
    top = 11.0
    for p in rep["pairs"]:
        d, c = p["dtde_first"], p["cedt_first"]
        if d is None and c is None:
            continue
        d = top if d is None else d
        c = top if c is None else c
        a.scatter(d, c, s=16, color=C_C if p["cedt_win"] else C_D,
                  marker="o" if p["cedt_win"] else "s", zorder=3)
    a.plot([0, top], [0, top], color="0.7", lw=0.6)
    a.set_xlim(0, top + 0.5); a.set_ylim(0, top + 0.5)
    a.set_xticks([0, 2, 4, 6, 8, top], ["0", "2", "4", "6", "8", "none"])
    a.set_yticks([0, 2, 4, 6, 8, top], ["0", "2", "4", "6", "8", "none"])
    a.set_xlabel("no sharing: per-core node-hours\nto first confirmed qualifier")
    a.set_ylabel("broker: per-core node-hours\nto first confirmed qualifier")
    n_none = sum(1 for p in rep["pairs"] if p["dtde_first"] is None and p["cedt_first"] is None)
    print("fig5 none", n_none)
    a.scatter([], [], s=16, color=C_C, marker="o", label="broker lower cost")
    a.scatter([], [], s=16, color=C_D, marker="s", label="no sharing lower cost")
    a.legend(frameon=False, loc="upper left")
    panel(a, "(b)")
    fig.tight_layout(w_pad=2.0)
    fig.savefig(HERE / "fig5_live2.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- annex
def fig_annex():
    fig, ax = plt.subplots(1, 3, figsize=(FULL, 54 * MM))
    s = load("centralization_surface/results/scaling.json")
    nw = s["meta"]["worlds"]
    N = s["meta"]["nparties"]
    a = ax[0]
    for arm, col, mk in [("CEDT-P4", C_C, "o")]:
        v = np.array([s["summary"][arm][str(n)]["win_win"] for n in N])
        ci = np.array([wilson(x, nw) for x in v])
        a.fill_between(N, ci[:, 0], ci[:, 1], color=col, alpha=0.18, lw=0)
        a.plot(N, v, marker=mk, ms=3, color=col, lw=1, label="P(win-win), P4")
    if "CEDT-P2" in s["summary"]:
        v = [s["summary"]["CEDT-P2"][str(n)]["r_id_acc"] for n in N]
        a.plot(N, v, marker="s", ms=3, color=C_D, lw=1,
               label="identity accuracy, P2")
        a.axhline(0.083, color=C_D, ls="--", lw=0.6)
    a.set_xlabel("research parties\nsharing one centre")
    a.set_xticks(N); a.set_ylim(0, 0.4)
    a.legend(frameon=False, loc="upper left")
    panel(a, "(a)")

    a = ax[1]
    sc = load("centralization_surface/results/schedules.json")
    key = "eps@P4|mean=0.5"
    names = ["ramp_up", "static", "mid_pulse", "ramp_down"]
    lab = ["late", "flat", "middle", "early"]
    nw2 = sc["meta"]["worlds"]
    v = np.array([sc["summary"][key][k]["win_win"] for k in names])
    ci = np.array([wilson(x, nw2) for x in v])
    a.bar(range(4), v, color=[GREY, GREY, GREY, C_C], width=0.6)
    a.errorbar(range(4), v, yerr=[v - ci[:, 0], ci[:, 1] - v], fmt="none",
               ecolor="0.15", elinewidth=0.6, capsize=1.5)
    a.set_xticks(range(4), lab)
    a.set_xlabel("when the broker is used\n(same average share)")
    a.set_ylabel("P(win-win)")
    panel(a, "(b)")

    a = ax[2]
    for lvl, col, mk in [("P1", C_D, "s"), ("P2", C_B, "^"), ("P3", C_G, "D"),
                         ("P4", C_C, "o")]:
        Z, L, ticks, nw3 = grid_from(lvl)
        v = Z[0, :]
        ci = np.array([wilson(x, nw3) for x in v])
        a.fill_between(ticks, ci[:, 0], ci[:, 1], color=col, alpha=0.15, lw=0)
        a.plot(ticks, v, marker=mk, ms=2.5, lw=0.9, color=col, label=lvl)
    a.set_xlabel("execution ε\n(τ = 0)")
    a.set_ylabel("P(win-win)")
    a.set_ylim(0, 0.4)
    a.legend(frameon=False, ncol=2, loc="upper left")
    panel(a, "(c)")
    fig.tight_layout(w_pad=1.2)
    fig.savefig(HERE / "figA1_annex.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- peer exchange
def fig_peer():
    """Research groups exchanging scientific results; no resource owner."""
    d = load("result_sharing/results/peer_exchange.json")
    cf = [c for c in d["configs"] if c["n"] == 3 and c["e_min"] == 1.5
          and c["rule"] == "mean" and not c["asym"]]
    cf.sort(key=lambda c: c["o"])
    o = np.array([c["o"] for c in cf])
    lv = [("X1", "named records", C_B, "^"), ("X2", "named verdicts", C_G, "D"),
          ("X3", "family counts", C_D, "s"),
          ("X1c", "public claims", C_C, "o")]
    bx = load("result_sharing/results/broker_exchange.json")
    bcf = sorted([c for c in bx["configs"] if c["n"] == 3], key=lambda c: c["o"])
    bd = load("result_sharing/results/broker_decoy.json")
    dcf = [c for c in bd["configs"] if c["o"] == 0.5][0]
    fig, ax = plt.subplots(1, 2, figsize=(FULL, 58 * MM))
    a = ax[0]
    for k, lab, col, mk in lv:
        q = np.array([c["grade"][k]["pw_world_p10_50_90"] for c in cf])
        m = np.array([np.mean(c["grade"][k]["pw_mean"]) for c in cf])
        a.fill_between(o, q[:, 0], q[:, 2], color=col, alpha=0.15, lw=0)
        a.plot(o, m, marker=mk, ms=3, lw=1, color=col, label=lab)
    ob = np.array([c["o"] for c in bcf])
    q = np.array([c["grade"]["Xb"]["pw_world_p10_50_90"] for c in bcf])
    m = np.array([np.mean(c["grade"]["Xb"]["pw_mean"]) for c in bcf])
    a.fill_between(ob, q[:, 0], q[:, 2], color="0.25", alpha=0.12, lw=0)
    a.plot(ob, m, marker="v", ms=3, lw=1, color="0.25", label="broker")
    g = dcf["grade"]["Xb_d0.5"]
    a.errorbar([0.5], [np.mean(g["pw_mean"])], yerr=[[np.mean(g["pw_mean"]) - g["pw_world_p10_50_90"][0]],
               [g["pw_world_p10_50_90"][2] - np.mean(g["pw_mean"])]], fmt="*", ms=6,
               color="0.25", mfc="white", lw=0.8, capsize=2, label="broker + decoys")
    a.axhline(0.60, color="0.2", ls="--", lw=0.6)
    a.set_xlabel("share of each list common to all groups")
    a.set_ylabel("paired win rate per group\n(first qualifier at lower spend)")
    a.set_xticks(o); a.set_ylim(0, 1)
    a.legend(frameon=True, facecolor="white", edgecolor="none", framealpha=1,
             loc="upper left", fontsize=6.0, handlelength=1.2, labelspacing=0.25,
             borderaxespad=0.2)
    panel(a, "(a)")

    a = ax[1]
    a.add_patch(plt.Rectangle((0.40, 0.60), 0.20, 0.40, color=C_G, alpha=0.12, lw=0))
    a.text(0.41, 0.95, "all groups gain,\nlists hidden", fontsize=6.3, va="top")
    for k, lab, col, mk in lv:
        for c in cf:
            g = c["grade"][k]
            x = np.mean(g["auc_pool"]); y = np.mean(g["pw_mean"])
            a.scatter(x, y, s=8 + 30 * c["o"], color=col, marker=mk, lw=0, alpha=0.9)
    for c in bcf:
        g = c["grade"]["Xb"]
        a.scatter(np.mean(g["auc_pool"]), np.mean(g["pw_mean"]), s=8 + 30 * c["o"],
                  color="0.25", marker="v", lw=0, alpha=0.9)
    for qq in (0.1, 0.2, 0.3, 0.5):
        g = dcf["grade"][f"Xb_d{qq}"]
        a.scatter(np.mean(g["auc_pool"]), np.mean(g["pw_mean"]), s=8 + 30 * 0.5,
                  color="0.25", marker="*", facecolor="white", lw=0.6)
    a.annotate("decoys\nq = 0.1 to 0.5", xy=(0.47, 0.585), xytext=(0.66, 0.30),
               fontsize=6.3, arrowprops=dict(arrowstyle="-", lw=0.5, color="0.3"))
    a.axvline(0.60, color="0.2", ls="--", lw=0.6)
    a.axhline(0.60, color="0.2", ls="--", lw=0.6)
    a.set_xlim(0.40, 1.0); a.set_ylim(0, 1)
    a.set_xlabel("membership AUC of a group's list\n(other groups pooled)")
    a.set_ylabel("paired win rate per group")
    a.text(0.98, 0.97, "marker size: list overlap", fontsize=6.3, ha="right",
           va="top", transform=a.transAxes)
    panel(a, "(b)")
    fig.tight_layout(w_pad=1.5)
    fig.savefig(HERE / "fig6_peer.pdf")
    plt.close(fig)


if __name__ == "__main__":
    fig_contracts()
    fig_metric()
    fig_surface()
    fig_cases()
    fig_live2()
    fig_annex()
    fig_peer()
    print("ok")
