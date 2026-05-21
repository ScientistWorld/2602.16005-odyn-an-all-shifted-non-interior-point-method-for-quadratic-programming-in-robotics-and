# Experiment Overview

## failure_rate_comparison
This experiment checks whether the solver can handle a standard suite of difficult convex quadratic programs at fixed requested tolerances. It treats errors, timeouts, and non-convergence as failures, so lower failure rates indicate a more dependable solver rather than just faster behavior on easy instances. It also reports how many benchmark problems the solver actually attempted, so reduced coverage is visible instead of hidden by the failure-rate denominator.

## degenerate_problems
This experiment checks whether the solver handles small but structurally difficult QPs. The cases are designed to expose fragility around redundant constraints, failed regularity assumptions, and solution non-uniqueness. The benchmark ranks methods by the redundant-constraint case because every solver has a numeric paper value there; the LICQ-failure case is still reported, but one paper baseline is marked only as a qualitative failure rather than a numeric iteration count.
