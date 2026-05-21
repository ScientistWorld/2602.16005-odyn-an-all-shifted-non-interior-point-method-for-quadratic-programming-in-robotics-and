#!/bin/bash
# Populate the visible train and held-out test scores from existing raw solver
# artifacts. This job is post-hoc scoring only; it does not retrain or rerun
# the method.

set -euo pipefail

cd /home/user

bash scripts/evaluate_train.sh \
    --results \
        /home/user/tmp/results/odyn_full_medium.json \
        /home/user/tmp/results/odyn_full_high.json \
        /home/user/tmp/results/osqp_full_medium.json \
        /home/user/tmp/results/osqp_full_high.json

bash scripts/evaluate_test.sh \
    --results \
        /home/user/tmp/results/odyn_full_medium.json \
        /home/user/tmp/results/odyn_full_high.json \
        /home/user/tmp/results/osqp_full_medium.json \
        /home/user/tmp/results/osqp_full_high.json
