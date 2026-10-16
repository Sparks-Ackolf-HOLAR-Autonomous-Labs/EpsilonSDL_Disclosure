#!/usr/bin/env python3
"""Figure for the metric-redesign study: P(win-win) per candidate R
metric (CEDT-P4 vs DTDE-P4, package H margins), wide prior x1 vs
measurement-informed posterior x100."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).parent
d = json.load(open(HERE / "metric_study.json"))
METRICS = ["T20", "T10", "REG20", "PW60", "EX10", "EX15", "QY05"]
LABELS = ["T20\n(frozen)", "T10", "REG20\n(oracle\nregret)",
          "PW60\n(paired\nwin-rate)", "EX10\n(labels/nh)", "EX15",
          "QY05\n(yield)"]
C1, C2 = "#2a78d6", "#eb6834"  # validated categorical slots 1-2
SURF, INK, MUT = "#fcfcfb", "#222222", "#6b6b6b"

wide = [d["wide_prior_x1"][m]["p_ww_package"] for m in METRICS]
post = [d["posterior_x100"][m]["p_ww_package"] for m in METRICS]

fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=150)
fig.patch.set_facecolor(SURF)
ax.set_facecolor(SURF)
x = np.arange(len(METRICS))
w = 0.38
b1 = ax.bar(x - w / 2 - 0.01, wide, w, color=C1,
            label="wide prior, ×1 task scale")
b2 = ax.bar(x + w / 2 + 0.01, post, w, color=C2,
            label="posterior (Stage-2 + pilot), ×100 scale")
ax.axhline(0.90, color=MUT, lw=1, ls="--", zorder=0)
ax.text(len(METRICS) - 0.45, 0.915, "preregistered 0.90", color=MUT,
        fontsize=8, ha="right")
for bars in (b1, b2):
    for r in bars:
        v = r.get_height()
        ax.text(r.get_x() + r.get_width() / 2, v + 0.015, f"{v:.2f}",
                ha="center", va="bottom", fontsize=7.5, color=INK)
ax.set_xticks(x, LABELS, fontsize=8, color=INK)
ax.set_ylabel("P(win-win)  —  CEDT-P4 vs DTDE-P4,\npackage H margins",
              fontsize=9, color=INK)
ax.set_ylim(0, 1.05)
ax.set_title("Does redesigning the R metric fix the noise-to-signal "
             "problem?", fontsize=11, color=INK, pad=10)
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color(MUT)
ax.tick_params(colors=MUT, labelcolor=INK)
ax.yaxis.grid(True, color="#e6e6e3", lw=0.7, zorder=0)
ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=8.5, loc="upper left")
fig.tight_layout()
fig.savefig(HERE / "fig_metric_redesign.png")
print("wrote fig_metric_redesign.png")
