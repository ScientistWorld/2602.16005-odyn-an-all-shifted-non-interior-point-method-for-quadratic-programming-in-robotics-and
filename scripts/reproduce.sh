#!/bin/bash
# End-to-end reproduction entry point.
#
# Runs the full Maros-Meszaros ODYN reproduction plus the OSQP baseline and
# writes scoring/scores.json. This assumes data has already been prepared by
# scripts/download.sh and dependencies by environment/setup.sh.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

echo "=== ODYN full benchmark, medium tolerance (1e-6) ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 3000 \
    --timeout 300 \
    --resume \
    --output /home/user/tmp/results/odyn_full_medium.json

echo "=== ODYN full benchmark, high tolerance (1e-9) ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-9 \
    --max-iter 5000 \
    --timeout 300 \
    --skip-degenerate \
    --resume \
    --output /home/user/tmp/results/odyn_full_high.json

echo "=== OSQP full benchmark, medium tolerance ==="
python3 -m baseline.run_osqp \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 4000 \
    --resume \
    --output /home/user/tmp/results/osqp_full_medium.json

echo "=== OSQP full benchmark, high tolerance ==="
python3 -m baseline.run_osqp \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-9 \
    --max-iter 8000 \
    --skip-degenerate \
    --resume \
    --output /home/user/tmp/results/osqp_full_high.json

echo "=== Scoring ==="
bash scripts/evaluate.sh \
    --results \
        /home/user/tmp/results/odyn_full_medium.json \
        /home/user/tmp/results/odyn_full_high.json \
        /home/user/tmp/results/osqp_full_medium.json \
        /home/user/tmp/results/osqp_full_high.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
