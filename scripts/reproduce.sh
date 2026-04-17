#!/bin/bash
# End-to-end reproduction entry point.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

echo "=== ODYN QP Solver Reproduction ==="
echo "[1/2] Medium-accuracy Maros-Meszaros benchmark"
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 250 \
    --timeout 120 \
    --output /home/user/tmp/results/odyn_medium.json

echo "[2/2] Scoring"
bash scripts/evaluate.sh \
    --results /home/user/tmp/results/odyn_medium.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare

