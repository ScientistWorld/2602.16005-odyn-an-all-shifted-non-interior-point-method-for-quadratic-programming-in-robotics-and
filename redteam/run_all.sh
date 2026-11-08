#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# Each subprocess exits before the hidden scorer starts. Cases are sequential.
for case in \
  packaged_reference reference_seed_0 shortcut_low_budget_weak_variant \
  shortcut_success_flags shortcut_visible_cache shortcut_hide_failures \
  shortcut_negative_cap shortcut_zero_cap_all_fail shortcut_ignore_degenerate \
  shortcut_replace_problem_loader shortcut_move_baseline shortcut_write_scores_only \
  stronger_regularization stronger_more_iterations reference_seed_1 reference_seed_2; do
  bash "redteam/$case/run.sh"
done
python3 redteam/report.py
