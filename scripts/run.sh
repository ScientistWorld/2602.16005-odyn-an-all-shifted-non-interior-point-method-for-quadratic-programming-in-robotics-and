#!/bin/bash
# Hardening verification job.
#
#   S0  environment report + smoke test of the verified evaluation pipeline
#   S1  hidden test (bash scripts/evaluate_test.sh, no arguments): reference
#       solver "odyn" + evaluator-owned OSQP baseline -> scoring/scores_test.json
#   S2  paper-level scores on unperturbed problems  -> scoring/scores.json
#   S3  better/weaker variants and shortcut probes, each in an isolated
#       workspace copy, through the unmodified hidden test
#   S4  train slice                                 -> scoring/scores_train.json
#   S5  analysis (ranks, paired bootstrap, draw noise) + validate.py
#
# QP_GYM_EVAL_CACHE stores raw solver outputs keyed by solver code + instance
# content, so a preempted job resumes and unchanged reference/baseline runs
# are reused by the case workspaces. Scores are always recomputed from the raw
# outputs. The hidden test itself never sets this variable.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$WS"
mkdir -p tmp/hardening/logs
export QP_GYM_EVAL_CACHE="$WS/tmp/eval_cache"
LOGS="$WS/tmp/hardening/logs"

stage() { echo; echo "=================== $* ($(date -u +%H:%M:%S)) ==================="; }

stage "S0 environment"
python3 -c "import sys, numpy, scipy, osqp; print(sys.version); print('numpy', numpy.__version__, 'scipy', scipy.__version__, 'osqp', osqp.__version__)"
echo "nproc=$(nproc) affinity=$(python3 -c 'import os; print(len(os.sched_getaffinity(0)))') cpu.max=$(cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo n/a)"
python3 -c "from eval.train.evaluate import available_cpus; print('evaluator workers:', min(8, available_cpus()))"

stage "S0 smoke"
if ! python3 scripts/hardening/cases.py smoke 2>&1 | tee "$LOGS/smoke.log"; then
    echo "SMOKE TEST FAILED - aborting"
    find /tmp -maxdepth 1 -name 'qp_gym_*' | head
    exit 1
fi
if grep -q "smoke test failed" "$LOGS/smoke.log"; then
    echo "SMOKE TEST FAILED - aborting"; exit 1
fi

stage "S1 hidden test: reference + baseline"
bash scripts/evaluate_test.sh 2>&1 | tee "$LOGS/test_reference.log" | grep -v " OK " | tail -n 400
test -f scoring/scores_test.json || echo "S1 FAILED: no scoring/scores_test.json"

stage "S2 paper-level scores"
bash scripts/evaluate.sh 2>&1 | tee "$LOGS/paper.log" | grep -v " OK " | tail -n 400
test -f scoring/scores.json || echo "S2 FAILED: no scoring/scores.json"

stage "S3 variants and shortcuts through the hidden test"
python3 scripts/hardening/cases.py export 2>&1 | tee "$LOGS/export.log"
python3 scripts/hardening/cases.py run --force 2>&1 | tee "$LOGS/cases.log"

stage "S4 train slice"
bash scripts/evaluate_train.sh 2>&1 | tee "$LOGS/train.log" | grep -v " OK " | tail -n 400
test -f scoring/scores_train.json || echo "S4 FAILED: no scoring/scores_train.json"

stage "S5 analysis and validation"
python3 scripts/hardening/cases.py analyze > "$LOGS/analyze.log" 2>&1; tail -n 60 "$LOGS/analyze.log"
python3 validate.py 2>&1 | tail -n 40

stage "S6 run-to-run noise: uncached rerun of the reference on the hidden test"
mkdir -p notes/hardening tmp/hardening/rerun
cp tmp/eval_runs/test/outcomes.jsonl tmp/hardening/reference_test_outcomes.jsonl
QP_GYM_EVAL_CACHE= python3 -m eval.test.evaluate --solvers odyn --output tmp/hardening/rerun/scores_test.json \
    > "$LOGS/rerun.log" 2>&1
cp tmp/eval_runs/test/outcomes.jsonl tmp/hardening/rerun/outcomes.jsonl
cp tmp/hardening/reference_test_outcomes.jsonl tmp/eval_runs/test/outcomes.jsonl
python3 scripts/hardening_noise.py tmp/hardening/reference_test_outcomes.jsonl \
    tmp/hardening/rerun/outcomes.jsonl notes/hardening/noise.json 2>&1 | tee "$LOGS/noise.log"
for f in smoke export cases analyze noise; do cp "$LOGS/$f.log" notes/hardening/ 2>/dev/null || true; done
stage "done"
