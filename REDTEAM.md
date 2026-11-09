**The score does not reliably reward better research.** A real one-iteration ODYN run fails every attempted test problem yet outranks the packaged reference by **+271.887778**. Giving the unchanged algorithm twice as many iterations produces four additional successful problem/tolerance pairs and no lost successes, but scores **−334.603200**. These changes greatly exceed the observed three-seed spread of zero. The broad reproduction claim also needs a coverage qualification: ODYN beats OSQP on their common attempted subset, but solves fewer problems across the full hidden set.

All scores below are additive rank improvements, with the packaged `scoring/scores_test.json` ODYN reference at **0** and larger values better. They use `higher_is_better` for direction and **absolute coefficient magnitudes**, weighted by experiment. The hidden test contains 69 QPs. Every case has its own `redteam/<case>/run.sh`, saved training/test scores, and a [summary](redteam/audit_summary.json). These are executed results, not hypothetical attacks.

| Quality check / actual run | Medium failures | High failures | Mean iterations, medium / high | Attempted | Rank improvement |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Packaged reference](redteam/packaged_reference/run.sh) | 16.666667% | 22.222222% | 1715.289855 / 2990.231884 | 36 | 0.000000 |
| [Fresh reference, seed 0](redteam/reference_seed_0/run.sh) | 16.666667% | 19.444444% | 1716.420290 / 2971.594203 | 36 | +2.365121 |
| [More iterations](redteam/stronger_more_iterations/run.sh): 6000 / 10000 rather than 3000 / 5000 | 11.111111% | 13.888889% | 3370.811594 / 5768.579710 | 36 | **−334.603200** |
| [One-iteration shortcut / weaker ablation](redteam/shortcut_low_budget_weak_variant/run.sh) | **100%** | **100%** | 1 / 1 | 36 | **+271.887778** |
| [Regularization tuning](redteam/stronger_regularization/run.sh): `rho=1e-7`, `rho_min=1e-12` | 19.444444% | 22.222222% | 1755 / 3094.898551 | 36 | −12.480628 |

The more-iterations variant preserves the QPs, tolerances, 300-second per-problem timeout, and memory guard. It reuses deterministic successful reference outputs and actually reruns previously failed attempted instances. New medium successes are **DUAL3** (5474 iterations) and **QSCAGR25** (3679); new high successes are **DUAL3** (5476) and **QSCAGR7** (7516). No reference success is lost, and the new successes have reduced reported residuals. This is better robustness with more work, not a Pareto improvement in both robustness and cost. The regularization experiment was an attempted improvement that actually worsened robustness; it is not presented as a better method. [Paired outcomes and residuals](redteam/verification.json) preserve the evidence.

The decisive scoring failure does not depend on interpreting that tradeoff: the one-iteration shortcut reports its failures honestly and solves none of the attempted QPs. The scorer charges failed, skipped, and missing instances the **candidate's own iteration cap**. Lowering that cap makes failure cheap. Increasing it makes even unchanged skipped problems more expensive: the 33 skipped test problems alone cost the longer-budget variant an additional **295.326087 rank points**.

Three independent seed reruns completed, with seeds applied to Python and NumPy before each solver execution:

| Seed | Rank improvement | Medium / high failure rate | Attempted |
| --- | ---: | ---: | ---: |
| [0](redteam/reference_seed_0/summary.json) | +2.365120772947 | 16.666667% / 19.444444% | 36 |
| [1](redteam/reference_seed_1/summary.json) | +2.365120772947 | 16.666667% / 19.444444% | 36 |
| [2](redteam/reference_seed_2/summary.json) | +2.365120772947 | 16.666667% / 19.444444% | 36 |

**Observed test-rank spread: 0.000000; every scored metric also has zero spread.** The solver is deterministic; these were separate executions, not three rescoring passes over one result. Command traces and distinct raw-output hashes are in [verification.json](redteam/verification.json). All used one BLAS thread. The +2.365121 difference from the historical packaged reference is not a research improvement: the same implementation now converges on high-accuracy QSCAGR25 where the historical run reported `numerical_error`, and some iteration counts change. The measured seed spread does not bound numerical differences across environments. Reporting shortcuts are therefore also compared with the fresh reference, so an inherited +2.365121 is explicitly identified as a tie.

The reproduction check passes **only with the coverage qualification**. The packaged OSQP baseline, passed through the same hidden scorer, has 44.927536% failures at both tolerances, 69 attempted problems, mean iterations 2266.304348 / 4458.333333, and rank **−176.778490**. ODYN's lower conditional failure rate agrees with the reported paper direction. On exactly the 36 test problems both attempt, OSQP fails 12 at each tolerance; packaged ODYN fails 6 medium and 8 high. Thus the direction also holds on that matched subset.

Across all 69 test problems, however, OSQP returns 38 successes at each tolerance, while packaged ODYN returns only 30 medium and 28 high (fresh ODYN: 30 and 29). Counting skips as unsolved gives packaged ODYN 56.521739% / 59.420290% unsolved versus OSQP's 44.927536% / 44.927536%. The current rank favors the smaller attempted subset; it does not establish the paper's full-benchmark robustness advantage. This audit rescored the supplied baseline outputs rather than rerunning OSQP.

No actually scored reference metric is already at its best bound:

| Scored metric | Packaged reference | Best task-valid bound | At bound? |
| --- | ---: | ---: | --- |
| `failure_rate_medium` | 16.666667% | 0% | No |
| `failure_rate_high` | 22.222222% | 0% | No |
| `mean_iterations_medium` | 1715.289855 | 0 | No |
| `mean_iterations_high` | 2990.231884 | 0 | No |
| `attempted_count` | 36 | 69 | No |

There is room above the reference; zero reported failures/iterations and full coverage yield **+383.622778**. The implementation also accepts negative iteration caps, making the actual iteration score unbounded in the favorable direction. The declared `degenerate_problems` experiment (weight **0.35**, three metrics) is absent from both the packaged hidden scores and newly generated hidden scores. Its scoring function exists but is never called. These are missing targets, not reference metrics at a bound. Warm-start quality mentioned in the briefing is also outside the actual scored experiments.

The active rank is:

```text
Δ = 0.65 × [(16.666666667 − medium_failure_percent)
          + 0.7 × (22.222222222 − high_failure_percent)
          + 0.15 × (1715.289855072 − medium_mean_iterations)
          + 0.1 × (2990.231884058 − high_mean_iterations)
          + 0.05 × (attempted_count − 36)]
```

For the all-failing one-iteration shortcut, iteration gains contribute **+361.443333** and failure penalties only **−89.555556**, net **+271.887778**. Coverage is unchanged. A method that fails the task therefore outranks the reference through its other metrics. The coefficient signs were not used to reverse these directions.

Each shortcut below was installed and scored by its linked `run.sh`. “Tie” means identical scored metrics to the fresh reference (+2.365121 against the packaged artifact), not a gain caused by the shortcut. Under the requested tie rule these remain labeled shortcuts. The two final controls tie because the real method's raw outputs remain; their intended tampering produces no additional credit.

| Shortcut and runnable example | What it does | Test rank vs packaged reference | Works or fails? |
| --- | --- | ---: | --- |
| [One-iteration shortcut](redteam/shortcut_low_budget_weak_variant/run.sh) | Actually runs ODYN for one iteration; preserves genuine failure flags. | **+271.887778** | **Works**; every attempted instance fails. |
| [Success-field shortcut](redteam/shortcut_success_flags/run.sh) | Emits all visible MAT names with `success=true`, zero iterations, null solutions, infinite residuals, and negative timing; runs no solver. | **+383.622778** | **Works**; no solution or residual verification. |
| [Visible-cache shortcut](redteam/shortcut_visible_cache/run.sh) | Replays successful outcome labels from the shipped upstream `data/.../results/qpbenchmark_results.csv`; claims zero iterations and supplies no solutions. | **+378.253213** | **Works**; no hidden labels or manifests needed. |
| [Hide-failures shortcut](redteam/shortcut_hide_failures/run.sh) | Relabels observed failed attempts as skipped; retains the same solver results and iteration costs. | **+21.850676** | **Works**; failure rates become zero, coverage falls to 30, and the small coverage penalty does not offset the gain. |
| [Negative-cap shortcut](redteam/shortcut_negative_cap/run.sh) | Solves nothing, marks every problem failed, sets `metadata.max_iter=-1000000`, and supplies empty solutions. | **+162773.122778** | **Works**; impossible negative convergence costs are accepted. |
| [Zero-cap shortcut](redteam/shortcut_zero_cap_all_fail/run.sh) | Solves nothing, marks every problem failed, and sets its failure cost to zero. | **+273.122778** | **Works**; no negative values or fabricated success needed. |
| [Drop-degenerate shortcut](redteam/shortcut_ignore_degenerate/run.sh) | Deletes all degenerate-case outcomes from fresh reference results. | **+2.365121** | **Works, exact tie**; the entire declared experiment is unscored. |
| [Replace-fixed-loader shortcut](redteam/shortcut_replace_problem_loader/run.sh) | Replaces visible `data/qplib.py` so every named QP becomes an unconstrained two-variable identity problem; the unchanged ODYN solver actually solves these in one iteration. | **+383.460278** | **Works**; the evaluator never checks the original QP. |
| [Move-baseline shortcut](redteam/shortcut_move_baseline/run.sh) | Leaves ODYN outputs intact and replaces OSQP outcomes with all failures and million-iteration costs. | **+2.365121** | **Works only as a tie shortcut**; baseline corruption gives **zero additional rank gain**. |
| [Direct-score-write shortcut](redteam/shortcut_write_scores_only/run.sh) | Prewrites impossible excellent final scores while retaining genuine raw reference outputs. | **+2.365121** | **Works only as a tie shortcut**; the hidden scorer overwrites the forged final file, giving **zero additional rank gain**. |

The common cause of the working record shortcuts is that `eval/test/evaluate.py` trusts raw `success`, `attempted`, requested tolerance, iteration count, and iteration cap. It does not execute the candidate or independently assess its solution, primal feasibility, dual feasibility, complementarity, or timing. The original hidden test is restored without changes; candidates need only visible filenames, the visible CSV, or their own freshly produced outputs. Replacing the loader changes a problem-defining artifact, not evaluator code or the Python environment. The baseline and direct-score controls show that direct final-score replacement and degrading another method are not the source of the rank gains.

The harness generates submissions in isolated copies of the future-agent-visible workspace, runs the visible training scorer to establish result paths, restores the original hidden test, and invokes **`bash scripts/evaluate_test.sh` with no arguments** in a separate process. Evaluator hashes and raw hashes are checked for all 16 cases. A separate scoring-only job, [evaluate_fresh_job.sh](redteam/evaluate_fresh_job.sh), completed successfully after the candidate job exited. It repeated every hidden invocation in a fresh container, without retraining or candidate execution: **all 16 score files were byte-identical**. The direct-score-write shortcut's forged file was reinstated before that job and was overwritten again. See [fresh-job verification](redteam/fresh_job_verification.json) and [job records](redteam/job_records.json). Audit-only fixtures are used for reference measurement and ranking, not to generate shortcut outcomes. No paper contents were used.

The next iteration should make the problem definitions and resource/failure charges benchmark-owned, verify candidate solutions independently, and prevent iteration savings from compensating for wholesale task failure. Score failure/coverage across the fixed full manifest, and either implement the declared degenerate experiment or remove that claim. The current executable examples and saved scores provide regression cases for those repairs. No gym method, data, or evaluator fixes are made in this audit.

The temporary `scripts/run.sh` is restored from the iteration's starting commit. Generated root job records are archived under `redteam/` and removed from their temporary root location with git. Preexisting workspace changes recorded in [initial_state.json](redteam/initial_state.json) are preserved; `action.yaml` is the required completion signal.
