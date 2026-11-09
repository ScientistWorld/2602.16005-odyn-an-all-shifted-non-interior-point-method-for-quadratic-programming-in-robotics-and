#!/bin/bash
# Held-out test: score every registered solver (scripts/solvers/*.sh) plus the
# evaluator-owned OSQP baseline on instances generated inside eval/test/;
# writes scoring/scores_test.json. Runs with no arguments.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WORKSPACE_DIR"
python3 -m eval.test.evaluate "$@"
