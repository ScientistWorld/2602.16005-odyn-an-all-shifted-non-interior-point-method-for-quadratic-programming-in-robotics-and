#!/bin/bash
# Evaluation script — the standard way to evaluate QP solver performance.
#
# This script runs ODYN and baseline solvers on the Maros-Meszárós test set
# and computes failure rates and performance metrics.
#
# Usage:
#   ./evaluate.sh                      # evaluate all solvers on all problems
#   ./evaluate.sh --max-problems 20    # quick test on 20 problems
#   ./evaluate.sh --solvers odyn proxqp osqp

set -e

cd /home/user

mkdir -p scoring

# Parse arguments
MAX_PROBLEMS=""
SOLVERS="odyn proxqp osqp"
RTOL="1e-6"

while [[ $# -gt 0 ]]; do
    case $1 in
        --max-problems)
            MAX_PROBLEMS="--max-problems $2"
            shift 2
            ;;
        --solvers)
            SOLVERS="$2"
            shift 2
            ;;
        --rtol)
            RTOL="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

python3 -m eval.benchmark \
    --data-dir /home/user/method/maros_meszaros_qpbenchmark/data \
    --solvers $SOLVERS \
    --rtol $RTOL \
    $MAX_PROBLEMS \
    --output /home/user/scoring/scores.json