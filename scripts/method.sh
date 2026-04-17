#!/bin/bash
# Run ODYN and score the produced raw result file.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

OUTPUT="/home/user/tmp/results/odyn_results.json"
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

python3 -m method.run_odyn --output "$OUTPUT" "${ARGS[@]}"
bash scripts/evaluate.sh --results "$OUTPUT" --output /home/user/scoring/scores.json

