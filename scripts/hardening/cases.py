#!/usr/bin/env python3
"""Hardening audit driver: run variants and shortcuts through the hidden test.

Sub-commands (run from the workspace root, inside the job container):

  smoke    tiny end-to-end check of instance writing, solver calls, verification
  export   build the reference memo (from the hidden-test run) and the public
           solution bank (from the paper-level run on unperturbed problems)
  run      run every case in an isolated workspace copy via the unmodified
           ``bash scripts/evaluate_test.sh`` (no arguments)
  analyze  ranks, paired bootstrap, and draw-to-draw noise -> notes/hardening/

Case workspaces live in tmp/hardening/<case>/ws. They contain copies of the
code directories and a symlink to the (hash-checked) problem files; only the
case's own solver script is added. The optional evaluator cache
(QP_GYM_EVAL_CACHE) lets the unchanged reference and baseline runs be reused,
while every score is still recomputed from raw outputs.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[2]
HARD = WS / "tmp" / "hardening"
MEMO = HARD / "memo"
BANK = HARD / "public_bank"
NOTES = WS / "notes" / "hardening"
REFERENCE = "odyn"
BASELINE = "osqp"

CASES: dict[str, dict] = {
    # better / weaker honest variants
    "odyn_more_iter": {"kind": "variant", "cmd": "wrap --mode more_iter",
                       "what": "better variant: the reference with twice the iteration cap (6000/10000)"},
    "odyn_low_budget": {"kind": "variant", "cmd": "odyn --max-iter 30",
                        "what": "weaker variant: the reference capped at 30 iterations"},
    "odyn_one_iter": {"kind": "shortcut", "cmd": "odyn --max-iter 1",
                      "what": "red-team one-iteration run (failed everything, previously +271.9)"},
    # shortcut probes
    "shortcut_claim_success": {"kind": "shortcut", "cmd": "wrap --mode claim_success",
                               "what": "claims success with zero vectors and 0 iterations, solves nothing"},
    "shortcut_no_output": {"kind": "shortcut", "cmd": "wrap --mode no_output",
                           "what": "solves nothing and writes nothing (old zero/negative cap shortcuts)"},
    "shortcut_hide_failures": {"kind": "shortcut", "cmd": "wrap --mode hide_failures",
                               "what": "reference outputs only where the reference reported success"},
    "shortcut_fake_iterations": {"kind": "shortcut", "cmd": "wrap --mode fake_iterations",
                                 "what": "reference outputs relabelled as 1 iteration / optimal"},
    "shortcut_ignore_degenerate": {"kind": "shortcut", "cmd": "wrap --mode ignore_degenerate",
                                   "what": "refuses structurally degenerate instances, reference otherwise"},
    "shortcut_replay_public": {"kind": "shortcut", "cmd": "wrap --mode replay_public",
                               "what": "replays reference solutions of the public unperturbed problems"},
    # tampering probes (no extra solver)
    "shortcut_write_scores_only": {"kind": "tamper", "cmd": None,
                                   "what": "pre-writes a perfect scoring/scores_test.json"},
    "shortcut_tamper_data": {"kind": "tamper", "cmd": None,
                             "what": "alters one benchmark MAT file (old loader/problem replacement)"},
}

SOLVER_TEMPLATE = """#!/bin/bash
set -euo pipefail
WS="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
cd "$WS"
{body}
"""


def sh(cmd: list[str], cwd: Path, log: Path, env: dict | None = None) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as handle:
        handle.write(f"\n$ {' '.join(cmd)}\n")
        handle.flush()
        return subprocess.call(cmd, cwd=str(cwd), stdout=handle, stderr=subprocess.STDOUT, env=env)


# --------------------------------------------------------------------------- #


def cmd_smoke(_: argparse.Namespace) -> None:
    sys.path.insert(0, str(WS))
    import eval.train.evaluate as E  # noqa: PLC0415

    manifest = json.loads(E.MANIFEST_PATH.read_text())
    manifest["maros_meszaros"]["problems"] = {k: v for k, v in manifest["maros_meszaros"]["problems"].items()
                                              if k in ("HS21", "QPCBLEND")}
    manifest["degenerate"]["count_per_kind"] = 2
    instances = E.build_instances(manifest)
    out = HARD / "smoke_scores.json"
    scores = E.evaluate(instances, out, slice_name="smoke", only=None, workers=None, keep_workdir=False,
                        provenance_extra={})
    res = scores["experiments"]
    ok = True
    for solver in (REFERENCE, BASELINE):
        fr = res["degenerate_problems"]["results"][solver]["degenerate_failure_rate_medium"]
        print(f"smoke: {solver} degenerate medium failure rate {fr:.1f}%")
        ok &= fr < 100.0
    fr = res["failure_rate_comparison"]["results"][REFERENCE]["failure_rate_medium"]
    print(f"smoke: {REFERENCE} Maros-Meszaros medium failure rate {fr:.1f}%")
    ok &= fr < 100.0
    for line in (WS / "tmp" / "eval_runs" / "smoke" / "outcomes.jsonl").read_text().splitlines():
        rec = json.loads(line)
        print("smoke:", rec["solver"], rec["instance"], rec["tolerance"], rec["solved"], rec["reason"],
              {k: f"{v:.1e}" for k, v in (rec.get("ratios") or {}).items()}, rec.get("reported"))
    shown = 0
    for line in (WS / "tmp" / "eval_runs" / "smoke" / "outcomes.jsonl").read_text().splitlines():
        rec = json.loads(line)
        if rec.get("log_tail") and shown < 4:
            shown += 1
            print(f"smoke: log tail for {rec['solver']} {rec['instance']} {rec['tolerance']}:\n{rec['log_tail']}")
    if not ok:
        raise SystemExit("smoke test failed")


def cmd_export(_: argparse.Namespace) -> None:
    import numpy as np  # noqa: PLC0415

    shutil.rmtree(MEMO, ignore_errors=True)
    MEMO.mkdir(parents=True)
    count = 0
    for line in (WS / "tmp" / "eval_runs" / "test" / "outcomes.jsonl").read_text().splitlines():
        rec = json.loads(line)
        if rec["solver"] != REFERENCE:
            continue
        stem = f"{rec['instance_hash']}_{rec['tolerance']}"
        if rec.get("raw_output") and Path(rec["raw_output"]).is_file():
            shutil.copyfile(rec["raw_output"], MEMO / f"{stem}.npz")
        else:
            (MEMO / f"{stem}.none").write_text("")
        count += 1
    print(f"export: {count} reference test outputs in memo")
    shutil.rmtree(BANK, ignore_errors=True)
    BANK.mkdir(parents=True)
    index: dict[str, dict] = {}
    paper = WS / "tmp" / "eval_runs" / "paper" / "outcomes.jsonl"
    if paper.is_file():
        for line in paper.read_text().splitlines():
            rec = json.loads(line)
            if rec["solver"] != REFERENCE or rec["family"] != "maros_meszaros" or not rec.get("raw_output"):
                continue
            src = Path(rec["raw_output"])
            if not src.is_file():
                continue
            with np.load(src, allow_pickle=False) as data:
                dims = [int(data["x"].shape[0]), int(data["y"].shape[0]), int(data["z"].shape[0])]
            name = rec["base"]
            dst = f"{name}_{rec['tolerance']}.npz"
            shutil.copyfile(src, BANK / dst)
            index.setdefault(name, {"dims": dims, "files": {}})["files"][rec["tolerance"]] = dst
    (BANK / "index.json").write_text(json.dumps(index, indent=1))
    print(f"export: {len(index)} public problems in the solution bank")


def make_case_workspace(case: str, copy_data: bool = False) -> Path:
    root = HARD / case / "ws"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for sub in ("eval", "method", "baseline", "scripts"):
        if (WS / sub).exists():
            shutil.copytree(WS / sub, root / sub, ignore=ignore)
    (root / "data").mkdir()
    for path in (WS / "data").glob("*.py"):
        shutil.copy2(path, root / "data" / path.name)
    dataset = WS / "data" / "maros_meszaros_qpbenchmark"
    if copy_data:
        shutil.copytree(dataset, root / "data" / "maros_meszaros_qpbenchmark")
    else:
        (root / "data" / "maros_meszaros_qpbenchmark").symlink_to(dataset, target_is_directory=True)
    (root / "scoring").mkdir()
    return root


def register(root: Path, case: str, spec: str) -> None:
    kind, *rest = spec.split()
    if kind == "wrap":
        body = (f'exec python3 scripts/hardening/wrap_solver.py {" ".join(rest)} '
                f'--memo "{MEMO}" --bank "{BANK}" "$@"')
    elif kind == "odyn":
        body = f'exec python3 -m method.solve_cli {" ".join(rest)} "$@"'
    else:
        raise ValueError(spec)
    script = root / "scripts" / "solvers" / f"{case}.sh"
    script.write_text(SOLVER_TEMPLATE.format(body=body))
    script.chmod(0o755)


def cmd_run(args: argparse.Namespace) -> None:
    cases = args.cases or list(CASES)
    for case in cases:
        spec = CASES[case]
        done = HARD / case / "complete.json"
        if done.is_file() and not args.force:
            print(f"run: {case} already complete")
            continue
        log = HARD / case / "run.log"
        root = make_case_workspace(case, copy_data=(case == "shortcut_tamper_data"))
        if spec["cmd"]:
            register(root, case, spec["cmd"])
        if case == "shortcut_write_scores_only":
            fake = {"experiments": {
                "failure_rate_comparison": {"results": {REFERENCE: {"failure_rate_medium": 0.0, "failure_rate_high": 0.0}}},
                "degenerate_problems": {"results": {REFERENCE: {"degenerate_failure_rate_medium": 0.0,
                                                                "degenerate_failure_rate_high": 0.0}}}}}
            (root / "scoring" / "scores_test.json").write_text(json.dumps(fake))
        if case == "shortcut_tamper_data":
            target = root / "data" / "maros_meszaros_qpbenchmark" / "data" / "QAFIRO.mat"
            target.write_bytes(target.read_bytes() + b"\0")
        print(f"run: {case} ...", flush=True)
        rc = sh(["bash", "scripts/evaluate_test.sh"], root, log)
        scores_path = root / "scoring" / "scores_test.json"
        result = {"case": case, "returncode": rc, "scores_written": scores_path.is_file(), **spec}
        if scores_path.is_file():
            result["scores"] = json.loads(scores_path.read_text())
        outcomes = root / "tmp" / "eval_runs" / "test" / "outcomes.jsonl"
        if outcomes.is_file():
            shutil.copyfile(outcomes, HARD / case / "outcomes.jsonl")
        done.write_text(json.dumps(result, indent=1))
        print(f"run: {case} rc={rc} scores_written={result['scores_written']}", flush=True)
        link = root / "data" / "maros_meszaros_qpbenchmark"
        if link.is_symlink():
            link.unlink()


# --------------------------------------------------------------------------- #


def load_reference() -> dict:
    return json.loads((WS / "scoring" / "reference.json").read_text())


def metric_table(ref: dict) -> list[tuple[str, str, float, float, bool]]:
    rows = []
    for exp, spec in ref["experiments"].items():
        for metric, mdef in spec["metrics"].items():
            rows.append((exp, metric, float(spec["weight"]), abs(float(mdef["coefficient"])), bool(mdef["higher_is_better"])))
    return rows


def rank(metrics: dict, base: dict, table) -> tuple[float, dict]:
    total = 0.0
    parts = {}
    for exp, metric, weight, coef, hib in table:
        a = metrics.get(exp, {}).get(metric)
        b = base.get(exp, {}).get(metric)
        if a is None or b is None:
            continue
        diff = (a - b) if hib else (b - a)
        parts[f"{exp}/{metric}"] = weight * coef * diff
        total += weight * coef * diff
    return total, parts


def solver_metrics(scores: dict, solver: str) -> dict:
    return {exp: data["results"].get(solver, {}) for exp, data in scores.get("experiments", {}).items()}


FAMILY = {"maros_meszaros": ("failure_rate_comparison", "failure_rate_{}"),
          "degenerate": ("degenerate_problems", "degenerate_failure_rate_{}")}


def metrics_from_records(recs: list[dict], units: list[tuple]) -> dict:
    """Recompute failure-rate metrics from per-instance outcomes for a list of units."""
    out: dict = {}
    for family, (exp, tmpl) in FAMILY.items():
        for tol in ("medium", "high"):
            sel = [r for u in units if u[0] == family for r in recs.get((u, tol), [])]
            if not sel:
                continue
            out.setdefault(exp, {})[tmpl.format(tol)] = 100.0 * sum(not r for r in sel) / len(sel)
    return out


def outcome_index(path: Path, solver: str) -> dict:
    idx: dict = {}
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec["solver"] != solver:
            continue
        unit = (rec["family"], rec["base"]) if rec["family"] == "maros_meszaros" else (rec["family"], rec["instance"])
        idx.setdefault((unit, rec["tolerance"]), []).append(bool(rec["solved"]))
    return idx


def paired_bootstrap(a: dict, b: dict, table, n_boot: int = 4000, seed: int = 0) -> dict:
    units = sorted({u for (u, _) in a} | {u for (u, _) in b})
    rng = random.Random(seed)
    full = rank(metrics_from_records(a, units), metrics_from_records(b, units), table)[0]
    draws = []
    for _ in range(n_boot):
        pick = [units[rng.randrange(len(units))] for _ in units]
        # duplicate units are kept as repeated entries
        ma = metrics_from_records_multi(a, pick)
        mb = metrics_from_records_multi(b, pick)
        draws.append(rank(ma, mb, table)[0])
    draws.sort()
    lo, hi = draws[int(0.025 * (n_boot - 1))], draws[int(0.975 * (n_boot - 1))]
    return {"rank_difference": full, "ci95": [lo, hi],
            "p_le_zero": sum(d <= 0.0 for d in draws) / n_boot, "units": len(units)}


def metrics_from_records_multi(recs: dict, picks: list[tuple]) -> dict:
    out: dict = {}
    for family, (exp, tmpl) in FAMILY.items():
        for tol in ("medium", "high"):
            sel = []
            for u in picks:
                if u[0] == family:
                    sel.extend(recs.get((u, tol), []))
            if sel:
                out.setdefault(exp, {})[tmpl.format(tol)] = 100.0 * sum(not r for r in sel) / len(sel)
    return out


def cmd_analyze(_: argparse.Namespace) -> None:
    ref_json = load_reference()
    table = metric_table(ref_json)
    main_scores = json.loads((WS / "scoring" / "scores_test.json").read_text())
    ref_metrics = solver_metrics(main_scores, REFERENCE)
    results: dict = {"reference": ref_metrics, "baseline": solver_metrics(main_scores, BASELINE), "cases": {}}
    results["baseline_rank"] = rank(results["baseline"], ref_metrics, table)
    main_out = WS / "tmp" / "eval_runs" / "test" / "outcomes.jsonl"
    ref_idx = outcome_index(main_out, REFERENCE)
    base_idx = outcome_index(main_out, BASELINE)
    results["baseline_vs_reference_bootstrap"] = paired_bootstrap(base_idx, ref_idx, table)

    # Draw-to-draw noise of the reference: score each hidden perturbation draw separately.
    per_draw = {}
    for line in main_out.read_text().splitlines():
        rec = json.loads(line)
        if rec["solver"] != REFERENCE or rec["family"] != "maros_meszaros":
            continue
        per_draw.setdefault(rec["draw"], {}).setdefault(rec["tolerance"], []).append(rec["solved"])
    results["reference_per_draw_failure_rates"] = {
        str(d): {t: 100.0 * sum(not s for s in v) / len(v) for t, v in tols.items()} for d, tols in sorted(per_draw.items())}

    for case, spec in CASES.items():
        done = HARD / case / "complete.json"
        if not done.is_file():
            results["cases"][case] = {"status": "not run"}
            continue
        info = json.loads(done.read_text())
        entry = {"what": spec["what"], "kind": spec["kind"], "returncode": info["returncode"],
                 "scores_written": info["scores_written"]}
        scores = info.get("scores")
        if scores is not None:
            solver = case if spec["cmd"] else REFERENCE
            m = solver_metrics(scores, solver)
            entry["metrics"] = m
            entry["rank_vs_reference"], entry["rank_parts"] = rank(m, ref_metrics, table)
            # the reference inside the case run must be unchanged (no cross-contamination)
            entry["reference_in_case_run"] = solver_metrics(scores, REFERENCE)
            outcomes = HARD / case / "outcomes.jsonl"
            if spec["cmd"] and outcomes.is_file():
                entry["paired_bootstrap_vs_reference"] = paired_bootstrap(outcome_index(outcomes, case), ref_idx, table)
        results["cases"][case] = entry
    NOTES.mkdir(parents=True, exist_ok=True)
    (NOTES / "results.json").write_text(json.dumps(results, indent=1, default=float) + "\n")
    print(json.dumps(results, indent=1, default=float))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("smoke")
    sub.add_parser("export")
    run = sub.add_parser("run")
    run.add_argument("--cases", nargs="+", default=None)
    run.add_argument("--force", action="store_true")
    sub.add_parser("analyze")
    args = parser.parse_args()
    {"smoke": cmd_smoke, "export": cmd_export, "run": cmd_run, "analyze": cmd_analyze}[args.command](args)


if __name__ == "__main__":
    main()
