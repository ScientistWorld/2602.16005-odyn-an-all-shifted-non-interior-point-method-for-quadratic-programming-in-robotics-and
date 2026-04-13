#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This runs ODYN vs PROXQP vs OSQP on the Maros-Meszárós test set
# and computes failure rates and degenerate problem performance.

set -e

cd /home/user

echo "=== ODYN QP Solver Reproduction ==="
echo "Benchmark: Maros-Meszárós test set"
echo ""

# Run full benchmark
echo "[1/3] Running benchmark on all solvers..."
bash scripts/evaluate.sh --solvers odyn proxqp osqp --rtol 1e-6

echo ""
echo "[2/3] Running high-accuracy benchmark..."
bash scripts/evaluate.sh --solvers odyn proxqp osqp --rtol 1e-9 --max-problems 50

echo ""
echo "[3/3] Computing warm-to-cold ratio..."
# Warm-start evaluation is handled by the benchmark script

echo ""
echo "=== Results Summary ==="
if [ -f scoring/scores.json ]; then
    python3 -c "
import json
with open('/home/user/scoring/scores.json') as f:
    data = json.load(f)
print(json.dumps(data, indent=2))
"
fi