#!/usr/bin/env python3
"""Score the visible train slice of the QP benchmark.

This scorer is method-agnostic: it reads raw solver result JSON files produced
elsewhere and never imports or executes code from ``method/``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SLICE = "train"
DEGENERATE_KEYS = ("redundant_ineq", "licq_failure", "multiple_solutions")


def _metric_for_tolerance(rtol: float) -> str:
    return "failure_rate_high" if rtol <= 1e-9 else "failure_rate_medium"


def _finite_number(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return number


def _nonnegative_finite_number(value: Any, default: float) -> float:
    return max(0.0, _finite_number(value, default))


def _workspace_relative(path: Path, workspace: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(workspace))
    except ValueError:
        return str(resolved)


def _default_result_paths(workspace: Path) -> list[Path]:
    packaged = sorted((workspace / "scoring" / "raw_results").glob("*.json"))
    if packaged:
        return packaged
    return sorted((workspace / "tmp" / "results").glob("*.json"))


def _load_problem_names() -> list[str]:
    manifest = Path(__file__).with_name("problem_names.json")
    data = json.loads(manifest.read_text())
    if data.get("slice") != SLICE:
        raise ValueError(f"{manifest} has slice={data.get('slice')!r}, expected {SLICE!r}")
    names = data.get("problem_names")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError(f"{manifest} must contain a string problem_names list")
    return names


def load_result(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    if "method" not in data:
        raise ValueError(f"{path} is missing top-level 'method'")
    return data


def _is_attempted(item: dict[str, Any]) -> bool:
    status = str(item.get("status", ""))
    return bool(item.get("attempted", not status.startswith("skipped_")))


def _is_success(item: dict[str, Any], rtol: float) -> bool:
    return bool(item.get("success", False))


def score_failure_rate(raw: dict[str, Any], problem_names: list[str]) -> dict[str, float]:
    by_name = {
        str(item.get("name")): item
        for item in raw.get("benchmark", [])
        if item.get("name") is not None
    }
    rtol = float(raw.get("metadata", {}).get("rtol", 1e-6))
    max_iter = float(raw.get("metadata", {}).get("max_iter", 200))
    failed = 0
    attempted = 0
    total_iterations = 0.0

    for name in problem_names:
        item = by_name.get(name)
        if item is None:
            total_iterations += max_iter
            continue
        if not _is_attempted(item):
            total_iterations += max_iter
            continue
        attempted += 1
        if _is_success(item, rtol):
            total_iterations += min(_nonnegative_finite_number(item.get("iterations"), max_iter), max_iter)
        else:
            failed += 1
            total_iterations += max_iter

    rate = 100.0 * failed / attempted if attempted else 100.0
    metric = _metric_for_tolerance(rtol)
    iteration_metric = "mean_iterations_high" if metric == "failure_rate_high" else "mean_iterations_medium"
    total = len(problem_names)
    return {metric: rate, iteration_metric: total_iterations / total if total else max_iter, "attempted_count": float(attempted)}


def score_degenerate(raw: dict[str, Any]) -> dict[str, float] | None:
    degenerate = raw.get("degenerate") or {}
    if not degenerate:
        return None
    out: dict[str, float] = {}
    max_iter = float(raw.get("metadata", {}).get("max_iter", 200))
    for key in DEGENERATE_KEYS:
        item = degenerate.get(key)
        if not item:
            continue
        out[key] = _finite_number(item.get("iterations"), max_iter)
    return out or None


def _merge_metrics(target: dict[str, float], update: dict[str, float]) -> None:
    for key, value in update.items():
        if key == "attempted_count" and key in target:
            target[key] = max(target[key], value)
        else:
            target[key] = value


def build_scores(result_paths: list[Path]) -> dict[str, Any]:
    if not result_paths:
        raise ValueError("no raw result JSON files were provided or discovered")

    workspace = Path.cwd().resolve()
    problem_names = _load_problem_names()
    scores: dict[str, Any] = {
        "_provenance": {
            "generator": "eval.train.evaluate",
            "slice": SLICE,
            "split_manifest": _workspace_relative(Path(__file__).with_name("problem_names.json"), workspace),
            "raw_results": [_workspace_relative(path, workspace) for path in result_paths],
            "target_problem_count": len(problem_names),
            "success_criterion": "solver success flag among attempted slice problems; attempted_count exposes coverage, and missing/skipped/failed problems receive the iteration cap for convergence-cost metrics",
        },
        "experiments": {},
    }
    failure_results: dict[str, dict[str, float]] = {}

    for path in result_paths:
        raw = load_result(path)
        method = str(raw["method"])

        failure_score = score_failure_rate(raw, problem_names)
        _merge_metrics(failure_results.setdefault(method, {}), failure_score)

    if failure_results:
        scores["experiments"]["failure_rate_comparison"] = {"results": failure_results}

    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        nargs="+",
        default=None,
        help="One or more raw result JSON files to score. Defaults to scoring/raw_results/*.json, then tmp/results/*.json.",
    )
    parser.add_argument("--output", default=str(Path.cwd() / "scoring" / "scores_train.json"))
    args = parser.parse_args()

    workspace = Path.cwd().resolve()
    result_paths = [Path(path) for path in args.results] if args.results else _default_result_paths(workspace)
    scores = build_scores(result_paths)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2) + "\n")
    print(json.dumps(scores, indent=2))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
