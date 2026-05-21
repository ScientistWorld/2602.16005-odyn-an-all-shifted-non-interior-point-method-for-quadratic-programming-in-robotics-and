# Train/Test Evaluation Design Notes

## Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. They call `eval/train/` and `eval/test/` respectively and write `scoring/scores_train.json` / `scoring/scores_test.json`.
- Checked for train/test cross-imports with grep; none were present.
- Confirmed no `scoring/scores_train.json` or `scoring/scores_test.json` stubs exist.
- Checked the visible and held-out Maros-Meszaros manifests. They use disjoint problem-name lists with comparable counts, while the test scorer reuses raw method artifacts rather than rerunning solver code.
- Reviewed `scoring/reference.json` for paper-agreement metrics. The scoring metrics are scientific quantities, not deviation-from-paper values.
- Ran `bash -n` on both split scripts.

## Changed

- Fixed a shortcut risk where failure-rate scoring trusted the raw `success` flag alone. Both train and test now require a residual certificate: `success` plus finite `primal_residual`, `dual_residual`, and `infeasibility` no larger than `max(1e-6, 10*rtol)`.
- Added train/test provenance text documenting the residual-certified success criterion.
- Added `mean_iterations_medium` and `mean_iterations_high` to the failure-rate experiment. These are machine-independent convergence-cost metrics and assign the iteration cap to missing or failed problems, so methods cannot improve reliability scores by skipping hard cases or hiding slow convergence.
- Reduced the coefficient on `attempted_count` so it remains a coverage guardrail without dominating the failure-rate objective.
- Added required metric descriptions throughout `scoring/reference.json`.

## Runtime Concerns For The Runner

- The residual threshold may expose any raw result files that mark `success: true` while recording stale, missing, or non-finite residual fields. That is intended, but the next runner should check whether old artifacts need regeneration.
- Degenerate-problem scoring is not split because there are only three cases; it remains a triangulation constraint rather than a strong train/test anti-shortcut signal.
- The held-out test scorer aligns to methods present in `scoring/scores_train.json` when that file exists. If a runner invokes test first, it falls back to `tmp/results/*.json`; that is usable but loses the explicit train-method alignment check.
