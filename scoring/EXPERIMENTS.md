# Experiment Overview

## failure_rate_comparison
This experiment checks whether the solver can handle a standard suite of difficult convex quadratic programs at fixed requested tolerances. It treats errors, timeouts, and non-convergence as failures, so lower failure rates indicate a more dependable solver rather than just faster behavior on easy instances.

## degenerate_problems
This experiment checks whether the solver handles small but structurally difficult QPs. The cases are designed to expose fragility around redundant constraints, failed regularity assumptions, and solution non-uniqueness.

