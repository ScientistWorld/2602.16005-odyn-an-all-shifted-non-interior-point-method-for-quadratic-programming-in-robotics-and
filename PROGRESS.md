# Progress

## What Works

- Implemented the ODYN all-shifted non-interior-point QP solver in `method/odyn_solver.py`.
- Added a method runner that writes raw, method-agnostic JSON results from ODYN.
- Moved the Maros-Meszaros benchmark files and loader into `data/`, including conversion of row bounds and variable bounds into standard-form equality and inequality constraints.
- Reworked `eval/benchmark.py` so evaluation only scores raw result files and no longer imports `method/`.
- Added an OSQP baseline runner for optional baseline checks when the package is installed.
- Replaced placeholder scoring docs with concrete target, constraint, direction, and experiment descriptions.

## Results Achieved

The previous raw run reached `method_runs`: ODYN executed on benchmark instances and solved some problems, but its preliminary failure rate and degenerate-case behavior did not yet support the paper's central claim. The current submitted job will regenerate `scoring/scores.json` after the corrected solver and evaluator changes.

Current stale scores from the earlier run:

| Experiment | Metric | Reproduced | Paper |
| --- | --- | ---: | ---: |
| failure_rate_comparison | failure_rate_medium | 25.0 | 9.7 |
| degenerate_problems | redundant_ineq | 7 | 5 |
| degenerate_problems | licq_failure | 200 | 10 |
| degenerate_problems | multiple_solutions | 200 | 6 |

## What Remains

- Run the corrected ODYN smoke benchmark in the compute environment.
- If the smoke run succeeds, scale from a small subset to the full Maros-Meszaros benchmark.
- Re-run high-accuracy failure-rate scoring after the medium-accuracy path is stable.
- Add warm-start scoring only if numeric paper targets can be extracted without inventing values.

## Issues Encountered

- The prior evaluator violated the separation rule by importing `method/` directly.
- The old QP loader mishandled infinity markers and omitted variable bounds from ODYN's constraints.
- The ODYN implementation had sign and shift mistakes in slack initialization and the condensed inequality equations.
- The markdown version of one degenerate case appears OCR-ambiguous; the implemented data case is documented in `data/qplib.py`.

## Deviations From Paper

1. The paper uses a C++ Eigen implementation. This reproduction implements the same ODYN computational steps in Python with NumPy/SciPy.
2. The current benchmark submission starts with a CPU smoke subset before running all 138 Maros-Meszaros problems.
3. Commercial baselines from the paper are recorded in `scoring/reference.json` but not re-run locally.

