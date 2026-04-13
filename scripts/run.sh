#!/bin/bash
# Test run — quick verification on a small subset.

set -e

cd /home/user

echo "=== Quick verification on 10 Maros-Meszaros problems ==="

PYTHONPATH=/home/user/pypkgs python3 -m eval.benchmark \
    --data-dir /home/user/method/maros_meszaros_qpbenchmark/data \
    --solvers odyn proxqp \
    --rtol 1e-6 \
    --max-problems 10 \
    --output /home/user/scoring/scores.json

echo ""
echo "Test complete. Results:"
python3 -c "
import json
with open('/home/user/scoring/scores.json') as f:
    data = json.load(f)
print(json.dumps(data, indent=2))
"