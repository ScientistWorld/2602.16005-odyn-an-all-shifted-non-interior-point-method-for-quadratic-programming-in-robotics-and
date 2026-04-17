#!/bin/bash
# Score one or more raw solver result files.
#
# Usage:
#   bash scripts/evaluate.sh --results tmp/results/odyn_results.json

set -euo pipefail

cd /home/user
mkdir -p scoring

RESULTS=("/home/user/tmp/results/odyn_results.json")
OUTPUT="/home/user/scoring/scores.json"

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

python3 -m eval.benchmark --results "${RESULTS[@]}" --output "$OUTPUT"

