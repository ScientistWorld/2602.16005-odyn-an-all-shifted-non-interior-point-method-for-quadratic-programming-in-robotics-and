#!/usr/bin/env python3
"""Score raw QP solver result files against the paper's benchmark targets.

This module is deliberately method-agnostic. It reads JSON result files produced
by ``method/`` or ``baseline/`` runners and writes ``scoring/scores.json``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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


def load_result(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    if "method" not in data:
        raise ValueError(f"{path} is missing top-level 'method'")
    return data


def _default_result_paths(workspace: Path) -> list[Path]:
    packaged = sorted((workspace / "scoring" / "raw_results").glob("*.json"))
    if packaged:
        return packaged
    return sorted((workspace / "tmp" / "results").glob("*.json"))


def score_failure_rate(raw: dict[str, Any]) -> dict[str, float] | None:
    benchmark = raw.get("benchmark") or []
    attempted = [item for item in benchmark if _is_attempted(item)]
    if not attempted:
        return None
    failed = sum(1 for item in attempted if not bool(item.get("success", False)))
    total = len(attempted)
    rate = 100.0 * failed / total if total else 100.0
    metric = _metric_for_tolerance(float(raw.get("metadata", {}).get("rtol", 1e-6)))
    iteration_metric = "mean_iterations_high" if metric == "failure_rate_high" else "mean_iterations_medium"
    max_iter = float(raw.get("metadata", {}).get("max_iter", 200))
    iteration_denominator = len(benchmark) if benchmark else total
    total_iterations = 0.0
    for item in benchmark:
        if _is_attempted(item) and bool(item.get("success", False)):
            total_iterations += min(max(_finite_number(item.get("iterations"), max_iter), 0.0), max_iter)
        else:
            total_iterations += max_iter
    return {
        metric: rate,
        iteration_metric: total_iterations / iteration_denominator if iteration_denominator else max_iter,
        "attempted_count": float(total),
    }


def _is_attempted(item: dict[str, Any]) -> bool:
    status = str(item.get("status", ""))
    return bool(item.get("attempted", not status.startswith("skipped_")))


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
        if bool(item.get("success", False)):
            out[key] = _finite_number(item.get("iterations"), max_iter)
        else:
            out[key] = max_iter
    return out or None


def build_scores(result_paths: list[Path]) -> dict[str, Any]:
    if not result_paths:
        raise ValueError("no raw result JSON files were provided or discovered")

    workspace = Path.cwd().resolve()
    provenance_paths = []
    for path in result_paths:
        resolved = path.resolve()
        try:
            provenance_paths.append(str(resolved.relative_to(workspace)))
        except ValueError:
            provenance_paths.append(str(resolved))

    scores: dict[str, Any] = {
        "_provenance": {
            "generator": "eval.benchmark",
            "raw_results": provenance_paths,
        },
        "experiments": {},
    }
    failure_results: dict[str, dict[str, float]] = {}
    degenerate_results: dict[str, dict[str, float]] = {}

    for path in result_paths:
        raw = load_result(path)
        method = str(raw["method"])

        failure_score = score_failure_rate(raw)
        if failure_score is not None:
            failure_results.setdefault(method, {}).update(failure_score)

        degenerate_score = score_degenerate(raw)
        if degenerate_score is not None:
            degenerate_results.setdefault(method, {}).update(degenerate_score)

    if failure_results:
        scores["experiments"]["failure_rate_comparison"] = {"results": failure_results}
    if degenerate_results:
        scores["experiments"]["degenerate_problems"] = {"results": degenerate_results}

    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        nargs="+",
        default=None,
        help="One or more raw result JSON files to score. Defaults to scoring/raw_results/*.json, then tmp/results/*.json.",
    )
    parser.add_argument("--output", default=str(Path.cwd() / "scoring" / "scores.json"))
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
