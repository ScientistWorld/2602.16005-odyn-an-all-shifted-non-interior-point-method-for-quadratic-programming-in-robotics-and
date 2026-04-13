#!/bin/bash
# Run ODYN QP solver and evaluate on the benchmark.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

echo "Running ODYN solver benchmark..."
bash scripts/evaluate.sh --solvers odyn --rtol 1e-6