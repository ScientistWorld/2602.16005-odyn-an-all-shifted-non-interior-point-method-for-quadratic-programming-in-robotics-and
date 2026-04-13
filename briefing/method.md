# Paper's Method

How the paper approaches the problem, i.e. the paper's core contributions.

## Key Contribution

ODYN introduces an all-shifted non-interior-point method (NIPM) that relaxes strict interior-feasibility requirements while maintaining path-following convergence. The three core innovations are:

1. **All-Shifted NCP Functions**: The complementarity condition s*z=0 is regularized using shifted variables (s_E, z_E) with proximal penalty ρ_n, providing stability near convergence where the NCP function becomes flat. This gives: φ(s,z;μ) + ρ_n*(s-s_E) + ρ_n*(z-z_E) = 0

2. **Centering-Weighted Barrier**: Adaptive barrier parameter update based on progress. If residual decreases sufficiently, σ is decreased (faster convergence); otherwise, σ is increased (larger steps). μ is computed as ||min(s,z)||²/p.

3. **Proximal Primal-Dual Estimates**: The proximal references (x_E, y_E, z_E, s_E) are updated via interpolated extrapolation between current and previous iterates, controlled by adaptive θ parameters. This provides a central path toward the solution.

## Approach

ODYN solves QP problems by iteratively solving a perturbed KKT system using Newton's method:

1. **KKT System**: The condensed KKT system uses H = Q + J^T*D^(-1)*J (always positive definite due to proximal terms), enabling stable Cholesky factorization.

2. **Search Direction**: Solve condensed system for Δx, then back-substitute for Δλ, Δz, Δs.

3. **Line Search**: Flexible Armijo condition using natural merit function M(U) = 0.5*(||r_d||² + ||r_p||² + ||r_g||²).

4. **Neighborhood Control**: Iterates kept in relaxed neighborhood ||r(U+α;Π)||∞ ≤ θ*||r(U;Π)||∞ + β*μ.

5. **Step-Length Adaptation**: θ parameters (for x, y, z/s) are adapted based on residual improvement — decrease when good progress, increase when stagnation.

6. **Termination**: Combined relative/absolute tolerance on all KKT residuals.

## Main Claims

Primary: ODYN achieves the lowest failure rate (9.7%) on the Maros-Meszárós test set at medium accuracy among open-source solvers (PROXQP 33.0%, OSQP 44.7%), demonstrating superior convergence robustness.

Secondary: ODYN's warm-start capability (warm-to-cold ratio) significantly outperforms ALM-based solvers (OSQP, PROXQP) due to its non-interior-point formulation that doesn't require strict interior feasibility.

Note: The paper's GitHub URL is not directly provided in the paper text. The solver is released as open-source C++ with Python bindings.