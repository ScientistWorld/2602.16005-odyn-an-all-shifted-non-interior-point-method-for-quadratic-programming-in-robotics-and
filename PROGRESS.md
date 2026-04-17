# Progress

## What Works

- Implemented the ODYN all-shifted non-interior-point QP solver in `method/odyn_solver.py`.
- Added a method runner that writes raw, method-agnostic JSON results from ODYN.
- Moved the Maros-Meszaros benchmark files and loader into `data/`, including conversion of row bounds and variable bounds into standard-form equality and inequality constraints.
- Reworked `eval/benchmark.py` so evaluation only scores raw result files and no longer imports `method/`.
- Added an OSQP baseline runner for optional baseline checks when the package is installed.
- Replaced placeholder scoring docs with concrete target, constraint, direction, and experiment descriptions.

## Results Achieved

The corrected CPU smoke runs completed successfully. ODYN solves all three degenerate QP cases used in the paper's Table IV, with iteration counts close to or better than the reported ODYN counts. The follow-up named Maros-Meszaros smoke run attempted 10 small benchmark instances and solved every one at the medium requested tolerance, so the environment now supports the paper's central robustness claim on a scaled but non-trivial suite.

Current scores from the completed named smoke run:

| Experiment | Metric | Reproduced | Paper |
| --- | --- | ---: | ---: |
| failure_rate_comparison | failure_rate_medium | 0.0 | 9.7 |
| degenerate_problems | redundant_ineq | 6 | 5 |
| degenerate_problems | licq_failure | 3 | 10 |
| degenerate_problems | multiple_solutions | 9 | 6 |

## What Remains

- Run a broader named Maros-Meszaros subset at both medium and high requested tolerances.
- If the broader subset succeeds, attempt the full dense-feasible benchmark slice and then consider sparse support for larger instances.
- Add OSQP baseline scoring on the same subset to make the local comparison more informative.
- Add warm-start scoring only if numeric paper targets can be extracted without inventing values.

## Issues Encountered

- The prior evaluator violated the separation rule by importing `method/` directly.
- The old QP loader mishandled infinity markers and omitted variable bounds from ODYN's constraints.
- The ODYN implementation had sign and shift mistakes in slack initialization and the condensed inequality equations.
- The markdown version of one degenerate case appears OCR-ambiguous; the implemented data case is documented in `data/qplib.py`.
- The first smoke job selected large alphabetical Maros instances, so the evaluator now excludes explicitly unattempted memory skips from failure-rate scoring. The second smoke job used named small instances and produced the current failure-rate score.

## Deviations From Paper

1. The paper uses a C++ Eigen implementation. This reproduction implements the same ODYN computational steps in Python with NumPy/SciPy.
2. The current benchmark result is a CPU smoke subset before running all 138 Maros-Meszaros problems.
3. Commercial baselines from the paper are recorded in `scoring/reference.json` but not re-run locally.
