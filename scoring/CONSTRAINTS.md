# Scientist Constraints

## Problem Set
Use the Maros-Meszaros QP instances provided in `data/maros_meszaros_qpbenchmark/data` for the main benchmark. Do not add, remove, rename, or edit problem files when reporting `failure_rate_comparison`.

## Problem Form
Evaluate every solver on the same standard-form convex QPs: quadratic objective, equality constraints, and upper-bound inequalities. Variable bounds from the benchmark files must be converted into explicit linear inequalities. Dropping box bounds, changing inequality orientation, or removing difficult constraints invalidates the comparison.

## Accuracy And Failure Rules
Use the same requested tolerances as the experiment being reported. Count solver errors, timeouts, numerical failures, and iteration-limit exits as failures. Do not exclude hard instances after seeing solver behavior, except for a predeclared memory guard that applies equally to all compared methods.

## Solver Resources
Use a single-process CPU solver run per QP instance unless a future benchmark explicitly adds a parallel setting. Do not report results from commercial solvers as improvements to the reproduced open-source method unless they are clearly labeled as external baselines.

## Result Contract
A submitted method must write raw JSON with the same top-level structure used by `method/run_odyn.py`, and it must be scored only through `scripts/evaluate.sh`. Evaluation code must remain method-agnostic.

## Compliance Checklist
- [ ] Main benchmark uses the provided Maros-Meszaros files unchanged
- [ ] Variable bounds are included as linear constraints
- [ ] Requested tolerance and failure-counting rules are unchanged
- [ ] Raw results are scored by `scripts/evaluate.sh`
- [ ] `eval/` does not import the submitted method

