# Reproduction Milestones

**Current: secondary_claims**

## Progress Log

### [2026-04-17 01:32] - method_runs
- Ran the Python ODYN implementation end-to-end on degenerate QPs and a 10-problem Maros-Meszaros smoke subset.
- Confirmed the solver writes raw method results and `scripts/evaluate.sh` scores them without importing from `method/`.

### [2026-04-17 01:51] - core_claim
- Ran ODYN and OSQP on a shared 29-problem dense-feasible Maros-Meszaros subset at medium and high tolerances.
- ODYN solved the subset with 17.24% medium and 20.69% high failure rates, versus OSQP's 41.38% at both tolerances.
- Degenerate QP cases ran successfully, matching the paper's robustness target at small scale.

### [2026-04-17 02:13] - core_claim_plus
- Increased ODYN iteration budgets on the same subset.
- ODYN improved to 10.35% medium and 13.79% high failure rates, near the paper's reported 9.7% and 15.5% despite this reproduction using a Python dense backend.

### [2026-04-17 07:49] - secondary_claims
- Completed the full Maros-Meszaros benchmark pass with ODYN attempting all dense-feasible cases and OSQP attempting all 138 problems.
- ODYN achieved 12.33% medium and 23.29% high failure rates over 73 dense-feasible attempted instances; OSQP was around 50% failure over all 138.
- Added reusable scoring, baseline, reproduction, download, and environment scripts.

## Stop Justification
- Not stopped yet. The next job is a final CPU packaging check after documentation and scoring cleanup.
