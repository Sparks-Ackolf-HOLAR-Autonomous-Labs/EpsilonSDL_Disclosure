#!/usr/bin/env python3
"""Grade the registered predictions (PREDICTION.md) and draw the summary figure.

For each method, ordinary least squares of log10(job cost) on public size descriptors.
Reported: R^2 and the residual spread after size (std in decades, and the max/min cost
ratio left unexplained), because R^2 alone is misleading when the total spread is small.
"""
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RES = HERE / "results"
jl = lambda p: [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    r2 = 1 - res.var() / y.var()
    return {"R2": float(r2), "resid_std_dec": float(res.std()),
            "unexplained_ratio": float(10 ** (res.max() - res.min())),
            "total_ratio": float(10 ** (y.max() - y.min())), "n": int(len(y))}, res


dft = {}
for d in jl(HERE.parent / "dft_campaign" / "results" / "outcomes.jsonl"):
    if d["candidate"] in dft:
        continue
    dft[d["candidate"]] = d
ff = {r["candidate"]: r for r in jl(RES / "ff_rung.jsonl")}
neb = {r["candidate"]: r for r in jl(RES / "vacancy_neb.jsonl")}
kmc = jl(RES / "kmc_runs.jsonl")
nfu = lambda c: 1 if c.endswith("_1T") else 2
nel_fu = {c: d["stages"]["F1"]["nelec"] / nfu(c) for c, d in dft.items()}
out = {}

# Reference: measured QE F2 wall time on 1x1 cells (29 compounds with relaxed F2)
c_dft = [c for c, d in dft.items() if d.get("a_relaxed_angstrom")]
y = np.log10([dft[c]["stages"]["F2"]["wall_s"] for c in c_dft])
x = np.log10([dft[c]["stages"]["F1"]["nelec"] for c in c_dft])
out["dft_F2"], _ = ols(y, [x])

# Test A1: MACE MD (90 jobs) and MACE relaxation (30 jobs)
md = [(c, m["atoms"], m["wall_s"]) for c, r in ff.items() for m in r["md"]]
out["ff_md"], _ = ols(np.log10([m[2] for m in md]), [np.log10([m[1] for m in md])])
# is the size-residual of MD cost compound information or machine noise? fraction of
# residual variance explained by compound identity (one-way ANOVA)
_, res_md = ols(np.log10([m[2] for m in md]), [np.log10([m[1] for m in md])])
_c = np.array([m[0] for m in md])
_between = sum((_c == c).sum() * res_md[_c == c].mean() ** 2 for c in set(_c))
out["ff_md_resid_frac_by_compound"] = float(_between / (res_md ** 2).sum())
out["ff_md_per_step_ms_range"] = [1e3 * min(m[2] for m in md) / 200, 1e3 * max(m[2] for m in md) / 200]
rel = list(ff.values())
out["ff_relax"], _ = ols(np.log10([r["relax_wall_s"] for r in rel]),
                         [np.log10([r["n_atoms_1x1"] for r in rel])])
out["ff_relax_steps_range"] = [min(r["relax_steps"] for r in rel), max(r["relax_steps"] for r in rel)]

# Test A2: lattice constants against PBE
errs = {c: 100 * (ff[c]["a_ff"] - dft[c]["a_relaxed_angstrom"]) / dft[c]["a_relaxed_angstrom"]
        for c in c_dft}
out["A2"] = {"within_3pct": sum(abs(e) <= 3 for e in errs.values()), "n": len(errs),
             "mean_abs_pct": float(np.mean(np.abs(list(errs.values())))),
             "max_abs_pct": float(max(abs(e) for e in errs.values())), "per_compound_pct": errs}
# Test A3: 1T - 2H sign per composition
RY = 13.605693
agree, rows = 0, {}
comps = sorted({c.split("_")[0] for c in ff})
for comp in comps:
    a, b = f"{comp}_1T", f"{comp}_2H"
    dff = ff[a]["e_per_fu_ev"] - ff[b]["e_per_fu_ev"]
    if b in dft and dft[b]["stages"]["F2"].get("etot_ry") and dft[b].get("a_relaxed_angstrom"):
        ddf = RY * (dft[a]["stages"]["F2"]["etot_ry"] - dft[b]["stages"]["F2"]["etot_ry"] / 2)
    else:
        ddf = None
    rows[comp] = {"ff_eV_fu": dff, "pbe_eV_fu": ddf}
    if ddf is not None:
        agree += int(np.sign(dff) == np.sign(ddf))
out["A3"] = {"agree": agree, "n": sum(r["pbe_eV_fu"] is not None for r in rows.values()), "rows": rows}

# Test B
eh = np.array([r["E_hop_eV"] for r in neb.values()])
out["B1"] = {"E_hop_min": float(eh.min()), "E_hop_max": float(eh.max()),
             "span_eV": float(eh.max() - eh.min()),
             "E_bind_range": [float(min(r["E_bind_divac_eV"] for r in neb.values())),
                              float(max(r["E_bind_divac_eV"] for r in neb.values()))],
             "neb_converged": sum(r["neb_converged"] for r in neb.values()), "n": len(neb)}
k = [r for r in kmc if np.isfinite(r["cost_to_t_end_s"]) and r["cost_to_t_end_s"] > 0]
yk = np.log10([r["cost_to_t_end_s"] for r in k])
size = [np.log10([r["sites"] for r in k]), np.log10([nel_fu[r["candidate"]] for r in k])]
out["B2_size_only"], _ = ols(yk, size)
out["B3_size_plus_barrier"], _ = ols(yk, size + [np.array([r["E_hop_eV"] for r in k]),
                                                  np.array([r["E_bind_eV"] for r in k])])
# robustness: drop 1T Mo/W (dynamically unstable phases that distort to 1T')
ks = [r for r in k if not (r["candidate"].endswith("_1T") and r["candidate"].startswith(("Mo", "W")))]
ys = np.log10([r["cost_to_t_end_s"] for r in ks])
szs = [np.log10([r["sites"] for r in ks]), np.log10([nel_fu[r["candidate"]] for r in ks])]
out["B2_stable_subset"], _ = ols(ys, szs)
out["B3_stable_subset"], _ = ols(ys, szs + [np.array([r["E_hop_eV"] for r in ks]),
                                             np.array([r["E_bind_eV"] for r in ks])])
out["kmc_runs_used"] = len(k)
out["kmc_runs_total"] = len(kmc)
out["kmc_cost_decades"] = float(yk.max() - yk.min())

verdict = {
    "A1": out["ff_md"]["R2"] >= 0.95,
    "A2": out["A2"]["within_3pct"] >= 25,
    "A3": out["A3"]["agree"] >= 12,
    "B1": out["B1"]["span_eV"] >= 0.3,
    "B2": out["B2_size_only"]["R2"] < 0.90,
    "B3": out["B3_size_plus_barrier"]["R2"] > 0.90,
}
out["verdict"] = verdict
(RES / "analysis.json").write_text(json.dumps(out, indent=2))

# Figure: cost against size for the three methods, one panel each (print size)
fig, ax = plt.subplots(1, 3, figsize=(7.0, 2.4), constrained_layout=True)
ax[0].scatter([dft[c]["stages"]["F1"]["nelec"] for c in c_dft],
              [dft[c]["stages"]["F2"]["wall_s"] for c in c_dft], s=10, c="#3366aa")
ax[0].set(xscale="log", yscale="log", xlabel="electrons per cell", ylabel="job cost (s)",
          title=f"DFT F2 (QE), $R^2$={out['dft_F2']['R2']:.2f}")
ax[1].scatter([m[1] for m in md], [m[2] for m in md], s=10, c="#3366aa")
ax[1].set(xscale="log", yscale="log", xlabel="atoms", title=f"Force field MD, $R^2$={out['ff_md']['R2']:.2f}")
sc = ax[2].scatter([r["sites"] for r in k], [r["cost_to_t_end_s"] for r in k], s=10,
                   c=[r["E_hop_eV"] for r in k], cmap="viridis")
ax[2].set(xscale="log", yscale="log", xlabel="lattice sites",
          title=f"Vacancy kMC, $R^2_{{size}}$={out['B2_size_only']['R2']:.2f}")
fig.colorbar(sc, ax=ax[2], label="hop barrier (eV)")
from matplotlib.ticker import NullFormatter, FixedLocator, FixedFormatter
for a, xt, yt in ((ax[0], [24, 36, 52], [50, 100, 200, 400]),
                  (ax[1], [12, 27, 48, 96], [2, 3, 4, 6]),
                  (ax[2], [576, 2304], None)):
    a.xaxis.set_major_locator(FixedLocator(xt)); a.xaxis.set_major_formatter(FixedFormatter([str(v) for v in xt]))
    a.xaxis.set_minor_formatter(NullFormatter())
    if yt:
        a.yaxis.set_major_locator(FixedLocator(yt)); a.yaxis.set_major_formatter(FixedFormatter([str(v) for v in yt]))
        a.yaxis.set_minor_formatter(NullFormatter())
for a in ax:
    a.title.set_fontsize(8); a.tick_params(labelsize=7)
    a.xaxis.label.set_fontsize(8); a.yaxis.label.set_fontsize(8)
fig.savefig(RES / "fig_cost_vs_size.png", dpi=200)
print(json.dumps({kk: v for kk, v in out.items() if kk not in ("A2", "A3")}, indent=1))
print("A2", out["A2"]["within_3pct"], out["A2"]["n"], out["A2"]["mean_abs_pct"], out["A2"]["max_abs_pct"])
print("A3", out["A3"]["agree"], out["A3"]["n"], out["A3"]["rows"])
