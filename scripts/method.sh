#!/bin/bash
# Score the reference solver alone on the train slice (development loop).
# Writes tmp/scores_train_odyn.json; the official train scores come from
# scripts/evaluate_train.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WORKSPACE_DIR"
mkdir -p tmp
python3 -m eval.train.evaluate --solvers odyn --output tmp/scores_train_odyn.json "$@"
