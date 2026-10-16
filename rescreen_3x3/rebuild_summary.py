#!/usr/bin/env python3
"""Rebuild the guest-screen summary from the raw QE outputs.

Reads the archived outputs of guest job 2048736 (results/qe_outputs/
guest_2048736_outs.tgz) plus the conjugate-gradient F3 reruns of follow-up
job 2087605 (results/qe_outputs/followup_2087605/<cand>/f3cg.cedt.out),
re-parses them with the fixed CPU-time parser, and writes
results/guest_summary_final.json and results/GUEST_RESULTS.md.
The 1x1 campaign gaps (scalar-relativistic and SOC) are joined for
comparison. The original guest_summary.json is left untouched as the
as-run record.
"""
import io
import json
import tarfile
from pathlib import Path

from guest_screen import qe_cpu_seconds, parse_scf, parse_gap, GAP_LO, GAP_HI

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
OUTS = RES / "qe_outputs"
DFT = HERE.parent / "dft_campaign"


def load_tgz(path):
    files = {}
    with tarfile.open(path) as tf:
        for m in tf.getmembers():
            if m.isfile():
                parts = Path(m.name).parts
                files[(parts[-2], parts[-1])] = tf.extractfile(m).read().decode(
                    "utf-8", "replace")
    return files


def main():
    files = load_tgz(OUTS / "guest_2048736_outs.tgz")
    fup = OUTS / "followup_2087605"
    for p in fup.glob("*/f3cg.cedt.out"):
        files[(p.parent.name, "f3cg.cedt.out")] = p.read_text(errors="replace")
    gap1 = {}
    for line in open(DFT / "results" / "outcomes.jsonl"):
        r = json.loads(line)
        gap1[r["candidate"]] = r.get("gap_ev")
    soc = json.load(open(DFT / "soc" / "results" / "soc_summary.json"))["soc_gaps"]
    manifest = json.load(open(HERE / "inputs" / "manifest.json"))
    rows = []
    for m in manifest:
        c = m["name"]
        f2 = files.get((c, "f2.cedt.out"), "")
        nelec = parse_scf(f2)["nelec"]
        f3 = files.get((c, "f3.cedt.out"), "")
        src = "davidson"
        gap = parse_gap(f3, nelec) if "JOB DONE" in f3 else None
        if gap is None and (c, "f3cg.cedt.out") in files:
            f3 = files[(c, "f3cg.cedt.out")]
            gap = parse_gap(f3, nelec) if "JOB DONE" in f3 else None
            src = "cg_followup"
        cc = qe_cpu_seconds(f2)
        dc = qe_cpu_seconds(files.get((c, "f2.dtde.out"), ""))
        rows.append({
            "candidate": c, "nelec": nelec,
            "gap_ev_3x3": round(gap, 4) if gap is not None else None,
            "gap_source": src if gap is not None else None,
            "gap_ev_1x1": gap1.get(c),
            "soc_gap_ev_1x1": soc.get(c),
            "qualifier": gap is not None and GAP_LO <= gap <= GAP_HI,
            "f2_cedt_cpu_s": cc, "f2_dtde_cpu_s": dc,
            "f2_cost_ratio_cedt_over_dtde": round(cc / dc, 3) if cc and dc else None,
        })
    quals = [r["candidate"] for r in rows if r["qualifier"]]
    ratios = sorted(r["f2_cost_ratio_cedt_over_dtde"] for r in rows
                    if r["f2_cost_ratio_cedt_over_dtde"])
    out = {"jobs": ["2048736", "2087605"], "partition": "granite-guest",
           "candidates": len(rows), "gaps_measured": sum(
               r["gap_ev_3x3"] is not None for r in rows),
           "qualifiers": quals, "cost_ratio_n": len(ratios),
           "cost_ratio_median": ratios[len(ratios) // 2] if ratios else None,
           "cost_ratio_min": ratios[0] if ratios else None,
           "cost_ratio_max": ratios[-1] if ratios else None,
           "rows": rows}
    json.dump(out, open(RES / "guest_summary_final.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    write_md(out)


def fmt(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def write_md(out):
    rows = out["rows"]
    both = [r for r in rows if r["gap_ev_3x3"] is not None
            and r["gap_ev_1x1"] is not None]
    dmax = max(abs(r["gap_ev_3x3"] - r["gap_ev_1x1"]) for r in both)
    q1 = sorted(r["candidate"] for r in rows
                if r["gap_ev_1x1"] is not None
                and GAP_LO <= r["gap_ev_1x1"] <= GAP_HI)
    pend = [r["candidate"] for r in rows if r["gap_ev_3x3"] is None]
    L = ["# Guest-partition screen: results (jobs 2048736 + 2087605)", "",
         "Real Quantum ESPRESSO 7.4 (PBE, GBRV ultrasoft), 29 MX2 candidates "
         "as 3x3 supercells (27 atoms for 1T, 54 for 2H), run on the free "
         "`granite-guest` partition (nodes grn068, then grn021). Generated "
         "by `rebuild_summary.py` from the raw outputs.", "",
         "## Summary", "",
         f"- Gaps measured at 3x3: {out['gaps_measured']} of {out['candidates']}"
         + (f" (still missing: {', '.join(pend)})" if pend else "") + ".",
         f"- Largest difference between the 3x3 gap and the 1x1 campaign gap: "
         f"{dmax:.4f} eV over {len(both)} candidates with both values.",
         f"- Qualifiers (PBE gap 1.0 to 2.0 eV) at 3x3: {len(out['qualifiers'])}: "
         f"{', '.join(out['qualifiers'])}.",
         f"- Qualifiers at 1x1 for the same 29 candidates: {len(q1)}: {', '.join(q1)}.",
         f"- F2 cost ratio, class-matched config (32 ranks, 2 k-point pools) "
         f"over the worst-case config (32 ranks, 1 pool), QE CPU seconds: "
         f"median {out['cost_ratio_median']}, range {out['cost_ratio_min']} to "
         f"{out['cost_ratio_max']} (n = {out['cost_ratio_n']}).", "",
         "The four candidates whose F3 band calculation failed in the Davidson "
         "eigensolver on the first run (TiS2-1T, TiS2-2H, ZrS2-1T, ZrSe2-1T) "
         "were rerun with the conjugate-gradient eigensolver in job 2087605.",
         "", "## Per-candidate table", "",
         "| candidate | electrons | gap 3x3 (eV) | source | gap 1x1 (eV) | SOC gap 1x1 (eV) | qualifier | F2 cost ratio |",
         "| --- | ---: | ---: | --- | ---: | ---: | --- | ---: |"]
    for r in rows:
        L.append(f"| {r['candidate']} | {int(r['nelec']) if r['nelec'] else 'n/a'} | "
                 f"{fmt(r['gap_ev_3x3'])} | {r['gap_source'] or 'pending'} | "
                 f"{fmt(r['gap_ev_1x1'])} | {fmt(r['soc_gap_ev_1x1'])} | "
                 f"{'yes' if r['qualifier'] else 'no'} | "
                 f"{fmt(r['f2_cost_ratio_cedt_over_dtde'])} |")
    L += ["", "1x1 gaps shown as n/a are metallic or were not recorded "
          "(the 1x1 campaign stored no gap for zero-gap cells).", ""]
    open(RES / "GUEST_RESULTS.md", "w").write("\n".join(L))


if __name__ == "__main__":
    main()
