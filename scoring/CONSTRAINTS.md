# Scientist Constraints

## Problem Set
The evaluators build every instance themselves from the pinned Maros-Meszaros files in `data/maros_meszaros_qpbenchmark/data` and their own degenerate-problem generators. Do not edit, replace, or add problem files; altered files abort scoring.

## Problem Form
Solve the instance exactly as given: `minimize 1/2 x'Qx + c'x subject to Ax = b, Gx <= h`. Return a primal-dual point `(x, y, z)` with `Qx + c + A'y + G'z = 0`, `z >= 0`. Dropping or relaxing constraints, or returning points for a different problem, fails verification.

## Accuracy And Failure Rules
The evaluator applies the same tolerances (1e-6, 1e-9) and the same residual test to every solver. Errors, crashes, budget overruns, missing or malformed outputs, and unverified points are failures. Every manifest instance is in the denominator. Self-reported status, iteration counts, or residuals are ignored.

## Solver Resources
Each solve gets 120 CPU-seconds (all threads of the process count) and each solver gets 7200 CPU-seconds per evaluation. Solvers run single-process on CPU with the evaluator's environment. Do not spawn detached processes to escape the budget.

## Result Contract
Register the solver as an executable `scripts/solvers/<name>.sh` implementing `--problem IN.npz --output OUT.npz --tol TOL` (see `briefing/evaluation.md`). Scores come only from `scripts/evaluate_{train,test}.sh` and `scripts/evaluate.sh`; the evaluators must remain method-agnostic and must not import `method/`.

## Compliance Checklist
- [ ] Problem files are unchanged (SHA-256 checks pass)
- [ ] The solver solves the instance it is given, and does not recognize instances or look up stored solutions
- [ ] No commercial or third-party QP solver is called in place of the method being developed
- [ ] Scores are produced by the evaluation scripts
- [ ] `eval/` does not import the submitted method
