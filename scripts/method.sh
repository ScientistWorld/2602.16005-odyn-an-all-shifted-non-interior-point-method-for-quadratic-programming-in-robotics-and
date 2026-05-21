#!/bin/bash
# Run ODYN and score the produced raw result file.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$WORKSPACE_DIR"
mkdir -p tmp/results scoring

OUTPUT="$WORKSPACE_DIR/tmp/results/odyn_results.json"
ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

python3 -m method.run_odyn --resume --output "$OUTPUT" "${ARGS[@]}"
bash scripts/evaluate.sh --results "$OUTPUT" --output "$WORKSPACE_DIR/scoring/scores.json"
