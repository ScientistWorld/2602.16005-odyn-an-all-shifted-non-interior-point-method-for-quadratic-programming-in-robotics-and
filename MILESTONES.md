# Reproduction Milestones

**Current: none**

## Progress Log

### [2026-04-12] - none
- Read paper thoroughly: ODYN is an all-shifted non-interior-point QP solver
- Key results: 9.7% failure rate on Maros-Meszárós (best among open-source), superior warm-start, robust on degenerate problems
- Could not clone ODYN repository (GitHub not accessible from this environment, no direct URL in paper)
- Cloned Maros-Meszárós QP benchmark repo to `/home/user/method/maros_meszaros_qpbenchmark/` (138 .mat files)
- Installed available QP solvers: proxsuite (PROXQP), osqp packages
- Created all briefing files (overview.md, problem.md, method.md, evaluation.md)
- Created scoring/reference.json with paper's reported numbers
- Implemented ODYN solver from scratch in Python based on paper's algorithm description
- Created eval/benchmark.py for evaluation
- Updated all scripts (evaluate.sh, method.sh, reproduce.sh, run.sh)
- Updated container.def and setup.sh

## Stop Justification
- Completed at milestone `method_runs`.
