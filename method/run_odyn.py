#!/usr/bin/env python3
"""Run the reproduced ODYN solver and write method-agnostic raw results."""

from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import scipy.sparse as spa

from data.qplib import degenerate_cases, estimated_dense_size_gb, load_maros_meszaros_problem
from method.odyn_solver import DenseOdynSolver, OdynParams, SparseOdynSolver


class SolverTimeout(RuntimeError):
    pass


def _timeout_handler(signum, frame):  # noqa: ARG001
    raise SolverTimeout("timeout")


def _matrix_for_solver(matrix: Any, dense: bool) -> Any:
    if matrix is None:
        return None
    if dense and spa.issparse(matrix):
        return matrix.toarray()
    if not dense and not spa.issparse(matrix):
        return spa.csc_matrix(matrix)
    return matrix


def _write_output(path: Path, data: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, allow_nan=True) + "\n")
    tmp_path.replace(path)


def _load_existing_output(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open() as handle:
        return json.load(handle)


def run_odyn(
    problem: dict[str, Any],
    *,
    rtol: float,
    max_iter: int,
    timeout: int,
    dense: bool,
    rho: float | None = None,
    rho_min: float | None = None,
) -> dict[str, Any]:
    params = OdynParams()
    params.max_iter = max_iter
    if rho is not None:
        params.rho = rho
    if rho_min is not None:
        params.rho_min = rho_min
    solver = DenseOdynSolver(params) if dense else SparseOdynSolver(params)

    Q = _matrix_for_solver(problem["Q"], dense)
    A = _matrix_for_solver(problem.get("A"), dense)
    G = _matrix_for_solver(problem.get("G"), dense)

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(max(timeout, 1))
    t0 = time.time()
    try:
        result = solver.solve(
            Q,
            problem["c"],
            None if A is None or A.size == 0 else A,
            None if problem.get("b") is None else problem["b"],
            None if G is None or G.size == 0 else G,
            None if problem.get("h") is None else problem["h"],
            rtol=rtol,
            atol=rtol * 1e-2,
        )
        elapsed = time.time() - t0
        return {
            "success": bool(result.success),
            "iterations": int(result.iterations),
            "solve_time": float(elapsed),
            "status": result.status,
            "primal_residual": float(result.primal_residual),
            "dual_residual": float(result.dual_residual),
            "infeasibility": float(result.infeasibility),
            "x": result.x.tolist() if result.x is not None and result.x.size <= 1000 else None,
        }
    except SolverTimeout:
        return {
            "success": False,
            "iterations": max_iter,
            "solve_time": float(time.time() - t0),
            "status": "timeout",
            "primal_residual": float("nan"),
            "dual_residual": float("nan"),
            "infeasibility": float("nan"),
            "x": None,
        }
    except Exception as exc:  # keep raw result files useful for debugging failed problems
        return {
            "success": False,
            "iterations": 0,
            "solve_time": float(time.time() - t0),
            "status": f"error: {exc}",
            "primal_residual": float("nan"),
            "dual_residual": float("nan"),
            "infeasibility": float("nan"),
            "x": None,
        }
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def run_degenerate(
    rtol: float,
    max_iter: int,
    timeout: int,
    rho: float | None,
    rho_min: float | None,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = dict(existing or {})
    for name, problem in degenerate_cases().items():
        if name in out:
            print(f"degenerate {name}: skip existing")
            continue
        result = run_odyn(problem, rtol=rtol, max_iter=max_iter, timeout=timeout, dense=True, rho=rho, rho_min=rho_min)
        out[name] = result
        print(f"degenerate {name}: {result['status']} {result['iterations']} it")
    return out


def iter_problem_files(data_dir: Path, max_problems: int | None, problems: list[str] | None) -> list[Path]:
    files = sorted(data_dir.glob("*.mat"))
    if problems:
        wanted = {p.removesuffix(".mat") for p in problems}
        files = [path for path in files if path.stem in wanted]
    if max_problems is not None:
        files = files[:max_problems]
    return files


def run_benchmark(
    args: argparse.Namespace,
    existing: list[dict[str, Any]] | None = None,
    *,
    checkpoint: Callable[[list[dict[str, Any]]], None] | None = None,
) -> list[dict[str, Any]]:
    files = iter_problem_files(Path(args.data_dir), args.max_problems, args.problems)
    raw: list[dict[str, Any]] = list(existing or [])
    completed = {str(item.get("name")) for item in raw if item.get("name")}
    for idx, mat_file in enumerate(files, start=1):
        if mat_file.stem in completed:
            print(f"[{idx}/{len(files)}] {mat_file.stem} skip existing", flush=True)
            continue
        print(f"[{idx}/{len(files)}] {mat_file.stem}", flush=True)
        try:
            problem = load_maros_meszaros_problem(mat_file)
        except Exception as exc:
            raw.append({"name": mat_file.stem, "success": False, "status": f"load_error: {exc}", "iterations": 0, "attempted": True})
            continue

        dense_gb = estimated_dense_size_gb(problem)
        dense = dense_gb <= args.max_dense_gb and problem["Q"].shape[0] <= args.max_dense_n
        if not dense and not args.allow_sparse:
            raw.append({
                "name": problem["name"],
                "success": False,
                "status": f"skipped_memory_estimate_{dense_gb:.2f}GB",
                "iterations": 0,
                "solve_time": 0.0,
                "attempted": False,
            })
            if checkpoint is not None:
                checkpoint(raw)
            continue

        result = run_odyn(
            problem,
            rtol=args.rtol,
            max_iter=args.max_iter,
            timeout=args.timeout,
            dense=dense,
            rho=args.rho,
            rho_min=args.rho_min,
        )
        result.update({"name": problem["name"], "dense": dense, "dense_size_gb": dense_gb, "attempted": True})
        print(f"  {result['status']} success={result['success']} it={result['iterations']} time={result['solve_time']:.2f}s")
        raw.append(result)
        if checkpoint is not None:
            checkpoint(raw)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="/home/user/data/maros_meszaros_qpbenchmark/data")
    parser.add_argument("--output", default="/home/user/tmp/results/odyn_results.json")
    parser.add_argument("--rtol", type=float, default=1e-6)
    parser.add_argument("--max-iter", type=int, default=250)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-problems", type=int, default=None)
    parser.add_argument("--problems", nargs="*", default=None)
    parser.add_argument("--max-dense-gb", type=float, default=2.0)
    parser.add_argument("--max-dense-n", type=int, default=1000)
    parser.add_argument("--rho", type=float, default=None)
    parser.add_argument("--rho-min", type=float, default=None)
    parser.add_argument("--allow-sparse", action="store_true")
    parser.add_argument("--degenerate-only", action="store_true")
    parser.add_argument("--skip-degenerate", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {
        "method": "odyn",
        "metadata": {
            "rtol": args.rtol,
            "max_iter": args.max_iter,
            "timeout": args.timeout,
            "data_dir": args.data_dir,
            "rho": args.rho,
            "rho_min": args.rho_min,
        },
        "degenerate": {},
        "benchmark": [],
    }
    if args.resume:
        existing = _load_existing_output(output)
        if existing is not None:
            if existing.get("method") != "odyn":
                raise ValueError(f"{output} does not contain ODYN results")
            existing_meta = existing.get("metadata", {})
            for key in ("rtol", "max_iter", "timeout", "data_dir", "rho", "rho_min"):
                if existing_meta.get(key) != data["metadata"].get(key):
                    raise ValueError(f"{output} metadata mismatch for {key}: {existing_meta.get(key)} != {data['metadata'].get(key)}")
            data["degenerate"] = existing.get("degenerate", {})
            data["benchmark"] = existing.get("benchmark", [])
            print(
                f"resuming {output} with {len(data['degenerate'])} degenerate and "
                f"{len(data['benchmark'])} benchmark entries"
            )
        else:
            print(f"starting fresh {output}")

    if not args.skip_degenerate:
        data["degenerate"] = run_degenerate(
            args.rtol,
            args.max_iter,
            args.timeout,
            args.rho,
            args.rho_min,
            existing=data["degenerate"],
        )
        _write_output(output, data)
    if not args.degenerate_only:
        def _checkpoint(benchmark: list[dict[str, Any]]) -> None:
            data["benchmark"] = benchmark
            _write_output(output, data)

        data["benchmark"] = run_benchmark(args, existing=data["benchmark"], checkpoint=_checkpoint)
        _write_output(output, data)

    _write_output(output, data)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
