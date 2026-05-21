# Problem Definition

## Research Question

Build a convex quadratic programming (QP) solver that remains reliable across difficult benchmark problems, sequential warm-started problem families, and degenerate or ill-conditioned cases such as redundant constraints, rank-deficient matrices, and non-unique solutions.

## Why It Matters

QP solvers are foundational in robotics and AI. They underpin model predictive control, contact simulation, whole-body control, SQP-based trajectory optimization, and differentiable optimization layers in neural networks. These applications require solvers that handle related QP sequences efficiently, solve hard and degenerate problems robustly, and achieve high accuracy.

## Success Criteria

A successful QP solver should:
1. **Low failure rate**: solve the vast majority of Maros-Meszaros benchmark problems within fixed limits at medium (1e-6) and high (1e-9) requested accuracy.
2. **High coverage**: report how many benchmark instances were attempted, so robustness cannot be inflated by silently skipping difficult problems.
3. **Degenerate robustness**: solve problems with redundant constraints, failed regularity assumptions, positive semidefinite cost matrices, and non-unique solutions.
4. **Efficient convergence**: use fewer iterations where possible while preserving the same problem definitions, tolerances, and failure rules.
5. **Warm-start usefulness**: on related QP sequences, reduce iteration count relative to cold starts without changing the target problem.
