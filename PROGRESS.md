# Progress

## What Works

- **ODYN solver implementation**: Python implementation of the all-shifted NIPM QP solver based on the paper's mathematical description. Implements dense and sparse backends with condensed KKT system, Cholesky factorization, adaptive centering, and line search.
- **Maros-Meszárós test set**: 138 QP problems cloned from GitHub, stored as .mat files. Evaluation loader parses them into QP format with sparse matrix support.
- **Baseline solvers**: PROXQP (via proxsuite) integrated but has compatibility issues with the Maros-Meszárós problem format (init() argument type errors).
- **Degenerate test cases**: Three specific degenerate QP problems (redundant constraints, LICQ failure, multiple solutions) implemented.
- **Evaluation pipeline**: eval/benchmark.py runs solvers on test set, computes failure rates, handles timeouts, skips OOM-prone problems.

## Results

| Metric | ODYN (reproduced) | ODYN (paper) | Baseline |
|--------|-------------------|--------------|----------|
| Failure rate (medium) | ~25% (pending full run) | 9.7% | PROXQP 33.0% |
| WCR (δ=1e-2) | TBD | 0.52 | PROXQP 0.75 |
| Degenerate: redundant | 7 it | 5 iter | PROXQP 12 |
| Degenerate: LICQ | 200 it (timeout) | 10 iter | PROXQP 30 |
| Degenerate: multi-sol | 200 it (timeout) | 6 iter | PROXQP 10 |

## Remaining

- **Run full benchmark** to completion — currently running
- **Improve ODYN convergence** on hard problems (AUG3D, LISWET, etc.)
- **Fix eigenvalue errors** on DUALC and HS76 problems
- **Compute failure rates** and compare against paper
- **Evaluate warm-start performance**
- **Fix PROXQP integration** for proper baseline comparison

## Issues

- **High failure rate**: ODYN fails ~25% vs paper's 9.7% — solver needs tuning/improvement
- **PROXQP incompatibility**: Maros-Meszárós problem format uses general constraints with bounds; PROXQP init() rejects the argument types
- **Memory limits**: 8 problems skipped due to dense conversion >5GB
- **Slow convergence**: Some problems need 500+ iterations (paper's C++ is much faster)

## Deviations from Paper

1. **ODYN implementation**: Paper releases C++ with EIGEN. Implemented from scratch in Python. Core computation matches.
2. **Baseline**: Paper compares vs MOSEK/GUROBI/PIQP. Compare vs PROXQP (compatibility issues).
3. **Warm-start**: Not yet evaluated.
4. **Problem formulation**: Maros-Meszárós uses general constraints. My loader converts to standard form with slack variables.
