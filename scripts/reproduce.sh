#!/bin/bash
# End-to-end reproduction entry point.
#
# Runs the full Maros-Meszaros ODYN reproduction plus the OSQP baseline and
# writes scoring/scores.json. This assumes data has already been prepared by
# scripts/download.sh and dependencies by environment/setup.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$WORKSPACE_DIR"
mkdir -p tmp/results scoring

DATA_DIR="$WORKSPACE_DIR/data/maros_meszaros_qpbenchmark/data"
if [[ ! -d "$DATA_DIR" ]]; then
    bash scripts/download.sh
fi
TOTAL_PROBLEMS="$(find "$DATA_DIR" -maxdepth 1 -name '*.mat' | wc -l | tr -d ' ')"

run_odyn_staged() {
    local label="$1"
    local rtol="$2"
    local max_iter="$3"
    local timeout="$4"
    local output="$5"
    local skip_degenerate="$6"

    local stages=(40 80 120 "$TOTAL_PROBLEMS")
    local extra_args=()
    if [[ "$skip_degenerate" == "true" ]]; then
        extra_args+=(--skip-degenerate)
    fi

    for stage in "${stages[@]}"; do
        if (( stage > TOTAL_PROBLEMS )); then
            continue
        fi
        echo "=== ${label} up to ${stage}/${TOTAL_PROBLEMS} problems ==="
        python3 -m method.run_odyn \
            --data-dir "$DATA_DIR" \
            --rtol "$rtol" \
            --max-iter "$max_iter" \
            --timeout "$timeout" \
            --max-problems "$stage" \
            --resume \
            --output "$output" \
            "${extra_args[@]}"
    done
}

run_odyn_staged \
    "ODYN medium tolerance (1e-6)" \
    1e-6 \
    3000 \
    300 \
    "$WORKSPACE_DIR/tmp/results/odyn_full_medium.json" \
    false

run_odyn_staged \
    "ODYN high tolerance (1e-9)" \
    1e-9 \
    5000 \
    300 \
    "$WORKSPACE_DIR/tmp/results/odyn_full_high.json" \
    true

echo "=== OSQP full benchmark, medium tolerance ==="
python3 -m baseline.run_osqp \
    --data-dir "$DATA_DIR" \
    --rtol 1e-6 \
    --max-iter 4000 \
    --resume \
    --output "$WORKSPACE_DIR/tmp/results/osqp_full_medium.json"

echo "=== OSQP full benchmark, high tolerance ==="
python3 -m baseline.run_osqp \
    --data-dir "$DATA_DIR" \
    --rtol 1e-9 \
    --max-iter 8000 \
    --skip-degenerate \
    --resume \
    --output "$WORKSPACE_DIR/tmp/results/osqp_full_high.json"

echo "=== Scoring ==="
bash scripts/evaluate.sh \
    --results \
        "$WORKSPACE_DIR/tmp/results/odyn_full_medium.json" \
        "$WORKSPACE_DIR/tmp/results/odyn_full_high.json" \
        "$WORKSPACE_DIR/tmp/results/osqp_full_medium.json" \
        "$WORKSPACE_DIR/tmp/results/osqp_full_high.json" \
    --output "$WORKSPACE_DIR/scoring/scores.json"

python3 validate.py --compare
