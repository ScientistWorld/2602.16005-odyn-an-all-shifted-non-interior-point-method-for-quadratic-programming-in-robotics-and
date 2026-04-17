# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-04-12] - none
- Read paper thoroughly: ODYN is an all-shifted non-interior-point QP solver
- Key results: 9.7% failure rate on Maros-Meszárós (best among open-source), superior warm-start, robust on degenerate problems
- Cloned Maros-Meszárós QP benchmark repo to `/home/user/method/maros_meszaros_qpbenchmark/` (138 .mat files)
- Installed available QP solvers: proxsuite (PROXQP), osqp packages
- Created all briefing files (overview.md, problem.md, method.md, evaluation.md)
- Created scoring/reference.json with paper's reported numbers
- Implemented ODYN solver from scratch in Python based on paper's algorithm description
- Created eval/benchmark.py for evaluation

### [2026-04-14] - method_runs
- Fixed multiple bugs in ODYN solver (SyntaxError, NaN handling, scipy.linalg.solve_triangular import)
- Fixed .mat file loading (sparse matrix conversion, infinity marker comparison)
- Fixed PROXQP integration (positional arguments, l/u bounds)
- ODYN successfully solves simple QP problems: unconstrained (2 iter), equality (2 iter), inequality (7 iter)
- Added memory guard to skip very large problems (>5GB dense)
- Added sparse matrix support to avoid OOM on large problems

### [2026-04-14] - core_claim
- ODYN solver runs on full Maros-Meszárós test set (138 problems)
- Fixed empty array norm guards, eigenvalue PD checks, NCP overflow clipping
- Preliminary results: ODYN solves ~75% of problems within 200 iterations
- PROXQP baseline has init compatibility issues on Maros-Meszárós problem format
- Full benchmark running to completion — results pending
