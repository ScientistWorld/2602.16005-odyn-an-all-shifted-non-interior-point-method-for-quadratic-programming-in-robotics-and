#!/bin/bash
# Optional baseline entry point. The core reproduction focuses on ODYN; this
# script runs the OSQP baseline when the package is available in the container.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$WORKSPACE_DIR"
mkdir -p tmp/results scoring

python3 -m baseline.run_osqp \
    --data-dir "$WORKSPACE_DIR/data/maros_meszaros_qpbenchmark/data" \
    --resume \
    --output "$WORKSPACE_DIR/tmp/results/osqp_results.json" \
    "$@"

bash scripts/evaluate.sh \
    --results "$WORKSPACE_DIR/tmp/results/osqp_results.json" \
    --output "$WORKSPACE_DIR/scoring/scores.json"
