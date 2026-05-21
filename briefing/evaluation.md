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

## Baselines and Targets

| Solver | Failure Rate (Medium) | Failure Rate (High) | Warm-start | Backend |
|--------|----------------------|---------------------|------------|---------|
| ODYN (proposed) | 9.7% | 15.5% | ✓ | Dense/Sparse |
| PROXQP (ALM) | 33.0% | 35.9% | ✓ | Dense/Sparse |
| OSQP (ADMM) | 44.7% | 49.5% | ✓ | Sparse |
| PIQP (IPM) | 10.7% | 10.7% | ✗ | Sparse |
| MOSEK (IPM) | 14.6% | 14.6% | ✗ | Dense/Sparse |
| GUROBI (IPM) | 9.7% | 12.6% | ✗ | Dense/Sparse |

Target: a successful reproduced solver should achieve low medium-accuracy failure rate while preserving high-accuracy robustness and benchmark coverage.

## Evaluation Protocol

1. **Benchmark**: run each solver on the Maros-Meszaros QP test set at both requested accuracy levels.
2. **Failure Rules**: count solver errors, timeouts, numerical failures, and iteration-limit exits as failures.
3. **Coverage**: report attempted problem count alongside failure rates.
4. **Degenerate Cases**: run the redundant-constraint, LICQ-failure, and multiple-solution QPs and report iteration counts.
5. **Reusable Scoring**: write raw solver result JSON files, then score them with `scripts/evaluate.sh` so evaluation remains independent of any particular solver implementation.
