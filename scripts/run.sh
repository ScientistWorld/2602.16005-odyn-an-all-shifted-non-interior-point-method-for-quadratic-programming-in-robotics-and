#!/bin/bash
# Populate the visible train and held-out test scores from existing raw solver
# artifacts. This job is post-hoc scoring only; it does not retrain or rerun
# the method.

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
