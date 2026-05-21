#!/bin/bash
# Recompute ODYN's scored benchmark outputs after the solver update-rule patch.
#
# The current method code changed, so the previous ODYN raw result files are no
# longer the exact artifacts behind the active implementation. This job reruns
# the scored ODYN benchmark end-to-end. ODYN now checkpoints after each
# problem, and this driver advances the benchmark in staged prefixes so resumed
# jobs can make bounded progress even if the cluster preempts a long CPU run.
# The script also verifies that baseline raw outputs are complete before
# rescoring. File existence alone is not enough after repeated preemptions.

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

    local count
    count="$(result_entry_count "$output")"
    if [[ "$count" == "$TOTAL_PROBLEMS" ]]; then
        echo "=== ${label} already complete (${count}/${TOTAL_PROBLEMS}) ==="
        return
    fi

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

result_entry_count() {
    local path="$1"
    python3 - <<'PY' "$path"
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.exists():
    print(-1)
else:
    data = json.loads(path.read_text())
    print(len(data.get("benchmark", [])))
PY
}

run_osqp_if_incomplete() {
    local label="$1"
    local rtol="$2"
    local max_iter="$3"
    local output="$4"
    local skip_degenerate="$5"
    local expected="$6"

    local count
    count="$(result_entry_count "$output")"
    if [[ "$count" == "$expected" ]]; then
        echo "=== ${label} already complete (${count}/${expected}) ==="
        return
    fi

    echo "=== ${label} resume (${count}/${expected}) ==="
    local extra_args=()
    if [[ "$skip_degenerate" == "true" ]]; then
        extra_args+=(--skip-degenerate)
    fi
    python3 -m baseline.run_osqp \
        --data-dir "$DATA_DIR" \
        --rtol "$rtol" \
        --max-iter "$max_iter" \
        --resume \
        --output "$output" \
        "${extra_args[@]}"
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

run_osqp_if_incomplete \
    "OSQP full benchmark, medium tolerance" \
    1e-6 \
    4000 \
    /home/user/tmp/results/osqp_full_medium.json \
    false \
    "$TOTAL_PROBLEMS"

run_osqp_if_incomplete \
    "OSQP full benchmark, high tolerance" \
    1e-9 \
    8000 \
    /home/user/tmp/results/osqp_full_high.json \
    true \
    "$TOTAL_PROBLEMS"

bash scripts/evaluate.sh \
    --results \
        /home/user/tmp/results/odyn_full_medium.json \
        /home/user/tmp/results/odyn_full_high.json \
        /home/user/tmp/results/osqp_full_medium.json \
        /home/user/tmp/results/osqp_full_high.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
