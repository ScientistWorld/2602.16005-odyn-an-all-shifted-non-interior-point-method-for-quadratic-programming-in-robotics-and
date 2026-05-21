#!/bin/bash
# Optional baseline entry point. The core reproduction focuses on ODYN; this
# script runs the OSQP baseline when the package is available in the container.

set -euo pipefail

cd /home/user
mkdir -p tmp/results scoring

python3 -m baseline.run_osqp \
    --data-dir /home/user/data/maros_meszaros_qpbenchmark/data \
    --resume \
    --output /home/user/tmp/results/osqp_results.json \
    "$@"

bash scripts/evaluate.sh \
    --results /home/user/tmp/results/osqp_results.json \
    --output /home/user/scoring/scores.json
