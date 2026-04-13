# Evaluation

How success is measured. Describe only the metrics, targets, and evaluation procedure.

## Metrics

1. **Failure Rate (%)**: Percentage of problems that fail to converge within 120 seconds or encounter errors. Lower is better.
2. **Performance Profile**: Fraction of problems solved as a function of the performance ratio τ = t_p,s / min_s(t_p,s). Higher is better (closer to 1.0 at lower τ).
3. **Warm-to-Cold Ratio (WCR)**: N_warm / N_cold — ratio of iterations with warm start vs cold start on perturbed problems. Lower is better.
4. **Iteration Count**: Number of solver iterations to convergence. Fewer is better.
5. **Solve Time**: Wall-clock time to convergence. Lower is better.

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

Target: ODYN should achieve failure rate ≤ 15% at medium accuracy (1e-6) on the full Maros-Meszárós test set (138 problems).

## Evaluation Protocol

1. **Benchmark**: Run each solver on all 138 problems from the Maros-Meszárós test set at both accuracy levels, with 120-second timeout.
2. **Performance Profiles**: Compute profiles based on iteration count and solve time.
3. **Warm-starting**: Create perturbed QP problems with perturbation levels δ ∈ {1e-3, 1e-2, 1e-1} and measure iteration reduction.
4. **Degenerate Cases**: Run specific test cases (redundant constraints, LICQ failure, multiple solutions).
5. **Dense Backend**: Benchmark per-iteration time on random QPs with n ∈ {1, 50, 100, 200, 400}.