#!/bin/bash
# Full benchmark run on all 138 Maros-Meszaros problems

set -e

cd /home/user

echo "=== Running full ODYN benchmark on all 138 Maros-Meszaros problems ==="

PYTHONPATH=/home/user/pypkgs/cmeel.prefix/lib/python3.12/site-packages:/home/user/pypkgs python3 -m eval.benchmark \
    --data-dir /home/user/method/maros_meszaros_qpbenchmark/data \
    --solvers odyn \
    --rtol 1e-6 \
    --output /home/user/scoring/scores.json

echo ""
echo "Benchmark complete. Results:"
python3 -c "
import json
with open('/home/user/scoring/scores.json') as f:
    data = json.load(f)
print(json.dumps(data, indent=2))
"