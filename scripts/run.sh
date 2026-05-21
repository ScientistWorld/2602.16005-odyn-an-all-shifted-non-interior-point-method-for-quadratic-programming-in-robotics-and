#!/bin/bash
# Container smoke verification for the packaged ODYN reproduction.
# This job is post-hoc scoring and validation only; it does not rerun the
# already-completed QP benchmark artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$WORKSPACE_DIR"

bash scripts/evaluate_train.sh \
    --results \
        "$WORKSPACE_DIR/tmp/results/odyn_full_medium.json" \
        "$WORKSPACE_DIR/tmp/results/odyn_full_high.json" \
        "$WORKSPACE_DIR/tmp/results/osqp_full_medium.json" \
        "$WORKSPACE_DIR/tmp/results/osqp_full_high.json"

bash scripts/evaluate_test.sh \
    --results \
        "$WORKSPACE_DIR/tmp/results/odyn_full_medium.json" \
        "$WORKSPACE_DIR/tmp/results/odyn_full_high.json" \
        "$WORKSPACE_DIR/tmp/results/osqp_full_medium.json" \
        "$WORKSPACE_DIR/tmp/results/osqp_full_high.json"

bash scripts/evaluate.sh \
    --results \
        "$WORKSPACE_DIR/tmp/results/odyn_full_medium.json" \
        "$WORKSPACE_DIR/tmp/results/odyn_full_high.json" \
        "$WORKSPACE_DIR/tmp/results/osqp_full_medium.json" \
        "$WORKSPACE_DIR/tmp/results/osqp_full_high.json" \
    --output "$WORKSPACE_DIR/scoring/scores.json"

python3 validate.py --compare
