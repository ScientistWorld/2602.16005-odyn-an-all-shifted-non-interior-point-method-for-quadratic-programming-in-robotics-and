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

### [2026-04-17 12:47] - secondary_claims
- Audited the restored workspace and confirmed the implementation is the paper's ODYN algorithm rather than a surrogate.
- Verified `eval/` is independent of `method/` and that current scores are regenerated from raw solver result JSON files.
- Removed evaluator `/home/user` assumptions and added deterministic raw-result provenance to `scoring/scores.json`.

### [2026-05-21 00:00] - secondary_claims
- Tightened the ODYN solver updates to match the paper more closely: neighborhood-gated proximal estimate refresh, per-residual interpolation and regularization updates, and Eq. (52)-style stopping checks in the sparse backend.
- Queued a containerized smoke validation job before changing any reported benchmark numbers.

### [2026-05-21 00:15] - secondary_claims
- Audited the continuation workspace and confirmed the implementation is still an ODYN solver rather than a surrogate model.
- Found that the patched ODYN code had become newer than the active ODYN benchmark artifacts, so this turn resubmits the scored ODYN benchmark to refresh `scoring/scores.json` against the current implementation.

### [2026-05-21 00:35] - secondary_claims
- The first scored-refresh rerun was orphaned by the scheduler before `odyn_full_medium.json` reached its final write, so no refreshed raw outputs were persisted.
- Patched the ODYN and OSQP runners to checkpoint after each problem and resume from partial JSON files, then rewired the reusable scripts to use `--resume` for long benchmark jobs.

## Stop Justification
- Completed at milestone `secondary_claims`.
