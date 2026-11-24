# ODYN: An All-Shifted Non-Interior-Point Method for Quadratic Programming in Robotics and AI

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2602.16005"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2602.16005-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2602.16005](https://arxiv.org/abs/2602.16005) |
|:---|:---|
| **Domain** | Numerical Optimization / Quadratic Programming |
| **TL;DR** | ODYN is a novel non-interior-point QP solver that combines all-shifted NCP functions with proximal primal-dual regularization, achieving state-of-the-art convergence on the Maros-Meszárós benchmark with superior warm-start performance. |

## Summary

ODYN is a warm-startable QP solver based on all-shifted non-interior-point methods (NIPMs). It relaxes strict interior-feasibility requirements of traditional interior-point methods while preserving path-following behavior, enabling robust handling of degenerate, ill-conditioned, and warm-started problems. The solver blends elements of primal-dual interior-point methods with augmented-Lagrangian techniques, featuring three key innovations: a centering-weighted barrier, all-shifted NCP formulation for degeneracy robustness, and proximal Lagrangian penalties. Evaluated on the Maros-Meszárós test set (138 QP problems), ODYN achieves the lowest failure rate at medium accuracy (9.7%) among tested solvers.

## Problem

Build a convex quadratic programming (QP) solver that remains reliable across difficult benchmark problems, sequential warm-started problem families, and degenerate or ill-conditioned cases such as redundant constraints, rank-deficient matrices, and non-unique solutions.

## The paper's method

ODYN introduces an all-shifted non-interior-point method (NIPM) that relaxes strict interior-feasibility requirements while maintaining path-following convergence. The three core innovations are:

1. **All-Shifted NCP Functions**: The complementarity condition s*z=0 is regularized using shifted variables (s_E, z_E) with proximal penalty ρ_n, providing stability near convergence where the NCP function becomes flat. This gives: φ(s,z;μ) + ρ_n*(s-s_E) + ρ_n*(z-z_E) = 0

2. **Centering-Weighted Barrier**: Adaptive barrier parameter update based on progress. If residual decreases sufficiently, σ is decreased (faster convergence); otherwise, σ is increased (larger steps). μ is computed as ||min(s,z)||²/p.

3. **Proximal Primal-Dual Estimates**: The proximal references (x_E, y_E, z_E, s_E) are updated via interpolated extrapolation between current and previous iterates, controlled by adaptive θ parameters. This provides a central path toward the solution.

## Key results of the paper

- **Failure Rate (Medium Acc.)**: ODYN 9.7% vs PROXQP 33.0% vs OSQP 44.7% vs PIQP 10.7% vs MOSEK 14.6% vs GUROBI 9.7%
- **Warm-to-Cold Ratio**: ODYN significantly outperforms OSQP and PROXQP across perturbation levels (δ = 1e-3, 1e-2, 1e-1)
- **Dense Backend**: Competitive per-iteration computation time vs PROXQP and PIQP for n ∈ [1, 400]
- **Degenerate Problems**: ODYN handles redundant constraints, LICQ failures, and multiple-solution QPs robustly

## Run it

```bash
pip install sciworld
sw research 2602.16005 --mode innovate --agent claude-code
sw evaluate 2602.16005
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

