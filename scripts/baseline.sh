#!/bin/bash
# Score the evaluator-owned OSQP baseline alone on the train slice.
# (The baseline lives in eval/*/osqp_solver.py and is included automatically
# by scripts/evaluate_{train,test}.sh and scripts/evaluate.sh.)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WORKSPACE_DIR"
mkdir -p tmp
python3 -m eval.train.evaluate --solvers osqp --output tmp/scores_train_osqp.json "$@"
