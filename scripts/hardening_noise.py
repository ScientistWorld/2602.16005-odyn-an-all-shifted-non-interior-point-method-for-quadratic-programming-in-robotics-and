#!/usr/bin/env python3
"""Noise estimates for the hidden test (hardening audit).

1. Run-to-run noise: compares the reference's hidden-test outcomes with an
   uncached rerun of the same solver on the same instances (CPU-budget timing,
   BLAS, scheduling).
2. Test-sampling noise: splits the hidden test into two halves (perturbation
   draw 0 vs 1 for Maros-Meszaros instances, even vs odd index for the
   degenerate family) and ranks one half against the other.

Usage: python3 scripts/hardening_noise.py REF_OUTCOMES RERUN_OUTCOMES OUT_JSON
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
FAMILY = {"maros_meszaros": ("failure_rate_comparison", "failure_rate_{}"),
          "degenerate": ("degenerate_problems", "degenerate_failure_rate_{}")}


def load(path: Path, solver: str) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec["solver"] == solver:
            out[(rec["instance"], rec["tolerance"])] = rec
    return out


def metrics(recs: list[dict]) -> dict:
    out: dict = {}
    for family, (exp, tmpl) in FAMILY.items():
        for tol in ("medium", "high"):
            sel = [r for r in recs if r["family"] == family and r["tolerance"] == tol]
            if sel:
                out.setdefault(exp, {})[tmpl.format(tol)] = 100.0 * sum(not r["solved"] for r in sel) / len(sel)
    return out


def rank(a: dict, b: dict) -> float:
    ref = json.loads((WS / "scoring" / "reference.json").read_text())
    total = 0.0
    for exp, spec in ref["experiments"].items():
        for metric, mdef in spec["metrics"].items():
            va, vb = a.get(exp, {}).get(metric), b.get(exp, {}).get(metric)
            if va is None or vb is None:
                continue
            diff = (va - vb) if mdef["higher_is_better"] else (vb - va)
            total += float(spec["weight"]) * abs(float(mdef["coefficient"])) * diff
    return total


def half(rec: dict) -> int:
    if rec["family"] == "maros_meszaros":
        return int(rec["draw"])
    return int(rec["draw"]) % 2


def main() -> None:
    ref_path, rerun_path, out_path = (Path(p) for p in sys.argv[1:4])
    ref = load(ref_path, "odyn")
    result: dict = {}
    if rerun_path.is_file():
        rerun = load(rerun_path, "odyn")
        shared = sorted(set(ref) & set(rerun))
        flips = [{"instance": k[0], "tolerance": k[1], "reference": ref[k]["solved"], "rerun": rerun[k]["solved"],
                  "reference_cpu_s": ref[k].get("cpu_s"), "rerun_cpu_s": rerun[k].get("cpu_s")}
                 for k in shared if ref[k]["solved"] != rerun[k]["solved"]]
        result["run_to_run"] = {
            "instances_compared": len(shared),
            "outcome_flips": len(flips),
            "flips": flips,
            "rerun_metrics": metrics([rerun[k] for k in shared]),
            "reference_metrics": metrics([ref[k] for k in shared]),
            "rank_rerun_vs_reference": rank(metrics([rerun[k] for k in shared]), metrics([ref[k] for k in shared])),
        }
    halves = {0: [], 1: []}
    for rec in ref.values():
        halves[half(rec)].append(rec)
    m0, m1 = metrics(halves[0]), metrics(halves[1])
    result["split_half"] = {"half0_metrics": m0, "half1_metrics": m1, "rank_half1_vs_half0": rank(m1, m0),
                            "note": "each half holds half the hidden test; the sampling noise (standard deviation) "
                                    "of the full test's rank is about half of the half-vs-half rank difference"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "flips"} for k, v in result.items()}, indent=1))


if __name__ == "__main__":
    main()
