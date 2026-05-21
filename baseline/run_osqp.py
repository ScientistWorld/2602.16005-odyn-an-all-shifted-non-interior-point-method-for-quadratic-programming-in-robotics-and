#!/usr/bin/env python3
"""Run OSQP as an open-source baseline on the QP benchmark."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as spa

from data.qplib import degenerate_cases, load_maros_meszaros_problem


def _write_output(path: Path, data: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, allow_nan=True) + "\n")
    tmp_path.replace(path)


def _load_existing_output(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open() as handle:
        return json.load(handle)


def run_osqp(problem: dict[str, Any], rtol: float, max_iter: int) -> dict[str, Any]:
    try:
        import osqp
    except ImportError:
        return {"success": False, "iterations": 0, "solve_time": 0.0, "status": "import_error"}

    Q = problem["Q"] if spa.issparse(problem["Q"]) else spa.csc_matrix(problem["Q"])
    c = problem["c"]
    n = c.shape[0]
    A_eq = problem.get("A")
    G = problem.get("G")

    rows = []
    lower = []
    upper = []
    if A_eq is not None and A_eq.size > 0:
        A_eq = A_eq if spa.issparse(A_eq) else spa.csc_matrix(A_eq)
        rows.append(A_eq)
        lower.append(problem["b"])
        upper.append(problem["b"])
    if G is not None and G.size > 0:
        G = G if spa.issparse(G) else spa.csc_matrix(G)
        rows.append(G)
        lower.append(np.full(G.shape[0], -np.inf))
        upper.append(problem["h"])

    if rows:
        constraints = spa.vstack(rows, format="csc")
        l = np.concatenate(lower)
        u = np.concatenate(upper)
    else:
        constraints = spa.csc_matrix((0, n))
        l = np.empty(0)
        u = np.empty(0)

    solver = osqp.OSQP()
    t0 = time.time()
    try:
        solver.setup(
            Q,
            c,
            constraints,
            l,
            u,
            eps_abs=rtol,
            eps_rel=rtol,
            max_iter=max_iter,
            verbose=False,
            polish=False,
        )
        result = solver.solve()
    except Exception as exc:
        return {"success": False, "iterations": 0, "solve_time": time.time() - t0, "status": f"error: {exc}"}

    return {
        "success": bool(result.info.status_val == 1),
        "iterations": int(result.info.iter),
        "solve_time": float(time.time() - t0),
        "status": str(result.info.status),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="/home/user/data/maros_meszaros_qpbenchmark/data")
    parser.add_argument("--output", default="/home/user/tmp/results/osqp_results.json")
    parser.add_argument("--rtol", type=float, default=1e-6)
    parser.add_argument("--max-iter", type=int, default=2000)
    parser.add_argument("--max-problems", type=int, default=None)
    parser.add_argument("--problems", nargs="*", default=None)
    parser.add_argument("--skip-degenerate", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    files = sorted(Path(args.data_dir).glob("*.mat"))
    if args.problems:
        wanted = {name.removesuffix(".mat") for name in args.problems}
        files = [path for path in files if path.stem in wanted]
    if args.max_problems is not None:
        files = files[: args.max_problems]

    raw: dict[str, Any] = {
        "method": "osqp",
        "metadata": {"rtol": args.rtol, "max_iter": args.max_iter, "data_dir": args.data_dir},
        "degenerate": {},
        "benchmark": [],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.resume:
        existing = _load_existing_output(output)
        if existing is not None:
            if existing.get("method") != "osqp":
                raise ValueError(f"{output} does not contain OSQP results")
            existing_meta = existing.get("metadata", {})
            for key in ("rtol", "max_iter", "data_dir"):
                if existing_meta.get(key) != raw["metadata"].get(key):
                    raise ValueError(f"{output} metadata mismatch for {key}: {existing_meta.get(key)} != {raw['metadata'].get(key)}")
            raw["degenerate"] = existing.get("degenerate", {})
            raw["benchmark"] = existing.get("benchmark", [])
            print(
                f"resuming {output} with {len(raw['degenerate'])} degenerate and "
                f"{len(raw['benchmark'])} benchmark entries"
            )
        else:
            print(f"starting fresh {output}")

    if not args.skip_degenerate:
        for name, problem in degenerate_cases().items():
            if name in raw["degenerate"]:
                print(f"degenerate {name}: skip existing")
                continue
            raw["degenerate"][name] = run_osqp(problem, args.rtol, args.max_iter)
            _write_output(output, raw)

    completed = {str(item.get("name")) for item in raw["benchmark"] if item.get("name")}
    for idx, path in enumerate(files, start=1):
        if path.stem in completed:
            print(f"[{idx}/{len(files)}] {path.stem} skip existing", flush=True)
            continue
        print(f"[{idx}/{len(files)}] {path.stem}", flush=True)
        try:
            problem = load_maros_meszaros_problem(path)
            result = run_osqp(problem, args.rtol, args.max_iter)
        except Exception as exc:
            result = {"success": False, "iterations": 0, "solve_time": 0.0, "status": f"load_error: {exc}"}
        result["name"] = path.stem
        raw["benchmark"].append(result)
        print(f"{path.stem}: {result['status']} success={result['success']} it={result['iterations']}")
        _write_output(output, raw)

    _write_output(output, raw)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
