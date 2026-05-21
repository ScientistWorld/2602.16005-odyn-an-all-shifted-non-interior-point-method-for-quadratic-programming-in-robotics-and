# Train/Test Evaluation Design Notes

## Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. They call `eval/train/` and `eval/test/` respectively and write `scoring/scores_train.json` / `scoring/scores_test.json`.
- Checked for train/test cross-imports with grep; none were present.
- Confirmed no `scoring/scores_train.json` or `scoring/scores_test.json` stubs exist.
- Checked the visible and held-out Maros-Meszaros manifests. They use disjoint problem-name lists with comparable counts, while the test scorer reuses raw method artifacts rather than rerunning solver code.
- Reviewed `scoring/reference.json` for paper-agreement metrics. The scoring metrics are scientific quantities, not deviation-from-paper values.
- Ran `bash -n` on both split scripts.

## Changed

- Kept failure-rate scoring on the raw solver `success` flag while counting missing or skipped slice problems as failures. A runtime test showed residual fields were not comparable across artifacts: OSQP did not report them at all, while ODYN's stored `infeasibility` diagnostic was not calibrated to the requested tolerance and made medium-tolerance results look worse than high-tolerance results.
- Added train/test provenance text documenting the success-and-coverage criterion.
- Added `mean_iterations_medium` and `mean_iterations_high` to the failure-rate experiment. These are machine-independent convergence-cost metrics and assign the iteration cap to missing or failed problems, so methods cannot improve reliability scores by skipping hard cases or hiding slow convergence.
- Reduced the coefficient on `attempted_count` so it remains a coverage guardrail without dominating the failure-rate objective.
- Added required metric descriptions throughout `scoring/reference.json`.

## Runtime Concerns For The Runner

- First split-scoring run (`e1be94a3-626`) completed, but exposed a residual-certificate evaluator artifact: OSQP raw artifacts contain solver success flags and iteration counts but no residual diagnostic fields, and ODYN's `infeasibility` diagnostic is not calibrated to the requested tolerance. The train/test evaluators now use the solver success flag consistently and keep the anti-shortcut coverage guard by scoring missing or skipped slice problems as failures.
- Degenerate-problem scoring is not split because there are only three cases; it remains a triangulation constraint rather than a strong train/test anti-shortcut signal.
- The held-out test scorer aligns to methods present in `scoring/scores_train.json` when that file exists. If a runner invokes test first, it falls back to `tmp/results/*.json`; that is usable but loses the explicit train-method alignment check.
