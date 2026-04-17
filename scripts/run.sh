#!/bin/bash
# Final packaging and scoring validation for the ODYN reproduction.
#
# The full benchmark protocol lives in scripts/reproduce.sh. This scheduler
# check verifies the reusable scripts, regenerates scoring/scores.json from the
# completed raw full-benchmark outputs, and runs a tiny ODYN smoke solve without
# overwriting the full benchmark scores.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --problems QPTEST \
    --rtol 1e-6 \
    --max-iter 300 \
    --timeout 60 \
    --output /home/user/tmp/results/package_smoke_odyn.json

bash scripts/evaluate.sh \
    --results \
        /home/user/tmp/results/odyn_full_medium.json \
        /home/user/tmp/results/odyn_full_high.json \
        /home/user/tmp/results/osqp_full_medium.json \
        /home/user/tmp/results/osqp_full_high.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
