# Research Direction

## Research Problem
This benchmark is about reliable convex quadratic programming for robotics and AI workloads. The scientific question is whether a solver can maintain robustness on difficult, degenerate, and warm-start-relevant QPs without depending on ideal interior-point assumptions.

## Core Contribution Scope
Future work should improve numerical QP solvers in the same problem family. The useful contribution is better robustness: verified solutions on more hard and degenerate instances, at both accuracies, under the same budget and failure rules.

## Approach Scope
In-scope changes include new or improved numerical QP algorithms, linear algebra choices, regularization policies, initialization strategies, stopping checks, and warm-start handling. Implementations may be dense, sparse, or hybrid as long as they solve the same QP formulation and expose comparable raw results.

## Out Of Bounds
- Replacing the method with a commercial optimizer and claiming it as the improved research method.
- Hardcoding solutions, statuses, iteration counts, or paper values for benchmark instances, or recognizing instances to replay stored or precomputed solutions.
- Fabricating or inflating multipliers to pass the residual check instead of solving the problem.
- Training a surrogate model that maps problem data to answers instead of running a QP algorithm.
- Changing the benchmark problems, tolerances, budget, or the evaluators to make the method look better.
- Dropping constraints, variable bounds, or degenerate cases from the scored experiments.
