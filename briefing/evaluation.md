# Evaluation

This page defines how a candidate QP solver is evaluated. It describes the task and metrics only; solver design choices belong outside the problem definition.

## Metrics

1. **Failure Rate (%)**: Percentage of problems that fail to converge within 120 seconds or encounter errors. Lower is better.
2. **Attempted Count**: Number of benchmark instances actually attempted. Higher is better because reduced coverage must be visible.
3. **Iteration Count**: Number of solver iterations to convergence. Fewer is better.
4. **Degenerate-Case Iterations**: Iteration counts on small pathological QPs with redundant constraints, violated constraint qualifications, and non-unique solutions. Fewer is better.
5. **Warm-to-Cold Ratio (WCR)**: Iterations with a warm start divided by iterations from a cold start on perturbed QP sequences. Lower is better.

The paper also reports wall-clock timing and performance profiles. This gym does not score wall-clock time because hardware varies across runs; it uses failure rates, coverage, and iteration counts as machine-independent quantities.

Accuracy levels: **Medium** = tolerance 1e-6, **High** = tolerance 1e-9.

## Targets

Paper-reported reference values and reproduced scores are stored in `scoring/reference.json` and `scoring/scores.json`. A successful solver should achieve low medium-accuracy failure rate while preserving high-accuracy robustness and benchmark coverage. Methods that skip difficult instances must report reduced `attempted_count`; the evaluator does not treat skipped problems as invisible.

## Evaluation Protocol

1. **Benchmark**: run each solver on the Maros-Meszaros QP test set at both requested accuracy levels.
2. **Failure Rules**: count solver errors, timeouts, numerical failures, and iteration-limit exits as failures.
3. **Coverage**: report attempted problem count alongside failure rates.
4. **Degenerate Cases**: run the redundant-constraint, LICQ-failure, and multiple-solution QPs and report iteration counts.
5. **Reusable Scoring**: write raw solver result JSON files, then score them with `scripts/evaluate.sh` so evaluation remains independent of any particular solver implementation.
