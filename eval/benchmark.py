#!/usr/bin/env python3
"""Paper-level reproduction scores (``scoring/scores.json``).

Runs every registered solver plus the evaluator-owned OSQP baseline on the
original, unperturbed tractable Maros-Meszaros problems (the paper's failure-rate
table, on this benchmark's problem subset) and on the paper's three small
degenerate QPs, with the same verification, tolerances, and CPU budget as the
train/test evaluators. It reuses the train-side machinery; the held-out test
slice has its own independent evaluator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import eval.train.evaluate as E

MANIFEST = Path(__file__).with_name("benchmark_manifest.json")
DEFAULT_OUTPUT = E.WORKSPACE / "scoring" / "scores.json"


def build_instances() -> list[E.Instance]:
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("protocol") != E.PROTOCOL:
        raise SystemExit(f"{MANIFEST}: unexpected protocol")
    base = E.load_base_problems(manifest["maros_meszaros"]["problems"])
    instances = [E._make_instance(f"mm/{name}/orig", "maros_meszaros", name, -1, base[name]) for name in sorted(base)]
    for name, prob in E.paper_degenerate_problems().items():
        instances.append(E._make_instance(f"deg/paper_{name}", "degenerate", f"paper_{name}", -1, prob))
    return instances


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solvers", nargs="+", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        output.unlink()
    E.evaluate(build_instances(), output, slice_name="paper", only=args.solvers, workers=args.workers,
               keep_workdir=False, provenance_extra={"manifest": str(MANIFEST.relative_to(E.WORKSPACE))})


if __name__ == "__main__":
    main()
