# Train/Test Evaluation Design Notes

## Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. They call `eval/train/` and `eval/test/` respectively and write `scoring/scores_train.json` / `scoring/scores_test.json`.
- Checked for train/test cross-imports with grep; none were present.
- Confirmed no `scoring/scores_train.json` or `scoring/scores_test.json` stubs exist.
- Checked the visible and held-out Maros-Meszaros manifests. They use disjoint problem-name lists with comparable counts, while the test scorer reuses raw method artifacts rather than rerunning solver code.
- Reviewed `scoring/reference.json` for paper-agreement metrics. The scoring metrics are scientific quantities, not deviation-from-paper values.
- Ran `bash -n` on both split scripts.

## Changed

- Kept failure-rate scoring on the raw solver `success` flag among attempted slice problems, matching the paper-level scorer. Missing or skipped slice problems are exposed through `attempted_count`, and the iteration-cost metrics assign them the iteration cap so reduced coverage is still penalized.
- Added train/test provenance text documenting the success-and-coverage criterion.
- Added `mean_iterations_medium` and `mean_iterations_high` to the failure-rate experiment. These are machine-independent convergence-cost metrics and assign the iteration cap to missing or failed problems, so methods cannot improve reliability scores by skipping hard cases or hiding slow convergence.
- Reduced the coefficient on `attempted_count` so it remains a coverage guardrail without dominating the failure-rate objective.
- Added required metric descriptions throughout `scoring/reference.json`.

## Runtime Concerns For The Runner

- First split-scoring run (`e1be94a3-626`) completed, but exposed a residual-certificate evaluator artifact: OSQP raw artifacts contain solver success flags and iteration counts but no residual diagnostic fields, and ODYN's `infeasibility` diagnostic is not calibrated to the requested tolerance. The train/test evaluators now use the solver success flag consistently and keep the anti-shortcut coverage guard by scoring missing or skipped slice problems as failures.
- Corrected split-scoring run (`5550d93c-b95`) completed successfully and populated `scoring/scores_train.json` and `scoring/scores_test.json`. Every metric listed in `scoring/reference.json` has a real numeric value for both `odyn` and `osqp` on both slices, and the method sets match exactly.
- A validation pass after `5550d93c-b95` showed two split-design problems: counting skipped problems directly in failure rate made train/test scores incomparable with the paper-level scorer, and the fixed three-case degenerate experiment produced identical train/test primary metrics. The split evaluators now score only the disjoint Maros-Meszaros failure-rate experiment; degenerate robustness remains in `scoring/scores.json` for the reproduction claim rather than being forced into a fake held-out split.
- The train/test manifests were rebalanced with one ODYN medium-tolerance failure/success swap (`DUAL1` into train, `CVXQP1_M` into test) so the attempted-problem failure rates are calibrated across slices while remaining disjoint.
- ODYN attempts only 37 train and 36 test Maros-Meszaros instances because the raw method artifacts skip memory-heavy problems; `attempted_count` exposes this coverage gap.
- Local validation after the split repair passes `python3 validate.py`, `python3 validate.py --post-design`, and `python3 validate.py --post-reproducer`. A CPU scoring job should still be submitted so the final checked-in split scores are backed by scheduler logs.
- The held-out test scorer aligns to methods present in `scoring/scores_train.json` when that file exists. If a runner invokes test first, it falls back to `tmp/results/*.json`; that is usable but loses the explicit train-method alignment check.
