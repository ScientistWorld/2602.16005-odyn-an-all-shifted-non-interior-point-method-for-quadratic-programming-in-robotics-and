#!/bin/bash
# Registered solver "odyn": the reproduced reference method.
#
# Every executable scripts/solvers/<name>.sh is scored by scripts/evaluate_*.sh
# under the name <name>. Contract (see briefing/evaluation.md):
#   <script> --problem INSTANCE.npz --output SOLUTION.npz --tol TOL
set -euo pipefail
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$WORKSPACE_DIR"
exec python3 -m method.solve_cli "$@"
