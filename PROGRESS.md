# Progress

## What Works

- Implemented the ODYN all-shifted non-interior-point QP solver in `method/odyn_solver.py`.
- Added a method runner that writes raw, method-agnostic JSON results from ODYN.
- Moved the Maros-Meszaros benchmark files and loader into `data/`, including conversion of row bounds and variable bounds into standard-form equality and inequality constraints.
- Reworked `eval/benchmark.py` so evaluation only scores raw result files and no longer imports `method/`.
- Added an OSQP baseline runner for optional baseline checks when the package is installed.
- Replaced placeholder scoring docs with concrete target, constraint, direction, and experiment descriptions.

## Results Achieved

The corrected CPU smoke run completed successfully. ODYN now solves all three degenerate QP cases used in the paper's Table IV, with iteration counts close to or better than the reported ODYN counts. The Maros-Meszaros portion of that smoke run was not counted because the first alphabetical instances were all skipped by the dense-memory guard rather than actually attempted.

Current scores from the completed smoke run:

| Experiment | Metric | Reproduced | Paper |
| --- | --- | ---: | ---: |
| degenerate_problems | redundant_ineq | 6 | 5 |
| degenerate_problems | licq_failure | 3 | 10 |
| degenerate_problems | multiple_solutions | 9 | 6 |

## What Remains

- Run an actual small Maros-Meszaros subset that is not skipped by the memory guard.
- If the small subset succeeds, scale to a broader dense subset before attempting the full 138-problem benchmark.
- Re-run high-accuracy failure-rate scoring after the medium-accuracy path is stable.
- Add warm-start scoring only if numeric paper targets can be extracted without inventing values.

## Issues Encountered

- The prior evaluator violated the separation rule by importing `method/` directly.
- The old QP loader mishandled infinity markers and omitted variable bounds from ODYN's constraints.
- The ODYN implementation had sign and shift mistakes in slack initialization and the condensed inequality equations.
- The markdown version of one degenerate case appears OCR-ambiguous; the implemented data case is documented in `data/qplib.py`.
- The first smoke job selected large alphabetical Maros instances, so the evaluator now excludes explicitly unattempted memory skips from failure-rate scoring.

## Deviations From Paper

1. The paper uses a C++ Eigen implementation. This reproduction implements the same ODYN computational steps in Python with NumPy/SciPy.
2. The current benchmark submission starts with a CPU smoke subset before running all 138 Maros-Meszaros problems.
3. Commercial baselines from the paper are recorded in `scoring/reference.json` but not re-run locally.
