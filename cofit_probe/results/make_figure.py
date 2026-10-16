#!/usr/bin/env python3
"""Figure for the cofit probe grading + post-refit comparison No. 2 regrade."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.0))
fig.suptitle("Co-fit gate probe 1940907: prediction falsified, model refit, "
             "comparison No. 2 regraded", fontsize=12)

# A: gate prediction vs measurement
a = ax[0]
a.errorbar([0], [19], yerr=[[3], [4]], fmt="o", capsize=6, color="#888",
           label="registered prediction\n(s prior 0.35–0.50)")
a.errorbar([1], [-0.7], yerr=[[2.3], [2.3]], fmt="o", capsize=6,
           color="#1f77b4", label="post-refit model\n(measured s, c)")
a.axhline(-1.8, color="#d62728", lw=2, label="measured: −1.8%")
a.axhline(0, color="k", lw=0.5)
a.set_xlim(-0.6, 1.6); a.set_xticks([0, 1])
a.set_xticklabels(["registered\n(before probe)", "refit\n(after probe)"])
a.set_ylabel("packing saving vs sequential 32-rank baseline (%)")
a.set_title("A. Gate prediction vs measured")
a.legend(fontsize=7.5, loc="center right")

# B: walls — near-linear intra-node scaling, tiny contention
b = ax[1]
names = ["MoSe2_2H", "WTe2_2H"]
w32 = [3777, 4868]; solo = [6509.8, 8591.2]; co = [6760.9, 8800.2]
x = [0, 1]; wdt = 0.26
b.bar([i - wdt for i in x], w32, wdt, label="32 ranks (probe 1928420)",
      color="#888")
b.bar(x, solo, wdt, label="16 ranks solo", color="#1f77b4")
b.bar([i + wdt for i in x], co, wdt, label="16 ranks concurrent",
      color="#ff7f0e")
for i in x:
    b.text(i, solo[i] + 150, f"×{solo[i]/w32[i]:.2f}", ha="center",
           fontsize=8)
    b.text(i + wdt, co[i] + 150, f"+{100*(co[i]/solo[i]-1):.1f}%",
           ha="center", fontsize=8)
b.set_xticks(x); b.set_xticklabels(names)
b.set_ylabel("wall time (s)")
b.set_title("B. Near-linear rank scaling; contention 2–4%")
b.legend(fontsize=7.5)

# C: post-refit design sweep (400 worlds)
c = ax[2]
designs = [("7×7 12c×20p", 356, (322, 401), 0.30, 0.53),
           ("8×8 8c×15p", 432, (376, 512), 0.68, 1.00),
           ("8×8 8c×20p", 577, (508, 684), 0.69, 1.00),
           ("8×8 12c×15p", 652, (576, 774), 0.67, 1.00),
           ("8×8 12c×20p", 870, (767, 1022), 0.69, 1.00)]
for name, bud, ci, pj, ph in designs:
    col = "#2ca02c" if name == "8×8 8c×15p" else "#1f77b4"
    c.errorbar([bud], [pj], xerr=[[bud - ci[0]], [ci[1] - bud]], fmt="o",
               capsize=4, color=col)
    c.annotate(f"{name}\nP(H)={ph:.2f}", (bud, pj), textcoords="offset points",
               xytext=(4, -18 if "7×7" not in name else 8), fontsize=7)
c.axvline(520, color="#2ca02c", ls="--", lw=1,
          label="cap 520 pc-nh (frozen)")
c.set_xlabel("total budget, per-core node-hours (median, 80% CI)")
c.set_ylabel("P(joint win-win: PW60 ∧ H≥1.05×)")
c.set_ylim(0, 1); c.set_title("C. Regraded designs (measured s, c)")
c.legend(fontsize=8, loc="lower right")

fig.tight_layout()
fig.savefig("fig_cofit.png", dpi=130)
print("wrote fig_cofit.png")
