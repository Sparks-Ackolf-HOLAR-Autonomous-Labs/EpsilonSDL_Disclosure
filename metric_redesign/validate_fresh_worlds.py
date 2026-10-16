#!/usr/bin/env python3
"""Fresh-world validation of the redesigned metrics (2026-09-09: the
frozen metrics had a noise-to-signal problem, so the metric is fixed
rather than frozen).

The fix is PW60 (paired-seed win-rate on nh-to-first-qualifier) + the
package H margins (labels/nh >= 1.05x, failure <= +0.04, memory-p95 no
worse). PW60 was *selected* from a 7-metric battery graded on worlds
0..299, so its 0.92 carried selection optimism. This script grades the
pre-chosen PW60+package design — no battery, no selection — on FRESH
worlds (ids 500000+) never used in the selection, for both settings.
If the fresh-world number holds near 0.92, the redesign is a fix, not
an overfit; the validated pair can then be adopted as the preregistered
metric set.

All node-hours are simulated units.
"""
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "prior_predictive"))
sys.path.insert(0, str(HERE.parent / "ceiling_diagnosis"))
os.environ.setdefault("MPT_HARD_CAP", "1")
import metric_study as ms  # noqa: E402
import simulator as sim  # noqa: E402

OFFSET = 500000


def main():
    worlds = int(os.environ.get("MRS_WORLDS", "300"))
    procs = int(os.environ.get("MRS_PROCS", os.cpu_count()))
    out = {"worlds": worlds, "offset": OFFSET,
           "metric": "PW60 + package H margins (pre-chosen)"}

    with Pool(procs) as p:
        rows = p.map(ms.run_one,
                     [("base", OFFSET + i) for i in range(worlds)],
                     chunksize=4)
    out["wide_prior_x1"] = ms.grade(rows)

    ms.SCALE = 100.0
    sim.sample_world = ms.sample_world_post
    sim.mem_per_node = ms.mem_per_node_post
    sim.OVERHEAD_NH = 0.02
    with Pool(procs) as p:
        rows = p.map(ms.run_one,
                     [("posterior", OFFSET + i) for i in range(worlds)],
                     chunksize=4)
    out["posterior_x100"] = ms.grade(rows)

    json.dump(out, open(HERE / "fresh_world_validation.json", "w"), indent=1)
    for setting in ("wide_prior_x1", "posterior_x100"):
        g = out[setting]
        v = g["PW60"]
        print(f"{setting}: PW60 P(Rgain)={v['p_r_gain']:.3f} "
              f"ww(package)={v['p_ww_package']:.3f} "
              f"[selection-set numbers were 0.230/0.160 (x1), "
              f"0.947/0.920 (x100)]")


if __name__ == "__main__":
    main()
