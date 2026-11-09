# Experiment Overview

Both experiments run the candidate solver on evaluator-constructed instances and count an instance as solved only when the evaluator's own residual check of the returned primal-dual point passes. Nothing the solver reports about itself is used.

## failure_rate_comparison
Establishes whether a solver reliably reaches medium (1e-6) and high (1e-9) accuracy on a standard suite of difficult convex QPs within a fixed CPU budget per instance. The suite is the tractable part of the Maros-Meszaros set; the held-out slice scores unseen perturbations of its problems. Errors, crashes, budget overruns, missing outputs, and points that fail the check are all failures, and every instance stays in the denominator. Lower failure rates mean a more dependable solver. The high-accuracy rate exposes methods that only work at loose tolerances.

## degenerate_problems
Establishes whether a solver stays reliable when the optimum is degenerate. The cases are redundant active constraints, failed constraint qualifications with rank-deficient and badly scaled data, and non-unique solutions from a semidefinite Hessian, generated freshly for the held-out slice. It is scored like the first experiment, as failure rates at medium and high accuracy.
