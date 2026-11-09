#!/bin/bash
# Paper-level reproduction scores: every registered solver plus the OSQP
# baseline on the original (unperturbed) tractable Maros-Meszaros problems and
# the paper's three degenerate QPs; writes scoring/scores.json.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WORKSPACE_DIR"
python3 -m eval.benchmark "$@"
