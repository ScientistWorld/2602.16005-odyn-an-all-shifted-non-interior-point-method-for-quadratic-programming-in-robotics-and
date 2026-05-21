#!/bin/bash
# Score one or more raw solver result files on the visible train slice.
#
# Usage:
#   bash scripts/evaluate_train.sh --results tmp/results/odyn_results.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$WORKSPACE_DIR"
mkdir -p scoring

RESULTS=()
OUTPUT="$WORKSPACE_DIR/scoring/scores_train.json"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --results)
            shift
            RESULTS=()
            while [[ $# -gt 0 && "$1" != --* ]]; do
                RESULTS+=("$1")
                shift
            done
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

CMD=(python3 -m eval.train.evaluate --output "$OUTPUT")
if [[ "${#RESULTS[@]}" -gt 0 ]]; then
    CMD+=(--results "${RESULTS[@]}")
fi

"${CMD[@]}"
