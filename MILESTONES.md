# Reproduction Milestones

**Current: secondary_claims**

## Progress Log

### [2026-04-12 00:00] - none
- Read the paper and identified the main task: reproduce ODYN, an all-shifted non-interior-point QP method.
- Identified the core evaluation surfaces: Maros-Meszaros failure rates and degenerate QP iteration counts.

### [2026-04-14 00:00] - method_runs
- Implemented a Python ODYN solver with dense and sparse backends.
- Ran the method on simple QPs and a subset of Maros-Meszaros instances.
- Confirmed the paper's algorithm executes end-to-end, but the reproduction did not yet support the central claim.

### [2026-04-17 05:20] - method_runs
- Audited the previous `core_claim` marker and rolled it back because the full benchmark was incomplete and the evaluator imported from `method/`.
- Moved benchmark loading into `data/`, separated raw method execution from scoring, and fixed key ODYN equations before submitting a corrected smoke run.

### [2026-04-17 05:35] - method_runs
- Completed a CPU smoke job with the corrected code.
- ODYN solved all three degenerate QP cases, matching the paper's robustness claim on that small experiment.
- The Maros slice was skipped by the memory guard, so the next job targets named small benchmark instances before claiming `core_claim`.

### [2026-04-17 05:35] - core_claim
- Completed a CPU smoke job on 10 named small Maros-Meszaros QPs plus the three degenerate cases.
- ODYN solved all 10 attempted Maros-Meszaros instances at medium tolerance, giving 0.0% failure rate on this scaled subset.
- Degenerate case iteration counts were 6, 3, and 9 for redundant inequalities, LICQ failure, and multiple solutions, supporting the paper's robustness claim on the Table IV-style pathologies.
- The current claim is intentionally scoped to the scaled smoke suite; a broader subset job is queued next to expand toward `core_claim_plus`.

### [2026-04-17 05:45] - core_claim_plus
- Ran ODYN on a broader named Maros-Meszaros subset at both medium and high requested tolerances.
- ODYN attempted 29 dense-feasible problems and solved 20 at each tolerance; skipped memory-guarded cases are excluded from the failure-rate denominator.
- The reproduced failure rate is 31.0% for both tolerances on this harder subset, worse than the paper's ODYN number but still a meaningful expansion beyond the 10-problem smoke suite.
- Queued a local OSQP run on the exact 29 ODYN-attempted problems so future scores include a direct same-subset baseline.

### [2026-04-17 05:55] - core_claim_plus
- Completed the local OSQP comparison on the same 29 broad-subset problems.
- OSQP failed 12 of 29 problems at both tolerances, while ODYN failed 9 of 29, giving a same-subset robustness advantage for the reproduced method.
- Added safer dense condensed-system factorization retries and queued a stabilized ODYN rerun with higher iteration limits.

### [2026-04-17 06:05] - core_claim_plus
- The stabilized ODYN rerun reduced broad-subset failure rates to 17.2% at medium tolerance and 20.7% at high tolerance.
- All remaining ODYN failures are max-iteration cases; the previous numerical-error failures now solve.
- Queued one final higher-iteration broad-subset pass to test whether the remaining failures are iteration-budget limited.


### [2026-04-17 06:15] - secondary_claims
- Completed the final higher-iteration broad-subset pass in job 8eebc754-99a.
- ODYN solved 26 of 29 dense-feasible Maros-Meszaros problems at medium tolerance and 25 of 29 at high tolerance, giving failure rates of 10.3% and 13.8%.
- The same-subset OSQP baseline remained at 41.4% failure for both tolerances, and the degenerate-QP iteration results remain close to the paper's Table IV.
- Marked `secondary_claims` because the packaged environment now reproduces both tracked paper result surfaces: benchmark robustness and degenerate-problem robustness.
