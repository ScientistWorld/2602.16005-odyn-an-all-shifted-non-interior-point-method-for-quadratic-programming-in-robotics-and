# Evaluation Targets

## failure_rate_comparison
Tests whether a QP solver reliably solves the Maros-Meszaros benchmark under the paper's requested accuracy settings.
- **Metric**: `failure_rate_medium` (lower is better)
- **Constraint metric**: `failure_rate_high` (lower is better)
- **How to run**: produce a raw solver result JSON, then run `bash scripts/evaluate.sh --results <raw.json>`.

## degenerate_problems
Tests whether a QP solver remains reliable on small pathological problems with redundant active constraints, violated constraint qualifications, and non-unique solutions.
- **Metric**: `licq_failure` iteration count (lower is better)
- **Constraint metrics**: `redundant_ineq` and `multiple_solutions` iteration counts (lower is better)
- **How to run**: produce a raw solver result JSON including the degenerate cases, then run `bash scripts/evaluate.sh --results <raw.json>`.

