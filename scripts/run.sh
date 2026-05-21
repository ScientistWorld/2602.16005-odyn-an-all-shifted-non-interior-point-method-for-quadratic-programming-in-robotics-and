#!/bin/bash
# Containerized smoke validation for the ODYN update-rule patch.
#
# The full benchmark protocol still lives in scripts/reproduce.sh. This
# scheduler check verifies that the paper-directed solver changes run inside the
# packaged environment, regenerates scoring/scores.json from the completed full
# benchmark outputs, and avoids overwriting those heavier raw result files.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

python3 -m method.run_odyn \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --problems QPTEST \
    --rtol 1e-6 \
    --max-iter 300 \
    --timeout 60 \
    --output /home/user/tmp/results/update_rule_smoke_odyn.json

bash scripts/evaluate.sh \
    --results \
        /home/user/tmp/results/odyn_full_medium.json \
        /home/user/tmp/results/odyn_full_high.json \
        /home/user/tmp/results/osqp_full_medium.json \
        /home/user/tmp/results/osqp_full_high.json \
    --output /home/user/scoring/scores.json

python3 validate.py --compare
