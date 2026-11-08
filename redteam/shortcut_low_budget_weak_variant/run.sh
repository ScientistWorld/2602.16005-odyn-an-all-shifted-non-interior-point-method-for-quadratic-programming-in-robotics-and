#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
python3 redteam/harness.py --case shortcut_low_budget_weak_variant
