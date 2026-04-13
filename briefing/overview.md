# Overview

- **Paper ID:** 2602.16005
- **Title:** ODYN: An All-Shifted Non-Interior-Point Method for Quadratic Programming in Robotics and AI
- **Domain:** Numerical Optimization / Quadratic Programming
- **TL;DR:** ODYN is a novel non-interior-point QP solver that combines all-shifted NCP functions with proximal primal-dual regularization, achieving state-of-the-art convergence on the Maros-Meszárós benchmark with superior warm-start performance.

## Short Summary

ODYN is a warm-startable QP solver based on all-shifted non-interior-point methods (NIPMs). It relaxes strict interior-feasibility requirements of traditional interior-point methods while preserving path-following behavior, enabling robust handling of degenerate, ill-conditioned, and warm-started problems. The solver blends elements of primal-dual interior-point methods with augmented-Lagrangian techniques, featuring three key innovations: a centering-weighted barrier, all-shifted NCP formulation for degeneracy robustness, and proximal Lagrangian penalties. Evaluated on the Maros-Meszárós test set (138 QP problems), ODYN achieves the lowest failure rate at medium accuracy (9.7%) among tested solvers.

## Key Results

- **Failure Rate (Medium Acc.)**: ODYN 9.7% vs PROXQP 33.0% vs OSQP 44.7% vs PIQP 10.7% vs MOSEK 14.6% vs GUROBI 9.7%
- **Warm-to-Cold Ratio**: ODYN significantly outperforms OSQP and PROXQP across perturbation levels (δ = 1e-3, 1e-2, 1e-1)
- **Dense Backend**: Competitive per-iteration computation time vs PROXQP and PIQP for n ∈ [1, 400]
- **Degenerate Problems**: ODYN handles redundant constraints, LICQ failures, and multiple-solution QPs robustly