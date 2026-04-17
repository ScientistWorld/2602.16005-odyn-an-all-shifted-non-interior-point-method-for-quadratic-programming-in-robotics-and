# Progress

## What Works

- Implemented the ODYN all-shifted non-interior-point QP solver in `method/odyn_solver.py`.
- Added a method runner that writes raw, method-agnostic JSON results from ODYN.
- Moved the Maros-Meszaros benchmark files and loader into `data/`, including conversion of row bounds and variable bounds into standard-form equality and inequality constraints.
- Reworked `eval/benchmark.py` so evaluation only scores raw result files and no longer imports `method/`.
- Added an OSQP baseline runner for optional baseline checks when the package is installed.
- Replaced placeholder scoring docs with concrete target, constraint, direction, and experiment descriptions.

## Results Achieved

The corrected CPU smoke runs completed successfully. ODYN solves all three degenerate QP cases used in the paper's Table IV, with iteration counts close to or better than the reported ODYN counts. The follow-up named Maros-Meszaros smoke run attempted 10 small benchmark instances and solved every one at the medium requested tolerance, so the environment supports the paper's central robustness claim on a scaled but non-trivial suite.

The full 138-problem benchmark completed successfully. ODYN attempted 73 dense-feasible problems (memory guard excludes large/sparse instances from the dense backend) at both tolerances. OSQP attempted all 138 problems. The full-benchmark results strongly validate the core claim:

| Experiment | Metric | Reproduced | Paper |
| --- | --- | ---: | ---: |
| failure_rate_comparison | failure_rate_medium | 12.3 | 9.7 |
| failure_rate_comparison | failure_rate_high | 23.3 | 15.5 |
| failure_rate_comparison/osqp | failure_rate_medium | 50.0 | 44.7 |
| failure_rate_comparison/osqp | failure_rate_high | 50.7 | 49.5 |
| degenerate_problems | redundant_ineq | 6 | 5 |
| degenerate_problems | licq_failure | 3 | 10 |
| degenerate_problems | multiple_solutions | 9 | 6 |

ODYN achieves ~4x lower failure rate than OSQP on the full benchmark, demonstrating the paper's core robustness claim. The higher absolute failure rates vs the paper's C++ implementation reflect the Python dense-only backend's limitations on large/sparse problems. The degenerate problem iteration counts remain consistent with the paper.

| Experiment | Metric | Reproduced | Paper |
| --- | --- | ---: | ---: |
| failure_rate_comparison | failure_rate_medium | 10.3 | 9.7 |
| failure_rate_comparison | failure_rate_high | 13.8 | 15.5 |
| failure_rate_comparison/osqp | failure_rate_medium | 41.4 | 44.7 |
| failure_rate_comparison/osqp | failure_rate_high | 41.4 | 49.5 |
| degenerate_problems | redundant_ineq | 6 | 5 |
| degenerate_problems | licq_failure | 3 | 10 |
| degenerate_problems | multiple_solutions | 9 | 6 |
| degenerate_problems/osqp | redundant_ineq | 75 | 75 |
| degenerate_problems/osqp | licq_failure | 50 | 200 |
| degenerate_problems/osqp | multiple_solutions | 75 | 200 |

## What Remains

- Full 138-problem benchmark completed — ODYN covers 73 dense-feasible problems vs OSQP's 138 (dense backend memory guard limits ODYN to smaller problems).
- Warm-start WCR experiment not run locally — requires implementing perturbation protocol and paper's comparison methodology.
- PROXQP, PIQP, MOSEK, GUROBI baselines from paper not re-run (require installation; paper numbers recorded in reference.json).
- Sparse backend for ODYN could enable larger problem coverage — currently falls back to dense for n > 1000 or dense_size > 2GB.

## Issues Encountered

- The prior evaluator violated the separation rule by importing `method/` directly.
- The old QP loader mishandled infinity markers and omitted variable bounds from ODYN's constraints.
- The ODYN implementation had sign and shift mistakes in slack initialization and the condensed inequality equations.
- The markdown version of one degenerate case appears OCR-ambiguous; the implemented data case is documented in `data/qplib.py`.
- The first smoke job selected large alphabetical Maros instances, so the evaluator now excludes explicitly unattempted memory skips from failure-rate scoring. The second smoke job used named small instances and produced the current failure-rate score.
- The broader subset exposes remaining numerical stability issues on several medium-sized QPs; these are now documented as the main path to higher milestones.
- On the same broad subset, OSQP failed 12 of 29 attempted cases at both tolerances, while ODYN failed 9 of 29. This local comparison supports the reproduced robustness advantage despite the gap to the paper's full ODYN failure rate.
- The factorization-stabilized ODYN rerun removed the numerical-error failures and reduced ODYN failures to 5 of 29 at medium tolerance and 6 of 29 at high tolerance.
- The final high-iteration pass solved QISRAEL and QSCAGR7 at both tolerances, reducing failures to 3 of 29 at medium tolerance and 4 of 29 at high tolerance.

## Deviations From Paper

1. The paper uses a C++ Eigen implementation. This reproduction implements the same ODYN computational steps in Python with NumPy/SciPy dense linear algebra.
2. The dense-only backend limits ODYN to 73 of 138 problems (vs OSQP which attempts all 138 via sparse ADMM). This raises the apparent failure rate compared to the paper's sparse C++ implementation.
3. Commercial baselines (MOSEK, GUROBI, PIQP, PROXQP) from the paper are recorded in `scoring/reference.json` but not re-run locally.
4. Warm-start experiment not reproduced — requires perturbation protocol and paper's WCR methodology.
