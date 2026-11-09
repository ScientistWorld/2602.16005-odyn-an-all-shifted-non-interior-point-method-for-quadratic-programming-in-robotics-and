#!/bin/bash
# Job entry point: reproduce the packaged reference scores end to end.
#
# The solvers need no training. Each evaluator runs every registered solver
# (scripts/solvers/*.sh; the reference is scripts/solvers/odyn.sh) and the
# evaluator-owned OSQP baseline on its own instances and verifies the returned
# points: scoring/scores.json, scoring/scores_train.json, scoring/scores_test.json.
# The variant/shortcut audit behind HARDENING.md is scripts/hardening/run_audit.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
bash scripts/reproduce.sh
