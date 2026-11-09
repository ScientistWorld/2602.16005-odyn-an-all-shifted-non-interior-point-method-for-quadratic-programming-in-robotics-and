#!/bin/bash
# End-to-end reproduction of the packaged scores.
#
# The QP solvers need no training: every evaluator below runs each registered
# solver (scripts/solvers/*.sh, the reference is scripts/solvers/odyn.sh) and
# the OSQP baseline on its own instances and verifies the returned points.
#   scoring/scores.json        paper-level (unperturbed problems)
#   scoring/scores_train.json  visible train slice
#   scoring/scores_test.json   held-out test slice (when eval/test/ is present)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WORKSPACE_DIR"

if [[ ! -d data/maros_meszaros_qpbenchmark/data ]]; then
    bash scripts/download.sh
fi

bash scripts/evaluate.sh
bash scripts/evaluate_train.sh
if [[ -d eval/test ]]; then
    bash scripts/evaluate_test.sh
fi
python3 validate.py --compare
