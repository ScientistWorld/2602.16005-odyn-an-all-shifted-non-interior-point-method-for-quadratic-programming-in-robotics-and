#!/bin/bash
# Compute-node smoke run for the corrected ODYN reproduction.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

echo "=== ODYN small Maros-Meszaros smoke benchmark ==="
python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --rtol 1e-6 \
    --max-iter 250 \
    --timeout 90 \
    --problems HS21 HS35 HS35MOD HS51 HS52 HS53 QAFIRO QADLITTL QPCBLEND QPTEST \
    --output /home/user/tmp/results/odyn_smoke.json

bash scripts/evaluate.sh \
    --results /home/user/tmp/results/odyn_smoke.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
