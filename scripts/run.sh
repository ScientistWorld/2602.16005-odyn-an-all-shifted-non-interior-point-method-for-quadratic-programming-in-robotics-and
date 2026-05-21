#!/bin/bash
# Recompute ODYN's scored benchmark outputs after the solver update-rule patch.
#
# The current method code changed, so the previous ODYN raw result files are no
# longer the exact artifacts behind the active implementation. This job reruns
# the scored ODYN benchmark end-to-end, reuses the unchanged OSQP baseline raw
# outputs if present, and rewrites scoring/scores.json from the refreshed raw
# files.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

echo "=== Patched ODYN full benchmark, medium tolerance (1e-6) ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 3000 \
    --timeout 300 \
    --output /home/user/tmp/results/odyn_full_medium.json

echo "=== Patched ODYN full benchmark, high tolerance (1e-9) ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-9 \
    --max-iter 5000 \
    --timeout 300 \
    --skip-degenerate \
    --output /home/user/tmp/results/odyn_full_high.json

if [[ ! -f /home/user/tmp/results/osqp_full_medium.json ]]; then
    echo "=== OSQP full benchmark, medium tolerance ==="
    python3 -m baseline.run_osqp \
        --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
        --rtol 1e-6 \
        --max-iter 4000 \
        --output /home/user/tmp/results/osqp_full_medium.json
fi

if [[ ! -f /home/user/tmp/results/osqp_full_high.json ]]; then
    echo "=== OSQP full benchmark, high tolerance ==="
    python3 -m baseline.run_osqp \
        --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
        --rtol 1e-9 \
        --max-iter 8000 \
        --skip-degenerate \
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
