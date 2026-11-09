#!/bin/bash
# Submit this script as its own job after all candidate-generation jobs exit.
# This job runs only the restored hidden scorer and lightweight JSON checks.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
for candidate_run in "$ROOT_DIR"/redteam/*/run.sh; do
    case_dir="$(dirname "$candidate_run")"
    echo "FRESH TEST $(basename "$case_dir")"
    (
        cd "$case_dir/workspace"
        bash scripts/evaluate_test.sh
    ) > "$case_dir/artifacts/fresh_test.log" 2>&1
    cp "$case_dir/workspace/scoring/scores_test.json" "$case_dir/scores_test_fresh_job.json"
    cmp "$case_dir/scores_test.json" "$case_dir/scores_test_fresh_job.json"
done
python3 redteam/report.py
python3 redteam/finalize_evidence.py
python3 redteam/verify_fresh_job.py
