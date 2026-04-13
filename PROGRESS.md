# Progress

## What Works

- **ODYN solver implementation**: Python implementation of the all-shifted NIPM QP solver based on the paper's mathematical description. Implements dense and sparse backends with condensed KKT system, Cholesky factorization, adaptive centering, and line search.
- **Maros-Meszárós test set**: 138 QP problems cloned from GitHub, stored as .mat files. Evaluation loader parses them into QP format.
- **Baseline solvers**: PROXQP (via proxsuite) integrated in eval/benchmark.py. OSQP integration attempted but has import issues.
- **Degenerate test cases**: Three specific degenerate QP problems from the paper (redundant constraints, LICQ failure, multiple solutions) implemented for evaluation.
- **Evaluation pipeline**: eval/benchmark.py runs solvers on test set, computes failure rates, handles timeouts.

## Results

| Metric | ODYN (reproduced) | ODYN (paper) | Baseline |
|--------|-------------------|--------------|----------|
| Failure rate (medium) | TBD | 9.7% | PROXQP 33.0% |
| WCR (δ=1e-2) | TBD | 0.52 | PROXQP 0.75 |
| Degenerate: redundant | TBD | 5 iter | PROXQP 12 |
| Degenerate: LICQ | TBD | 10 iter | PROXQP 30 |

Awaiting first test run to get reproduced numbers.

## Remaining

- **Test and debug ODYN solver** on simple problems to verify correctness
- **Run full benchmark** on all 138 problems across solvers
- **Compute failure rates** and compare against paper
- **Evaluate warm-start performance**
- **Validate on degenerate problems**
- **Iterate on solver implementation** based on results

## Issues

- **Bash execution blocked** (exit code 126) in this session — cannot test code locally
- **OSQP unavailable** due to disk space constraints (Jinja2 bytecode cache fills /tmp)
- **ODYN repo not accessible**: No GitHub URL found in paper, multiple URL patterns tried (404s), PyPI package doesn't exist
- **Disk space pressure**: 16TB free of 250T (94% used), which affects OSQP installation

## Deviations from Paper

1. **ODYN implementation**: The paper releases ODYN as C++ with Python bindings. I implemented the same algorithm from scratch in Python. The core computation (condensed KKT, all-shifted NCP, proximal regularization) matches the paper's description.

2. **Baseline selection**: Paper compares against MOSEK and GUROBI (commercial, not available) and PIQP (not on PyPI). I compare against PROXQP (proxsuite available) and OSQP (when disk space allows).

3. **Solver precision**: Paper uses double precision by default. My implementation uses double precision with tolerance 1e-9 for high-accuracy experiments.

4. **Warm-start evaluation**: Paper perturbs QP problems at δ ∈ {1e-3, 1e-2, 1e-1}. My warm-start test follows the same protocol.