#!/bin/bash
# Recompute ODYN's scored benchmark outputs after the solver update-rule patch.
#
# The current method code changed, so the previous ODYN raw result files are no
# longer the exact artifacts behind the active implementation. This job reruns
# the scored ODYN benchmark end-to-end. ODYN now checkpoints after each
# problem, and this driver advances the benchmark in staged prefixes so resumed
# jobs can make bounded progress even if the cluster preempts a long CPU run.
# The script reuses the unchanged OSQP baseline raw outputs if present and
# rewrites scoring/scores.json from the refreshed raw files.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

DATA_DIR="/home/user/data/maros_meszaros_qpbenchmark/data"
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
    "Patched ODYN medium tolerance (1e-6)" \
    1e-6 \
    3000 \
    300 \
    /home/user/tmp/results/odyn_full_medium.json \
    false

run_odyn_staged \
    "Patched ODYN high tolerance (1e-9)" \
    1e-9 \
    5000 \
    300 \
    /home/user/tmp/results/odyn_full_high.json \
    true

if [[ ! -f /home/user/tmp/results/osqp_full_medium.json ]]; then
    echo "=== OSQP full benchmark, medium tolerance ==="
    python3 -m baseline.run_osqp \
        --data-dir "$DATA_DIR" \
        --rtol 1e-6 \
        --max-iter 4000 \
        --resume \
        --output /home/user/tmp/results/osqp_full_medium.json
fi

if [[ ! -f /home/user/tmp/results/osqp_full_high.json ]]; then
    echo "=== OSQP full benchmark, high tolerance ==="
    python3 -m baseline.run_osqp \
        --data-dir "$DATA_DIR" \
        --rtol 1e-9 \
        --max-iter 8000 \
        --skip-degenerate \
        --resume \
        --output /home/user/tmp/results/osqp_full_high.json
fi

bash scripts/evaluate.sh \
    --results \
        /home/user/tmp/results/odyn_full_medium.json \
        /home/user/tmp/results/odyn_full_high.json \
        /home/user/tmp/results/osqp_full_medium.json \
        /home/user/tmp/results/osqp_full_high.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
