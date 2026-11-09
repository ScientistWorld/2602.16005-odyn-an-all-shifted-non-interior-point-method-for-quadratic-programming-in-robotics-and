# Evaluation Targets

## failure_rate_comparison
Tests whether a QP solver reliably solves Maros-Meszaros problems at the paper's two requested accuracies.
- **Metric**: `failure_rate_medium` (lower is better): % of instances without a verified 1e-6 solution
- **Constraint metric**: `failure_rate_high` (lower is better): % of instances without a verified 1e-9 solution
- Coverage is part of the metric: the denominator is the fixed manifest, so skipping an instance is a failure.
- **How to run**: register the solver as `scripts/solvers/<name>.sh` (contract in `briefing/evaluation.md`), then `bash scripts/evaluate_train.sh` (train) or `bash scripts/evaluate.sh` (published problems).

## degenerate_problems
Tests whether a QP solver remains reliable on degenerate problems (redundant active inequalities, LICQ failure, non-unique solutions).
- **Metric**: `degenerate_failure_rate_high` (lower is better): degeneracy mainly separates solvers at 1e-9
- **Constraint metric**: `degenerate_failure_rate_medium` (lower is better)
- The paper reports iteration counts on three small examples; iteration counts are not scored because they cannot be verified. The paper's three examples are part of the train slice and the paper-level scores.
- **How to run**: same as above; the degenerate instances are part of every evaluation.
