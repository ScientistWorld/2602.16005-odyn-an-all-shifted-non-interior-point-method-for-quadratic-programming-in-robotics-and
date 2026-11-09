# Problem Definition

## Research Question

Build a convex quadratic programming (QP) solver that remains reliable across difficult benchmark problems and degenerate or ill-conditioned cases such as redundant constraints, rank-deficient constraint matrices, failed constraint qualifications, and non-unique solutions.

## Why It Matters

QP solvers are foundational in robotics and AI. They underpin model predictive control, contact simulation, whole-body control, SQP-based trajectory optimization, and differentiable optimization layers in neural networks. These applications need solvers that solve hard and degenerate problems robustly, to high accuracy, within a fixed compute budget.

## Success Criteria

A successful QP solver should:
1. **Low failure rate on hard problems**: return a verified optimal primal-dual point for as many Maros-Meszaros-derived instances as possible at medium (1e-6) and high (1e-9) accuracy, within a fixed CPU budget per instance.
2. **Degenerate robustness**: do the same on problems with redundant active constraints, failed regularity assumptions, positive semidefinite cost matrices, and non-unique solutions.
3. **Generalization**: the held-out instances are unseen perturbations and freshly generated degenerate problems, so behaviour tuned to particular public instances does not carry over.

Efficiency (iterations) and warm-start behaviour on related QP sequences matter for the applications above but are not scored here, because a solver's own iteration count cannot be verified independently.
