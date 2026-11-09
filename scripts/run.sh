#!/bin/bash
# Job entry point. This job runs the hardening audit, which also regenerates the
# reference scores (scores_test / scores / scores_train) from the final code.
# The plain end-to-end reproduction is scripts/reproduce.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
bash scripts/hardening/run_audit.sh
