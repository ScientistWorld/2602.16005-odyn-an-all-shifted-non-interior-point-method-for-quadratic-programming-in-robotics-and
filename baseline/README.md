# Baseline

The comparison baseline (OSQP with fixed settings) is owned by the evaluator so
it cannot drift between attempts: see `eval/train/osqp_solver.py` (train and
paper-level scores) and the held-out evaluator's own copy. It is run through the
same solver contract and verification as every registered method and appears
as `osqp` in every scores file. `scripts/baseline.sh` scores it alone on the
train slice.
