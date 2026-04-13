#!/bin/bash
# Quick test run on a subset of problems to verify the pipeline works.

set -e

cd /home/user

echo "Quick test: running ODYN on 5 Maros-Meszárós problems..."
python3 -m eval.benchmark \
    --data-dir /home/user/method/maros_meszaros_qpbenchmark/data \
    --solvers odyn \
    --rtol 1e-6 \
    --max-problems 5 \
    --output /home/user/scoring/scores.json

echo ""
echo "Quick test complete. Check scoring/scores.json for results."