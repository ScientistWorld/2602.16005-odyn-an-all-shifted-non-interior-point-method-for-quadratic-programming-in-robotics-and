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

The broader subset run attempted 29 dense-feasible Maros-Meszaros problems at both medium and high requested tolerances. After adding safer condensed-system factorization retries, ODYN solved 24 of 29 at medium tolerance and 23 of 29 at high tolerance. The current failure rates are 17.2% and 20.7%, respectively. This is still worse than the paper's reported ODYN result, but it is substantially better than OSQP on the same local subset.

Current scores from the completed broader subset run:

| Experiment | Metric | Reproduced | Paper |
| --- | --- | ---: | ---: |
| failure_rate_comparison | failure_rate_medium | 17.2 | 9.7 |
| failure_rate_comparison | failure_rate_high | 20.7 | 15.5 |
| failure_rate_comparison/osqp | failure_rate_medium | 41.4 | 44.7 |
| failure_rate_comparison/osqp | failure_rate_high | 41.4 | 49.5 |
| degenerate_problems | redundant_ineq | 6 | 5 |
| degenerate_problems | licq_failure | 3 | 10 |
| degenerate_problems | multiple_solutions | 9 | 6 |
| degenerate_problems/osqp | redundant_ineq | 75 | 75 |
| degenerate_problems/osqp | licq_failure | 50 | 200 |
| degenerate_problems/osqp | multiple_solutions | 75 | 200 |

## What Remains

- Run one final high-iteration broad-subset pass now that the remaining ODYN failures are max-iteration cases rather than numerical errors.
- Investigate persistent max-iteration failures on QFORPLAN, QISRAEL, QRECIPE, QSCAGR7, and QSHARE1B if the high-iteration pass does not reduce failures.
- Attempt the full 138-problem benchmark only after the broad subset stabilizes further or sparse support is improved.
- Add warm-start scoring only if numeric paper targets can be extracted without inventing values.

## Issues Encountered

- The prior evaluator violated the separation rule by importing `method/` directly.
- The old QP loader mishandled infinity markers and omitted variable bounds from ODYN's constraints.
- The ODYN implementation had sign and shift mistakes in slack initialization and the condensed inequality equations.
- The markdown version of one degenerate case appears OCR-ambiguous; the implemented data case is documented in `data/qplib.py`.
- The first smoke job selected large alphabetical Maros instances, so the evaluator now excludes explicitly unattempted memory skips from failure-rate scoring. The second smoke job used named small instances and produced the current failure-rate score.
- The broader subset exposes remaining numerical stability issues on several medium-sized QPs; these are now documented as the main path to higher milestones.
- On the same broad subset, OSQP failed 12 of 29 attempted cases at both tolerances, while ODYN failed 9 of 29. This local comparison supports the reproduced robustness advantage despite the gap to the paper's full ODYN failure rate.
- The factorization-stabilized ODYN rerun removed the numerical-error failures and reduced ODYN failures to 5 of 29 at medium tolerance and 6 of 29 at high tolerance.

## Deviations From Paper

1. The paper uses a C++ Eigen implementation. This reproduction implements the same ODYN computational steps in Python with NumPy/SciPy.
2. The current benchmark result is a CPU smoke subset before running all 138 Maros-Meszaros problems.
3. Commercial baselines from the paper are recorded in `scoring/reference.json` but not re-run locally.
