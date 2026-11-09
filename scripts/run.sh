#!/bin/bash
# Container smoke verification for the packaged ODYN reproduction.
# This job is post-hoc scoring and validation only; it does not rerun the
# already-completed QP benchmark artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$WORKSPACE_DIR"

mkdir -p "$WORKSPACE_DIR/tmp/results" "$WORKSPACE_DIR/scoring"

raw_result() {
    local name="$1"
    if [[ -f "$WORKSPACE_DIR/tmp/results/$name" ]]; then
        printf '%s\n' "$WORKSPACE_DIR/tmp/results/$name"
    else
        printf '%s\n' "$WORKSPACE_DIR/scoring/raw_results/$name"
    fi
}

ODYN_MEDIUM="$(raw_result odyn_full_medium.json)"
ODYN_HIGH="$(raw_result odyn_full_high.json)"
OSQP_MEDIUM="$(raw_result osqp_full_medium.json)"
OSQP_HIGH="$(raw_result osqp_full_high.json)"

for required in "$ODYN_MEDIUM" "$ODYN_HIGH" "$OSQP_MEDIUM" "$OSQP_HIGH"; do
    if [[ ! -f "$required" ]]; then
        echo "Missing raw benchmark result: $required" >&2
        echo "Run scripts/reproduce.sh to regenerate full raw artifacts." >&2
        exit 1
    fi
done

python3 -m method.run_odyn \
    --degenerate-only \
    --rtol 1e-6 \
    --max-iter 300 \
    --timeout 30 \
    --output "$WORKSPACE_DIR/tmp/results/odyn_smoke_current.json"

python3 -m eval.benchmark \
    --results "$WORKSPACE_DIR/tmp/results/odyn_smoke_current.json" \
    --output "$WORKSPACE_DIR/tmp/scores_smoke_current.json"

python3 - <<'PY'
import numpy as np
import scipy.sparse as spa

from method.odyn_solver import OdynParams, SparseOdynSolver

params = OdynParams()
params.max_iter = 100
solver = SparseOdynSolver(params)
result = solver.solve(
    spa.csc_matrix([[2.0, 0.5], [0.5, 1.0]]),
    np.array([-1.0, -0.5]),
    None,
    None,
    spa.csc_matrix([[-1.0, 0.0], [0.0, -1.0], [1.0, 1.0]]),
    np.array([0.0, 0.0, 2.0]),
    rtol=1e-6,
)
if not result.success:
    raise SystemExit(f"sparse ODYN smoke failed: {result.status}")
print(f"sparse ODYN smoke: {result.status} in {result.iterations} iterations")
PY

bash scripts/evaluate_train.sh \
    --results \
        "$ODYN_MEDIUM" \
        "$ODYN_HIGH" \
        "$OSQP_MEDIUM" \
        "$OSQP_HIGH"

bash scripts/evaluate_test.sh \
    --results \
        "$ODYN_MEDIUM" \
        "$ODYN_HIGH" \
        "$OSQP_MEDIUM" \
        "$OSQP_HIGH"

bash scripts/evaluate.sh \
    --results \
        "$ODYN_MEDIUM" \
        "$ODYN_HIGH" \
        "$OSQP_MEDIUM" \
        "$OSQP_HIGH" \
    --output "$WORKSPACE_DIR/scoring/scores.json"

python3 validate.py --compare
