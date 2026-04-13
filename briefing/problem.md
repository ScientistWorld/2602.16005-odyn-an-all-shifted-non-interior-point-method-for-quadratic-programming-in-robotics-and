# Problem Definition

What problem does this paper address? Write this so that someone with no knowledge of the paper can understand what needs to be solved and how success is measured.

Do NOT describe the paper's method or solution here — only the problem itself.

## Research Question

How can we build a QP solver that simultaneously achieves: (1) high convergence robustness across hard/difficult QP problems, (2) efficient warm-starting for sequential problems, (3) robustness to degenerate/ill-conditioned cases (redundant constraints, rank-deficient matrices, multiple solutions)? Existing state-of-the-art solvers make trade-offs: interior-point methods (PIQP, MOSEK, GUROBI) are robust but don't support warm-starting; augmented-Lagrangian methods (PROXQP, OSQP) support warm-starting but have higher failure rates on hard problems.

## Why It Matters

QP solvers are foundational in robotics and AI — they underpin model predictive control (MPC), contact simulation, whole-body control, SQP-based trajectory optimization, and differentiable optimization layers in neural networks. These applications require solvers that handle sequences of related QP problems efficiently (warm-start), solve hard/degenerate problems robustly, and achieve high accuracy. Current solvers cannot satisfy all three requirements simultaneously.

## Success Criteria

A successful QP solver should:
1. **Low failure rate**: Solve the vast majority of problems in the Maros-Meszárós test set (138 problems) within time limits at medium (1e-6) and high (1e-9) accuracy
2. **Efficient warm-start**: Achieve significant iteration reduction when solving related QP problems in sequence (warm-to-cold ratio much less than 1.0)
3. **Handle degeneracy**: Solve problems with redundant constraints, linearly dependent constraint matrices, positive semidefinite cost matrices, and ill-conditioning
4. **High accuracy**: Reach primal-dual optimality within tight tolerances
5. **Reasonable speed**: Compute times competitive with state-of-the-art solvers