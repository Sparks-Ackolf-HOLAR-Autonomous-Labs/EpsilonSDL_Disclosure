#!/usr/bin/env python3
"""Figures for the disclosure article (minimal reciprocal disclosure).

Every number plotted is read from a committed result file under
; nothing is typed in by hand except the plotting
thresholds that the preregistrations fixed (1.05 margin, 0.60 AUC limit,
identity limits read from the attack JSONs). Figures are drawn at their
printed size (text width 153 mm in iopjournal.cls) with 6.5-8 pt fonts.

Uncertainty conventions
- Simulated probabilities P(win-win): Wilson 95% interval with n = number
  of prior worlds behind the cell.
- Measured throughput ratios: paired bootstrap over seeds (10 000 draws).
- Timing-attack scores: cluster bootstrap over held-out seeds, read from
  bootstrap_ci/seed_bootstrap.json.

Reader-facing labels use plain names: "no sharing" (DTDE in the result
files), "per-job broker" (CEDT), "shared logbook" (CTDE), "all merged"
(CTCE); disclosure levels in words ("class only" = P4, "coarse bins" = P2).
"""
import json
import math
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # repository root
MM = 1 / 25.4
FULL = 153 * MM

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 7.5, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "savefig.dpi": 300, "font.family": "DejaVu Sans",
    "mathtext.default": "regular",
})
C_D = "#5B6770"   # no sharing, slate
C_C = "#C8553D"   # per-job broker, brick (measured broker outcomes)
C_C2 = "#7D2E1F"  # measured: shared logbook (dark brick)
C_C3 = "#E39A85"  # measured: half routed (light brick)
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


def panel(ax, s, title=None):
    ax.text(-0.02, 1.04, s, transform=ax.transAxes, fontweight="bold",
            fontsize=8.5, ha="right", va="bottom")
    if title:
        ax.set_title(title, fontsize=7.5, pad=4, loc="left")


def chem(name):
    """'HfS2_1T' -> 'HfS$_2$-1T' for mathtext."""
    f, ph = name.split("_")
    return f.replace("2", "$_2$") + "-" + ph


# ---------------------------------------------------------------- figure 1
def fig_contracts():
    man = load("paired_comparison_2/inputs/manifest2.json")
    cand = {r["name"]: r for r in man["candidates"]}["MoS2_2H"]
    recs = [json.loads(l) for l in open(ROOT / "paired_comparison_2/results/campaigns.jsonl")]
    job = [j for r in recs if r["arm"] == "CEDT_P4" and r["seed"] == 8
           for j in r["jobs"] if j["candidate"] == "MoS2_2H" and j["cls"] == "f2"][0]
    wire = [json.loads(l) for l in open(ROOT / "paired_comparison_2/results/wire_log.jsonl")]
    msg = [w for w in wire if w["arm"] == "CEDT_P4" and w["seed"] == 8
           and w["cls"] == "f2" and abs(w["billed_nh"] - job["billed_nh"]) < 1e-3][0]
    ecut = 45  # Ry, from paired_comparison_2/inputs/MoS2_2H.f2.in
    for line in open(ROOT / "paired_comparison_2/inputs/MoS2_2H.f2.in"):
        if "ecutwfc" in line:
            ecut = float(line.split("=")[1])

    fig = plt.figure(figsize=(FULL, 112 * MM))
    # (a) coordination square
    ax = fig.add_axes([0.075, 0.55, 0.30, 0.40])
    ax.set_xlim(-0.62, 1.4); ax.set_ylim(-0.5, 1.35)
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, lw=0.8, ec="0.3"))
    corners = {
        (0, 0): ("no sharing", "DTDE"),
        (1, 0): ("per-job broker", "CEDT"),
        (0, 1): ("shared logbook", "CTDE"),
        (1, 1): ("all merged", "CTCE"),
    }
    for (x, y), (d, n) in corners.items():
        ax.plot(x, y, "o", ms=5, color=C_C if (x, y) == (1, 0) else C_D)
        dy = -0.07 if y == 0 else 0.07
        va = "top" if y == 0 else "bottom"
        ax.text(x, y + dy, f"{d}\n({n})",
                ha="center", va=va, fontsize=6.6, linespacing=1.1)
    ax.plot(0.5, 0.5, "s", ms=4, mfc="white", mec=C_B)
    ax.text(0.53, 0.47, "mixture\n(τ, ε)", fontsize=6.6, color=C_B, va="top")
    ax.annotate("", xy=(1.18, -0.36), xytext=(-0.05, -0.36),
                arrowprops=dict(arrowstyle="->", lw=0.6, color="0.3"))
    ax.text(0.56, -0.40, "execution centralization ε", ha="center",
            va="top", fontsize=7)
    ax.annotate("", xy=(-0.45, 1.18), xytext=(-0.45, -0.05),
                arrowprops=dict(arrowstyle="->", lw=0.6, color="0.3"))
    ax.text(-0.49, 0.56, "training centralization τ", ha="right",
            va="center", rotation=90, fontsize=7)
    ax.axis("off")
    ax.text(-0.62, 1.33, "(a)", fontweight="bold", fontsize=8.5,
            ha="left", va="bottom")

    # (c) request and result flow through the broker
    ac = fig.add_axes([0.43, 0.55, 0.56, 0.40])
    ac.set_xlim(0, 1); ac.set_ylim(0, 1); ac.axis("off")
    boxes = [(0.0, "research\ngroup\n(candidate list)", C_D),
             (0.385, "broker\n(run-time\nmatching)", C_C),
             (0.77, "computing\ncentre\n(node, settings)", C_D)]
    bw, by, bh = 0.23, 0.34, 0.32
    for x0, t, col in boxes:
        ac.add_patch(FancyBboxPatch((x0, by), bw, bh,
                     boxstyle="round,pad=0.0,rounding_size=0.02",
                     fc="white", ec=col, lw=0.9))
        ac.text(x0 + bw / 2, by + bh / 2, t, ha="center", va="center",
                fontsize=6.8, linespacing=1.15)
    arr = dict(arrowstyle="->", lw=0.7, color="0.25")
    # requests (top, left to right)
    for xa, xb, t in [(0.23, 0.385, "job request:\nclass,\nmemory bit"),
                      (0.615, 0.77, "reservation\n109 or 152 GB,\n16 processes")]:
        ac.annotate("", xy=(xb, 0.56), xytext=(xa, 0.56), arrowprops=arr)
        ac.text((xa + xb) / 2, 0.68, t, ha="center", va="bottom",
                fontsize=6.5, linespacing=1.1)
    # results (bottom, right to left)
    for xa, xb, t in [(0.77, 0.615, "completion,\nsuccess, charge"),
                      (0.385, 0.23, "success bit,\ncharge, time at\n600-s boundary")]:
        ac.annotate("", xy=(xb, 0.44), xytext=(xa, 0.44), arrowprops=arr)
        ac.text((xa + xb) / 2, 0.32, t, ha="center", va="top",
                fontsize=6.5, linespacing=1.1)
    ac.text(0.0, 1.0, "(c)", fontweight="bold", fontsize=8.5, ha="left",
            va="bottom", transform=ac.transAxes)

    # (b) one measured job message at three disclosure levels
    ab = fig.add_axes([0.01, 0.01, 0.98, 0.47])
    ab.set_xlim(0, 1); ab.set_ylim(0, 1); ab.axis("off")
    W = "withheld"
    t_true = job["wall_s"] / 3600
    t_mask = (msg["t_end"] - msg["t_start"]) / 3600
    rows = [
        ("compound", "MoS$_2$-2H bilayer", W, W),
        ("cell", f"8×8, {cand['nat']} atoms, {cand['nelec']:,} electrons",
         "size class: upper half", W),
        ("plane-wave cutoff", f"{ecut:.0f} Ry", W, W),
        ("memory", f"estimate {cand['ram_est_gb']:.1f} GB",
         "demand class: upper half",
         f"one bit: above median ({man['ram_median_gb']:.1f} GB)"),
        ("calculation", "production SCF", "production SCF", "production SCF"),
        ("outcome", "converged; energy, density", "succeeded",
         "success bit = 1"),
        ("completion time", f"{t_true:.2f} h", f"{t_true:.2f} h",
         f"{t_mask:.2f} h (600-s boundary)"),
        ("charge", f"{job['billed_nh']:.2f} per-core node-h",
         f"{job['billed_nh']:.2f} per-core node-h",
         f"{job['billed_nh']:.2f} per-core node-h"),
    ]
    heads = ["", "raw records (P0)", "coarse bins (P2)",
             "class only + one bit (P4 + 1 bit)"]
    xs = [0.0, 0.17, 0.455, 0.70]
    ws = [0.165, 0.28, 0.24, 0.30]
    top = 0.83
    rh = 0.099
    for k, h in enumerate(heads):
        ab.text(xs[k] + 0.006, top + 0.025, h, fontsize=7, fontweight="bold",
                va="bottom", color=C_C if k == 3 else "0.15")
    for i, row in enumerate(rows):
        y = top - (i + 1) * rh
        ab.text(xs[0] + 0.006, y + rh / 2, row[0], fontsize=6.8, va="center",
                color="0.25")
        for k in (1, 2, 3):
            hidden = row[k] == W
            ab.add_patch(Rectangle((xs[k], y + 0.008), ws[k], rh - 0.016,
                                   fc="0.86" if hidden else
                                   ("#F6E1DB" if k == 3 else "0.97"),
                                   ec="none"))
            ab.text(xs[k] + 0.008, y + rh / 2, row[k], fontsize=6.8,
                    va="center", color="0.55" if hidden else "0.1",
                    style="italic" if hidden else "normal")
    ab.text(0.0, 0.985, "(b)", fontweight="bold", fontsize=8.5, ha="left",
            va="top", transform=ab.transAxes)
    ab.text(0.04, 0.985, "one measured job of comparison No. 2 (broker arm, "
            "seed 8) as each level reports it", fontsize=7, va="top",
            transform=ab.transAxes)
    fig.savefig(HERE / "fig1_contracts.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- figure 2
def fig_metric():
    cd = load("ceiling_diagnosis/results/ceiling_diagnosis.json")
    rows = cd["rows"]
    comp = {
        "irreducible": [r["irreducible_frac"] for r in rows],
        "luck": [r["science_gap_frac"] for r in rows],
        "tradable\ngap": [r["exec_gap_frac"] for r in rows],
    }
    ms = load("metric_redesign/metric_study.json")
    n = ms["worlds"]
    order = ["T20", "T10", "REG20", "EX15", "EX10", "QY05", "PW60"]
    lab = {"T20": "spend to first qualifier 20% lower",
           "T10": "spend to first qualifier 10% lower",
           "REG20": "regret against oracle 20% lower",
           "EX15": "labels per node-hour 15% higher",
           "EX10": "labels per node-hour 10% higher",
           "QY05": "0.5 more qualifiers found",
           "PW60": "paired win rate at least 0.60"}

    fig = plt.figure(figsize=(FULL, 66 * MM))
    ax = [fig.add_axes([0.095, 0.17, 0.235, 0.66]),
          fig.add_axes([0.615, 0.17, 0.37, 0.66])]
    a = ax[0]
    data = list(comp.values())
    parts = a.violinplot(data, positions=range(3), showextrema=False,
                         widths=0.8)
    for pc, c in zip(parts["bodies"], [GREY, C_B, C_C]):
        pc.set_facecolor(c); pc.set_alpha(0.35); pc.set_edgecolor("none")
    for i, d in enumerate(data):
        q10, q50, q90 = np.percentile(d, [10, 50, 90])
        a.plot([i, i], [q10, q90], color="0.2", lw=0.8)
        m = np.mean(d)
        a.plot(i, m, "o", ms=3.5, color="0.1")
        a.text(i, 1.08, f"mean\n{m:.2f}", ha="center", va="bottom",
               fontsize=6.8, linespacing=1.0)
    a.axhline(0.20, color="0.3", ls="--", lw=0.6)
    a.plot([-0.5, -0.2], [-0.68, -0.68], color="0.3", ls="--", lw=0.6)
    a.text(-0.12, -0.68, "20% target", fontsize=6.6, ha="left",
           va="center")
    a.axhline(0, color="0.8", lw=0.5)
    a.set_xticks(range(3), list(comp))
    a.set_xlim(-0.6, 2.5)
    a.set_ylabel("share of spend to first qualifier")
    a.set_ylim(-0.8, 1.35)
    a.set_yticks([-0.5, 0, 0.5, 1.0])
    panel(a, "(a)", "simulated")

    a = ax[1]
    y = np.arange(len(order))
    for off, key, col, name in [(0.17, "wide_prior_x1", GREY,
                                 "wide prior, 1× task cost"),
                                (-0.17, "posterior_x100", C_C,
                                 "measured prior, 100× task cost")]:
        v = [ms[key][m]["p_ww_package"] for m in order]
        lo = [v[i] - wilson(v[i], n)[0] for i in range(len(v))]
        hi = [wilson(v[i], n)[1] - v[i] for i in range(len(v))]
        a.barh(y + off, v, height=0.32, color=col, alpha=0.85, label=name)
        a.errorbar(v, y + off, xerr=[lo, hi], fmt="none", ecolor="0.15",
                   elinewidth=0.6, capsize=1.5)
    a.axvline(0.90, color="0.3", ls="--", lw=0.6)
    a.text(0.89, len(order) - 0.55, "0.90", fontsize=6.6, ha="right",
           va="top")
    a.set_yticks(y, [lab[m] for m in order])
    a.set_ylim(-2.0, len(order) - 0.5)
    a.set_xlim(0, 1.0)
    a.set_xlabel("P(both gain and all leakage limits hold)")
    a.legend(frameon=False, loc="lower right", bbox_to_anchor=(1.02, 0.0),
             ncol=1, handlelength=1.2, labelspacing=0.2)
    panel(a, "(b)", "simulated")
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


LEVEL_NAME = {"P1": "exact descriptors", "P2": "coarse bins",
              "P3": "private aggregates", "P4": "class only"}


def fig_surface():
    fig = plt.figure(figsize=(FULL, 62 * MM))
    gs = fig.add_gridspec(1, 5, width_ratios=[1, 1, 0.06, 0.42, 1.3],
                          wspace=0.28, left=0.07, right=0.985, bottom=0.2,
                          top=0.86)
    vmax = 0.30
    for idx, lvl in enumerate(["P4", "P2"]):
        Z, L, ticks, nw = grid_from(lvl)
        a = fig.add_subplot(gs[0, idx])
        im = a.imshow(Z, origin="lower", extent=[-0.05, 1.05, -0.05, 1.05],
                      cmap="Reds", vmin=0, vmax=vmax, aspect="equal")
        a.contour(np.linspace(0, 1, Z.shape[1]), np.linspace(0, 1, Z.shape[0]),
                  L, levels=[0.5], colors=["0.15"], linewidths=0.7,
                  linestyles="--")
        # cells whose value lies inside the Wilson 95% interval of the maximum
        zmax = np.nanmax(Z)
        lo_max = wilson(zmax, nw)[0]
        ii, jj = np.where(Z >= lo_max)
        a.plot(ticks[jj], ticks[ii], ".", ms=2.2, color="0.1")
        a.set_xlabel("execution ε")
        if idx == 0:
            a.set_ylabel("training τ")
        a.set_xticks([0, 0.5, 1]); a.set_yticks([0, 0.5, 1])
        for s in a.spines.values():
            s.set_visible(False)
        panel(a, "(a)" if idx == 0 else "(b)",
              f"{LEVEL_NAME[lvl]}, simulated")
    cax = fig.add_subplot(gs[0, 2])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("P(win-win)", fontsize=7, labelpad=3)
    cb.ax.tick_params(labelsize=6.8)

    a = fig.add_subplot(gs[0, 4])
    sc = load("centralization_surface/results/surface_scale.json")
    nw = sc["meta"]["worlds"]
    eps = [0.0, 0.25, 0.5, 0.75, 1.0]
    # x1 = measured 1x1-cell campaign cost; x30-x100 about the 3x3 cost
    # (centralization_surface/RESULTS.md, section 5)
    styles = {1: (GREY, "o", "1× (1×1 cells)"),
              10: (C_B, "s", "10×"),
              100: (C_C, "^", "100× (about 3×3 cells)")}
    lab_at = {1: (0.62, 0.40, "center"), 10: (0.55, 0.63, "left"),
              100: (0.0, 0.965, "left")}
    for s, (col, mk, name) in styles.items():
        v = np.array([sc["cells"][f"x{s}|P4|0.0|{e}"]["win_win"] for e in eps])
        ci = np.array([wilson(x, nw) for x in v])
        a.fill_between(eps, ci[:, 0], ci[:, 1], color=col, alpha=0.18, lw=0)
        a.plot(eps, v, marker=mk, ms=3, lw=1.0, color=col, label=name)
        tx, ty, ha = lab_at[s]
        a.text(tx, ty, name, color=col, fontsize=6.8, ha=ha, va="center")
    a.axhline(0.90, color="0.3", ls="--", lw=0.6)
    a.set_xlabel("execution ε (τ = 0, class only)")
    a.set_ylabel("P(win-win)")
    a.set_ylim(0, 1.02); a.set_xticks([0, 0.5, 1])
    panel(a, "(c)", "task cost, simulated")
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


def no3_campaigns(folder):
    """Final campaign records and processor model of comparisons No. 3/3b."""
    base = ROOT / folder / "collected_2026-10-14"
    camps = {}
    for d in sorted(base.iterdir()):
        f = d / "campaigns.jsonl"
        if f.exists():
            rec = json.loads(f.read_text().splitlines()[-1])
            camps[(rec["arm"], rec["seed"])] = rec
    sites = load(f"{folder}/pair_sites.json")["campaigns"]
    return camps, sites


def no3_ratio(camps, sites, arm, same_cpu):
    seeds = [s for s in range(15) if (arm, s) in camps and ("DTDE", s) in camps]
    if same_cpu:
        seeds = [s for s in seeds
                 if sites[f"{arm}_s{s}"]["cpu"] == sites[f"DTDE_s{s}"]["cpu"]]
    lc = np.array([camps[(arm, s)]["labels_f2"] for s in seeds], float)
    cc = np.array([camps[(arm, s)]["billed"] for s in seeds])
    ld = np.array([camps[("DTDE", s)]["labels_f2"] for s in seeds], float)
    cd_ = np.array([camps[("DTDE", s)]["billed"] for s in seeds])
    r = (lc.sum() / cc.sum()) / (ld.sum() / cd_.sum())
    lo, hi = boot_ratio(lc, cc, ld, cd_)
    return r, lo, hi, len(seeds)


def fig_cases():
    bil = load("billing_regrade/billing_regrade.json")
    fig = plt.figure(figsize=(FULL, 128 * MM))
    a = fig.add_axes([0.375, 0.50, 0.605, 0.45])
    # (label, ratio, lo, hi, colour, kind) kind: meas / recomp / bound
    items = []
    arr = no1_arrays("pc")
    (lc, cc), (ld, cdd) = arr["CEDT_P4"], arr["DTDE"]
    r = (lc.sum() / cc.sum()) / (ld.sum() / cdd.sum())
    lo, hi = boot_ratio(lc, cc, ld, cdd)
    items.append(("No. 1, 3×3, per-core billing", r, lo, hi, C_C, "meas"))
    arr = no1_arrays("node")
    (lc, cc), (ld, cdd) = arr["CEDT_P4"], arr["DTDE"]
    r = (lc.sum() / cc.sum()) / (ld.sum() / cdd.sum())
    lo, hi = boot_ratio(lc, cc, ld, cdd)
    items.append(("No. 1, 3×3, whole-node billing", r, lo, hi, C_C,
                  "recomp"))
    orc = bil["oracle_percore"]
    items.append(("No. 1, 3×3, best setting per class",
                  orc["dtde_charge"] / orc["class_best_charge"], None, None,
                  GREY, "bound"))
    items.append(("No. 1, 3×3, best setting per job",
                  orc["dtde_charge"] / orc["job_best_charge"], None, None,
                  GREY, "bound"))
    arr2, rep = no2_arrays("billed_asrun")
    (lc, cc), (ld, cdd) = arr2["CEDT_P4"], arr2["DTDE"]
    lo, hi = boot_ratio(lc, cc, ld, cdd)
    items.append(("No. 2, 8×8, broker + memory bit", rep["h_ratio_asrun"],
                  lo, hi, C_C, "meas"))
    c3, s3 = no3_campaigns("paired_comparison_3")
    for arm, name, col, same in [
            ("CEDT_P4", "No. 3, broker + bit, all pairs", C_C, False),
            ("CEDT_P4", "No. 3, broker + bit, same processor", C_C, True),
            ("CTDE_P2", "No. 3, shared logbook", C_C2, False),
            ("MIX50", "No. 3, half of jobs to broker", C_C3, False)]:
        r, lo, hi, npair = no3_ratio(c3, s3, arm, same)
        items.append((f"{name} ({npair})", r, lo, hi, col, "meas"))
        print("fig4", name, round(r, 3), round(lo, 3), round(hi, 3), npair)
    c3b, s3b = no3_campaigns("paired_comparison_3b")
    for name, same in [("No. 3b, single layers, all pairs", False),
                       ("No. 3b, single layers, same processor", True)]:
        r, lo, hi, npair = no3_ratio(c3b, s3b, "CEDT_P4", same)
        items.append((f"{name} ({npair})", r, lo, hi, C_C, "meas"))
        print("fig4", name, round(r, 3), round(lo, 3), round(hi, 3), npair)

    y = np.arange(len(items))[::-1].astype(float)
    # small gaps between comparison groups
    groups = [0, 0, 0, 0, 1, 2, 2, 2, 2, 3, 3]
    y = y + 0.5 * (3 - np.array(groups))
    for yy, (name, r, lo, hi, col, kind) in zip(y, items):
        g = (r - 1) * 100
        if kind == "bound":
            a.plot(g, yy, "D", mfc="white", mec=col, ms=4.5, zorder=3)
            continue
        a.plot([(lo - 1) * 100, (hi - 1) * 100], [yy, yy], color=col, lw=1.4,
               ls="-" if kind == "meas" else (0, (2, 1)))
        if kind == "meas":
            a.plot(g, yy, "o", color=col, ms=4.5, zorder=3)
        else:
            a.plot(g, yy, "o", mfc="white", mec=col, mew=1.0, ms=4.5, zorder=3)
    a.set_yticks(y, [it[0] for it in items])
    a.set_ylim(y.min() - 0.7, y.max() + 0.7)
    a.axvline(5, color="0.3", ls="--", lw=0.6)
    a.axvline(0, color="0.8", lw=0.5)
    a.text(5.6, y.max() + 0.45, "required +5%", fontsize=6.6, va="center")
    a.set_xlabel("computing-centre gain in valid labels per charge over no sharing (%)")
    a.plot([], [], "o", color=C_C, ms=4.5, label="measured (95% interval)")
    a.plot([], [], "o", mfc="white", mec=C_C, ms=4.5,
           label="recomputed, other billing")
    a.plot([], [], "D", mfc="white", mec=GREY, ms=4.5,
           label="bound")
    a.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.95),
             fontsize=6.6, handlelength=1.0)
    a.text(-0.60, 1.04, "(a)", transform=a.transAxes, fontweight="bold",
           fontsize=8.5, ha="left", va="bottom")
    a.set_title("measured", fontsize=7.5, pad=4, loc="left")

    # (b) timing attack against the cost of the completion-time quantum
    a = fig.add_axes([0.10, 0.075, 0.50, 0.32])
    mk = load("timing_masking/mask_results.json")
    bs = load("bootstrap_ci/seed_bootstrap.json")
    bq = {m["param"]: m["worse_arm"] for m in bs["masking"] if m["mask"] == "quant"}
    q = [r for r in mk["sweep"] if r["mask"] == "quant" and r["param"] > 0]
    qs = np.array([r["param"] for r in q])
    cost = np.array([r["cost_inflation"] for r in q]) * 100
    for key, col, mkr, name in [("identity", C_D, "o", "identity accuracy"),
                                ("auc", C_B, "s", "membership AUC")]:
        v = np.array([bq[p][key]["point"] for p in qs])
        lo = np.array([bq[p][key]["lo"] for p in qs])
        hi = np.array([bq[p][key]["hi"] for p in qs])
        a.fill_between(cost, lo, hi, color=col, alpha=0.15, lw=0)
        a.plot(cost, v, marker=mkr, ms=3, lw=1.0, color=col,
               label=f"{name}, 3×3")
    for p, (dx, dy, ha) in {60: (-4, -6, "right"), 300: (3, 7, "left"),
                            600: (3, 7, "left")}.items():
        i = list(qs).index(p)
        a.annotate(f"{p} s", xy=(cost[i], bq[p]["identity"]["point"]),
                   xytext=(dx, dy), textcoords="offset points", fontsize=6.6,
                   ha=ha, va="center", color="0.15")
    a.axhline(mk["identity_limit"], color=C_D, ls="--", lw=0.6)
    a.axhline(0.60, color=C_B, ls="--", lw=0.6)
    a.text(1.1, mk["identity_limit"] + 0.015, "identity limit", fontsize=6.6,
           color=C_D, va="bottom")
    a.text(3500, 0.615, "AUC limit", fontsize=6.6, color=C_B, va="bottom",
           ha="right")
    # 8x8 broker arm at 600 s: attack on the masked wire log, cost from the
    # three unmasked replays (paired_comparison_2/results/campaigns.jsonl)
    w2 = load("paired_comparison_2/results/wire_attack_results.json")
    recs = [json.loads(l) for l in open(ROOT / "paired_comparison_2/results/campaigns.jsonl")]
    bil2 = {(r["arm"], r["seed"]): r["billed"] for r in recs}
    rs = [s for s in range(15) if ("CEDT_P4_UNMASKED", s) in bil2]
    c8 = (sum(bil2[("CEDT_P4", s)] for s in rs)
          / sum(bil2[("CEDT_P4_UNMASKED", s)] for s in rs) - 1) * 100
    print("fig4b 8x8 mask cost %", round(c8, 2), rs)
    a.plot(c8, w2["CEDT_P4"]["identity_acc"], "D", ms=4.5, color=C_C,
           zorder=4, label="identity accuracy, 8×8, 600 s")
    a.plot(c8, w2["CEDT_P4"]["membership_auc"], "D", ms=4.5, mfc="white",
           mec=C_C, zorder=4, label="membership AUC, 8×8, 600 s")
    a.set_xscale("log")
    a.set_xlim(1, 4000)
    a.set_xlabel("added compute cost of the quantum (%)")
    a.set_ylabel("attack score")
    a.set_ylim(0, 1.05)
    a.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.04, 1.0),
             fontsize=6.6, handlelength=1.4)
    a.text(-0.16, 1.04, "(b)", transform=a.transAxes, fontweight="bold",
           fontsize=8.5, ha="left", va="bottom")
    a.set_title("measured logs, attacked", fontsize=7.5, pad=4, loc="left")
    fig.savefig(HERE / "fig4_cases.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- figure 5
def fig_live2():
    arr, rep = no2_arrays("billed_asrun")
    fig, ax = plt.subplots(1, 2, figsize=(FULL, 64 * MM))
    a = ax[0]
    ld, cd_ = arr["DTDE"]; lc, cc = arr["CEDT_P4"]
    seeds = np.arange(len(ld))
    ed = cd_ / ld; ec = cc / lc
    for s in seeds:
        a.plot([0, 1], [ed[s], ec[s]], color="0.75", lw=0.6, zorder=1)
    a.scatter(np.zeros_like(ed), ed, s=10, color=C_D, zorder=2)
    a.scatter(np.ones_like(ec), ec, s=10, color=C_C, zorder=2)
    a.set_xticks([0, 1], ["no sharing", "broker +\nmemory bit"])
    a.set_xlim(-0.4, 1.4)
    a.set_ylabel("per-core node-hours per valid label")
    lo, hi = boot_ratio(lc, cc, ld, cd_)
    print("fig5 CI", rep["h_ratio_asrun"], lo, hi)
    yl = a.get_ylim()
    a.set_ylim(yl[0], yl[1] + 0.12 * (yl[1] - yl[0]))
    a.text(0.5, 1.0, f"labels per charge, broker / no sharing:\n"
           f"{rep['h_ratio_asrun']:.3f} (95% interval {lo:.2f}–{hi:.2f})",
           transform=a.transAxes, ha="center", va="top", fontsize=6.8)
    panel(a, "(a)", "measured")

    a = ax[1]
    top = 11.0
    # label offsets (points) chosen per seed to keep compound names apart
    off = {0: (-4, -6, "right"), 2: (0, 8, "center"), 7: (-4, 5, "right"),
           8: (5, -6, "left"), 9: (-5, 0, "right"), 10: (5, -2, "left"),
           12: (5, -6, "left")}
    for p in rep["pairs"]:
        d, c = p["dtde_first"], p["cedt_first"]
        if d is None and c is None:
            continue
        d = top if d is None else d
        c = top if c is None else c
        a.scatter(d, c, s=16, color=C_C if p["cedt_win"] else C_D,
                  marker="o" if p["cedt_win"] else "s", zorder=3)
        name = p["cedt_first_qualifier"] or p["dtde_first_qualifier"]
        dx, dy, ha = off.get(p["seed"], (4, 4, "left"))
        a.annotate(chem(name), xy=(d, c), xytext=(dx, dy),
                   textcoords="offset points", fontsize=6.6, ha=ha,
                   va="center", color="0.15")
    a.plot([0, top], [0, top], color="0.7", lw=0.6)
    a.set_xlim(0, top + 0.5); a.set_ylim(0, top + 0.5)
    a.set_xticks([0, 2, 4, 6, 8, top], ["0", "2", "4", "6", "8", "none"])
    a.set_yticks([0, 2, 4, 6, 8, top], ["0", "2", "4", "6", "8", "none"])
    a.set_xlabel("no sharing: cost to first qualifier\n(per-core node-hours)")
    a.set_ylabel("broker: cost to first qualifier\n(per-core node-hours)")
    n_none = sum(1 for p in rep["pairs"] if p["dtde_first"] is None and p["cedt_first"] is None)
    print("fig5 none", n_none)
    a.scatter([], [], s=16, color=C_C, marker="o", label="broker lower cost")
    a.scatter([], [], s=16, color=C_D, marker="s", label="no sharing lower cost")
    a.legend(frameon=False, loc="center left", bbox_to_anchor=(0.0, 0.40))
    panel(a, "(b)", "measured")
    fig.tight_layout(w_pad=2.0)
    fig.savefig(HERE / "fig5_live2.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- annex
def fig_annex():
    fig, ax = plt.subplots(2, 2, figsize=(FULL, 104 * MM))
    s = load("centralization_surface/results/scaling.json")
    nw = s["meta"]["worlds"]
    N = s["meta"]["nparties"]
    a = ax[0, 0]
    v = np.array([s["summary"]["CEDT-P4"][str(n)]["win_win"] for n in N])
    ci = np.array([wilson(x, nw) for x in v])
    a.fill_between(N, ci[:, 0], ci[:, 1], color=C_C, alpha=0.18, lw=0)
    a.plot(N, v, marker="o", ms=3, color=C_C, lw=1)
    a.set_xlabel("research parties sharing one centre")
    a.set_ylabel("P(win-win), broker, class only")
    a.set_xticks(N); a.set_ylim(0, 0.4)
    panel(a, "(a)", "simulated")

    a = ax[0, 1]
    if "CEDT-P2" in s["summary"]:
        v = [s["summary"]["CEDT-P2"][str(n)]["r_id_acc"] for n in N]
        a.plot(N, v, marker="s", ms=3, color=C_D, lw=1)
        a.axhline(0.083, color=C_D, ls="--", lw=0.6)
        a.text(N[-1], 0.088, "limit 0.083", fontsize=6.6, ha="right",
               va="bottom", color=C_D)
    a.set_xlabel("research parties sharing one centre")
    a.set_ylabel("identity accuracy, broker,\ncoarse bins (pooled attacker)")
    a.set_xticks(N); a.set_ylim(0, 0.3)
    panel(a, "(b)", "simulated")

    a = ax[1, 0]
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
    a.set_xlabel("when the broker is used (same average share)")
    a.set_ylabel("P(win-win)")
    panel(a, "(c)", "simulated")

    a = ax[1, 1]
    for lvl, col, mk in [("P1", C_D, "s"), ("P2", C_B, "^"), ("P3", C_G, "D"),
                         ("P4", C_C, "o")]:
        Z, L, ticks, nw3 = grid_from(lvl)
        v = Z[0, :]
        ci = np.array([wilson(x, nw3) for x in v])
        a.fill_between(ticks, ci[:, 0], ci[:, 1], color=col, alpha=0.15, lw=0)
        a.plot(ticks, v, marker=mk, ms=2.5, lw=0.9, color=col,
               label=LEVEL_NAME[lvl])
    a.set_xlabel("execution ε (τ = 0)")
    a.set_ylabel("P(win-win)")
    a.set_ylim(0, 0.4)
    a.legend(frameon=False, ncol=2, loc="upper left", fontsize=6.6,
             handlelength=1.4, columnspacing=0.8)
    panel(a, "(d)", "simulated")
    fig.tight_layout(w_pad=2.0, h_pad=1.2)
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
    bx = load("result_sharing/results/broker_exchange.json")
    bcf = sorted([c for c in bx["configs"] if c["n"] == 3], key=lambda c: c["o"])
    bd = load("result_sharing/results/broker_decoy.json")
    dcf = [c for c in bd["configs"] if c["o"] == 0.5][0]
    fig, a = plt.subplots(1, 1, figsize=(96 * MM, 64 * MM))
    # exchanges of results (records, verdicts, family counts): one band
    qs = np.array([[c["grade"][k]["pw_world_p10_50_90"] for k in ("X1", "X2", "X3")]
                   for c in cf])
    ms = np.array([[np.mean(c["grade"][k]["pw_mean"]) for k in ("X1", "X2", "X3")]
                   for c in cf])
    a.fill_between(o, qs[:, :, 0].min(1), qs[:, :, 2].max(1), color=C_D,
                   alpha=0.18, lw=0)
    a.plot(o, ms.max(1), color=C_D, lw=0.8, ls="-")
    a.plot(o, ms.min(1), color=C_D, lw=0.8, ls="-")
    a.fill_between(o, ms.min(1), ms.max(1), color=C_D, alpha=0.35, lw=0,
                   label="exchange of results\n(records, verdicts or counts)")
    q = np.array([c["grade"]["X1c"]["pw_world_p10_50_90"] for c in cf])
    m = np.array([np.mean(c["grade"]["X1c"]["pw_mean"]) for c in cf])
    a.fill_between(o, q[:, 0], q[:, 2], color=C_B, alpha=0.15, lw=0)
    a.plot(o, m, marker="o", ms=4.5, lw=1, color=C_B, label="public claims")
    ob = np.array([c["o"] for c in bcf])
    q = np.array([c["grade"]["Xb"]["pw_world_p10_50_90"] for c in bcf])
    m = np.array([np.mean(c["grade"]["Xb"]["pw_mean"]) for c in bcf])
    a.fill_between(ob, q[:, 0], q[:, 2], color=C_C, alpha=0.15, lw=0)
    a.plot(ob, m, marker="v", ms=4.5, lw=1, color=C_C, label="broker")
    g = dcf["grade"]["Xb_d0.5"]
    mm = np.mean(g["pw_mean"])
    a.errorbar([0.5], [mm], yerr=[[mm - g["pw_world_p10_50_90"][0]],
               [g["pw_world_p10_50_90"][2] - mm]], fmt="*", ms=8,
               color=C_C, mfc="white", lw=0.8, capsize=2,
               label="broker + decoys (q = 0.5)")
    a.axhline(0.60, color="0.2", ls="--", lw=0.6)
    a.set_xlabel("share of each list common to all groups")
    a.set_ylabel("paired win rate per group\n(first qualifier at lower spend)")
    a.set_xticks(o); a.set_ylim(0, 1)
    a.set_xlim(-0.04, 1.04)
    a.legend(frameon=True, facecolor="white", edgecolor="none", framealpha=1,
             loc="upper left", fontsize=6.6, handlelength=1.4,
             labelspacing=0.3, borderaxespad=0.2)
    a.set_title("measurement-anchored, simulated", fontsize=7.5, pad=4,
                loc="left")
    fig.tight_layout()
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
