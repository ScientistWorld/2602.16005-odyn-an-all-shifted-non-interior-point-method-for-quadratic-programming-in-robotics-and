# Evaluation Targets

## failure_rate_comparison
Tests whether a QP solver reliably solves the Maros-Meszaros benchmark under the paper's requested accuracy settings.
- **Metric**: `failure_rate_medium` (lower is better)
- **Constraint metrics**: `failure_rate_high` (lower is better) and `attempted_count` (higher is better, to expose reduced benchmark coverage)
- **How to run**: produce a raw solver result JSON, then run `bash scripts/evaluate.sh --results <raw.json>`.

## degenerate_problems
Tests whether a QP solver remains reliable on small pathological problems with redundant active constraints, violated constraint qualifications, and non-unique solutions.
- **Metric**: `redundant_ineq` iteration count (lower is better)
- **Constraint metrics**: `licq_failure` and `multiple_solutions` iteration counts (lower is better)
- The paper's OSQP value for `licq_failure` is non-numeric (`†`, meaning "declared dual infeasible"), and the markdown OCR for that test case is ambiguous, so `licq_failure` is kept as a diagnostic constraint rather than the scored primary metric.
- **How to run**: produce a raw solver result JSON including the degenerate cases, then run `bash scripts/evaluate.sh --results <raw.json>`.
