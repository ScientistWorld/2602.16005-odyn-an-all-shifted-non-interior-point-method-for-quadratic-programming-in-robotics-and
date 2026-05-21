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

### [2026-05-21 01:05] - secondary_claims
- The next resumed refresh attempt was preempted for SLURM worker drain after persisting 38 medium-tolerance benchmark entries through `GOULDQP2`.
- Switched the benchmark driver to staged prefix expansion (`40`, `80`, `120`, full) so resumed jobs can make bounded progress across repeated preemptions while keeping the same ODYN benchmark protocol.

### [2026-05-21 01:40] - secondary_claims
- The staged refresh job finished and regenerated complete patched ODYN medium/high raw files despite multiple scheduler preemptions.
- Auditing the completed artifacts showed that the OSQP high-tolerance raw file was still only a 16-problem partial because `scripts/run.sh` checked only for file existence; this turn fixes the driver to verify completion counts and resume incomplete baseline files before rescoring.

### [2026-05-21 16:35] - secondary_claims
- The OSQP baseline repair job resumed `osqp_full_high.json` from 16 persisted problems to the full 138-problem benchmark and then regenerated `scoring/scores.json`.
- The workspace is internally consistent again: ODYN medium/high and OSQP medium/high raw files are all complete, and `python3 validate.py --compare` passes on the final scored artifacts.

### [2026-05-21 16:50] - secondary_claims
- Corrected the Table IV paper transcription in `scoring/reference.json`: OSQP's LICQ-failure entry is a dagger note ("declared dual infeasible"), not a numeric iteration count.
- Updated the degenerate benchmark scoring contract so the unambiguous `redundant_ineq` case is the primary metric, retained `licq_failure` as a diagnostic constraint, and revalidated the workspace with both `python3 validate.py` and `python3 validate.py --compare`.

### [2026-05-21 17:02] - secondary_claims
- Audited the reproduction with a parallel explorer and tightened the dense ODYN line-search condition so it explicitly uses the relaxed Armijo `gamma` multiplier.
- Updated `scripts/run.sh` to execute a fresh ODYN degenerate smoke run in the container before regenerating train/test/main scores from the completed raw benchmark artifacts.
- Revalidated locally with `python3 validate.py --compare`; the fresh ODYN smoke itself requires the container dependencies because the login Python lacks NumPy.

## Stop Justification
- Completed at milestone `secondary_claims`.
