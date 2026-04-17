# Research Direction

## Research Problem
This benchmark is about reliable convex quadratic programming for robotics and AI workloads. The scientific question is whether a solver can maintain robustness on difficult, degenerate, and warm-start-relevant QPs without depending on ideal interior-point assumptions.

## Core Contribution Scope
Future work should improve primal-dual numerical methods for QPs in the same problem family. The useful contribution is better robustness, convergence, or warm-start behavior under the same benchmark and failure rules.

## Approach Scope
In-scope changes include modifying the residual model, regularization schedule, linear-system reduction, factorization strategy, line search, initialization, stopping checks, or warm-start handling of a QP solver. Implementations may be dense, sparse, or hybrid as long as they solve the same QP formulation and expose comparable raw results.

## Out Of Bounds
- Replacing the method with a commercial optimizer and claiming it as the improved research method.
- Hardcoding solutions, statuses, iteration counts, or paper values for benchmark instances.
- Training a surrogate model that maps problem data to answers instead of running a QP algorithm.
- Changing the benchmark problems, tolerances, or failure definition to make the method look better.
- Dropping constraints, variable bounds, or degenerate cases from the scored experiments.

