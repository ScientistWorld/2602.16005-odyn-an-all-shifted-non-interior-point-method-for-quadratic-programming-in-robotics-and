#!/bin/bash
# Score every registered solver (scripts/solvers/*.sh) plus the evaluator-owned
# OSQP baseline on the visible train slice; writes scoring/scores_train.json.
#
# The evaluator runs each solver itself on evaluator-generated instances and
# verifies every returned (x, y, z) with its own KKT check. Optional arguments
# are forwarded, e.g. --solvers odyn osqp, --workers 4, --output tmp/x.json.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WORKSPACE_DIR"
python3 -m eval.train.evaluate "$@"
