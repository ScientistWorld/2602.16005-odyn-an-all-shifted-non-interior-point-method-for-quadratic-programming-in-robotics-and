#!/usr/bin/env python3
"""Variant and shortcut solvers used to audit the hidden test (hardening only).

Each mode is registered as ``scripts/solvers/<case>.sh`` inside an isolated copy
of the workspace and scored by the unmodified ``scripts/evaluate_test.sh``.

ODYN is deterministic, so modes that differ from the reference only after the
reference has stopped reuse the reference's own output for the identical
instance ("memo", exported from the reference's hidden-test run) instead of
recomputing the same iterations:

* ``more_iter``   better variant: twice the iteration cap. Reference runs that
                  stopped on their own criterion are identical, runs that hit the
                  cap (or produced no output) are recomputed with the larger cap.
* ``hide_failures`` writes the reference output only when the reference reported
                  success, nothing otherwise (old "relabel failures as skipped").
* ``ignore_degenerate`` refuses instances that look structurally degenerate
                  (zero or parallel duplicate rows), reference output otherwise.
* ``fake_iterations`` reference output with ``iterations=1``.
* ``claim_success`` no solve: zero vectors, ``status='optimal'``, ``iterations=0``.
* ``no_output``   no solve, no file (old zero/negative iteration-cap shortcuts).
* ``replay_public`` no solve: returns the reference solution of the public,
                  unperturbed problem with the same dimensions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from data.qp_format import read_instance, write_solution  # noqa: E402


def content_hash(path: str) -> str:
    digest = hashlib.sha256()
    with np.load(path, allow_pickle=False) as data:
        for key in sorted(data.files):
            arr = np.ascontiguousarray(data[key])
            digest.update(key.encode())
            digest.update(arr.dtype.str.encode())
            digest.update(str(arr.shape).encode())
            digest.update(arr.tobytes())
    return digest.hexdigest()


def tol_key(tol: float) -> str:
    return "medium" if tol > 1e-8 else "high"


def memo_lookup(memo: Path, problem_path: str, tol: float) -> tuple[Path | None, bool]:
    """Return (reference output or None, whether the reference was run at all)."""
    stem = f"{content_hash(problem_path)}_{tol_key(tol)}"
    out = memo / f"{stem}.npz"
    if out.is_file():
        return out, True
    return None, (memo / f"{stem}.none").is_file()


def reported_status(path: Path) -> str:
    with np.load(path, allow_pickle=False) as data:
        return str(np.asarray(data["status"]).reshape(-1)[0]) if "status" in data.files else ""


def looks_degenerate(problem: dict) -> bool:
    if problem["n"] > 200:
        return False
    rows = []
    if problem["p"]:
        rows.append(problem["G"].toarray())
    if problem["m"]:
        rows.append(problem["A"].toarray())
    if not rows:
        return False
    M = np.vstack(rows)
    norms = np.linalg.norm(M, axis=1)
    if np.any(norms == 0):
        return True
    U = np.round(M / norms[:, None], 9)
    return len({tuple(r) for r in U}) < U.shape[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--memo", default=None)
    parser.add_argument("--bank", default=None)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tol", type=float, required=True)
    args = parser.parse_args()
    memo = Path(args.memo) if args.memo else None
    mode = args.mode

    if mode == "no_output":
        return
    if mode == "claim_success":
        prob = read_instance(args.problem)
        write_solution(args.output, np.zeros(prob["n"]), np.zeros(prob["m"]), np.zeros(prob["p"]),
                       iterations=np.int64(0), status=np.array("optimal"))
        return
    if mode == "replay_public":
        prob = read_instance(args.problem)
        index = json.loads((Path(args.bank) / "index.json").read_text())
        dims = [prob["n"], prob["m"], prob["p"]]
        for name, info in sorted(index.items()):
            if info["dims"] == dims and tol_key(args.tol) in info["files"]:
                shutil.copyfile(Path(args.bank) / info["files"][tol_key(args.tol)], args.output)
                return
        return
    if mode in ("hide_failures", "fake_iterations", "ignore_degenerate"):
        ref, _ = memo_lookup(memo, args.problem, args.tol)
        if ref is None:
            return
        if mode == "hide_failures":
            if reported_status(ref) == "optimal":
                shutil.copyfile(ref, args.output)
            return
        if mode == "ignore_degenerate":
            if not looks_degenerate(read_instance(args.problem)):
                shutil.copyfile(ref, args.output)
            return
        with np.load(ref, allow_pickle=False) as data:
            write_solution(args.output, data["x"], data["y"], data["z"], iterations=np.int64(1),
                           status=np.array("optimal"))
        return
    if mode == "more_iter":
        ref, _ = memo_lookup(memo, args.problem, args.tol)
        if ref is not None and reported_status(ref) != "max_iterations":
            shutil.copyfile(ref, args.output)  # identical deterministic path: it stopped before the cap
            return
        from method.solve_cli import default_max_iter, solve_instance  # noqa: PLC0415

        prob = read_instance(args.problem)
        result = solve_instance(prob, args.tol, 2 * default_max_iter(args.tol))
        y = result.y if result.y is not None else np.zeros(prob["m"])
        z = result.z if result.z is not None else np.zeros(prob["p"])
        write_solution(args.output, result.x, y, z, iterations=np.int64(result.iterations),
                       status=np.array(str(result.status)))
        return
    raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
