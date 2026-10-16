#!/usr/bin/env python3
"""kMC rung: value and leakage of barrier disclosure at graded resolution.

Uses the 60 measured kMC runs (30 compounds x 2 lattice sizes, MACE barriers) in
results/kmc_runs.jsonl. Two questions per disclosure level:

  Value. How well can a party predict the kMC cost of a compound it has NOT run yet?
    Leave-one-compound-out R^2 of log10(cost to the 1 s anneal) from
      own        : public size only (lattice edge L, phase)          -> what R has in DTDE
      bin01      : size + hop barrier rounded to 0.1 eV               -> logbook, fine
      rank3      : size + barrier tercile (rank only, 3 bins)         -> logbook, coarse
      rank2      : size + one bit, barrier above or below the median  -> logbook, one bit
      exact      : size + exact barrier and divacancy binding         -> full disclosure
    The gap (logbook R^2 - own R^2) is the slope the training axis can gain.

  Leakage. Exact-compound identification accuracy by an attacker who holds the public
    table of disclosed values (worst case), compared with the study limit
    prior + 0.05 = 1/30 + 0.05 = 0.083. Also the kMC wall-time channel: a compound's job
    duration (run-to-run noise 0.05 decades, the measured GPU/CPU scatter scale) seen
    raw, rounded up to 600 s, or rounded to whole decades.

Barriers here are MACE-MP-0 values; the DFT check (dft_neb/) decides whether the spread
holds. All costs are measured kMC CPU seconds projected to 1 s of simulated time.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RES = HERE / "results"
runs = [json.loads(l) for l in (RES / "kmc_runs.jsonl").read_text().splitlines() if l.strip()]
names = sorted({r["candidate"] for r in runs})
LIMIT_ID = 1 / len(names) + 0.05
UNSTABLE = {"MoS2_1T", "MoSe2_1T", "MoTe2_1T", "WS2_1T", "WSe2_1T", "WTe2_1T"}

y = np.log10([r["cost_to_t_end_s"] for r in runs])
L = np.array([r["L"] for r in runs], float)
ph = np.array([r["candidate"].endswith("_2H") for r in runs], float)
eb = np.array([r["E_hop_eV"] for r in runs])
ebind = np.array([r["E_bind_eV"] for r in runs])
comp = np.array([r["candidate"] for r in runs])
cb = {c: eb[comp == c][0] for c in names}
terc = np.quantile(list(cb.values()), [1 / 3, 2 / 3])
rank3 = np.digitize(eb, terc).astype(float)
med = np.median(list(cb.values()))
rank2 = (eb > med).astype(float)
bin01 = np.round(eb, 1)

FEATS = {
    "own": [np.log10(L), ph],
    "bin01": [np.log10(L), ph, bin01],
    "rank3": [np.log10(L), ph, rank3],
    "rank2": [np.log10(L), ph, rank2],
    "exact": [np.log10(L), ph, eb, ebind],
}


def loco_r2(X, mask):
    """Leave-one-compound-out R^2 on the rows in mask."""
    Xm = np.column_stack([np.ones(mask.sum())] + [x[mask] for x in X])
    ym, cm = y[mask], comp[mask]
    pred = np.empty_like(ym)
    for c in np.unique(cm):
        tr = cm != c
        beta, *_ = np.linalg.lstsq(Xm[tr], ym[tr], rcond=None)
        pred[~tr] = Xm[~tr] @ beta
    return float(1 - np.mean((ym - pred) ** 2) / ym.var())


def ident_acc(values):
    """Attacker with the public table guesses uniformly among compounds sharing the
    disclosed value; expected exact-identity accuracy."""
    v = np.array([values[c] for c in names])
    return float(np.mean([1 / np.sum(v == x) for x in v]))


def timing_acc(mask_fn, sd=0.05, trials=400, seed=3):
    """Nearest-neighbour attack on observed job duration (one L=48 job per compound)."""
    rng = np.random.default_rng(seed)
    ref = {c: float(np.log10([r["cost_to_t_end_s"] for r in runs
                              if r["candidate"] == c and r["L"] == 48][0])) for c in names}
    keys = np.array(names)
    refm = np.array([mask_fn(ref[c]) for c in names])
    hit = 0.0
    for _ in range(trials):
        for c in names:
            obs = mask_fn(ref[c] + rng.normal(0, sd))
            d = np.abs(refm - obs)
            cands = keys[d == d.min()]
            hit += (c in cands) / len(cands)
    return hit / (trials * len(names))


def main():
    allm = np.ones(len(y), bool)
    stab = ~np.isin(comp, list(UNSTABLE))
    out = {"n_runs": int(len(y)), "n_compounds": len(names), "identity_limit": LIMIT_ID,
           "value_loco_R2": {}, "value_loco_R2_stable": {}, "identity_accuracy": {}}
    for k, X in FEATS.items():
        out["value_loco_R2"][k] = loco_r2(X, allm)
        out["value_loco_R2_stable"][k] = loco_r2(X, stab)
    out["identity_accuracy"]["exact"] = ident_acc({c: round(cb[c], 6) for c in names})
    out["identity_accuracy"]["bin01"] = ident_acc({c: round(cb[c], 1) for c in names})
    out["identity_accuracy"]["rank3"] = ident_acc(
        {c: int(np.digitize(cb[c], terc)) for c in names})
    out["identity_accuracy"]["rank2"] = ident_acc({c: int(cb[c] > med) for c in names})
    q600 = lambda lg: np.log10(np.ceil(10 ** lg / 600.0) * 600.0)
    out["identity_accuracy"]["timing_raw"] = timing_acc(lambda lg: lg)
    out["identity_accuracy"]["timing_600s"] = timing_acc(q600)
    out["identity_accuracy"]["timing_decade"] = timing_acc(lambda lg: np.round(lg))
    out["bin01_bin_sizes"] = sorted(
        {b: int(sum(round(cb[c], 1) == b for c in names)) for c in names
         for b in [round(cb[c], 1)]}.items())
    (RES / "disclosure_probe.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
