# Hardening report (iteration 11)

**Outcome.** Better results now score higher on the hidden test, and worse ones lower. Every red-team shortcut that paid now loses heavily or ties the reference exactly. The reference reproduces the paper's direction: ODYN fails far less often than OSQP. All numbers below come from the final job (`4e755478-17c`), which reran the reference from the final code. Per-case evidence is in `notes/hardening/results.json`, `notes/hardening/noise.json`, and `notes/hardening/*.log`. The audit itself is `bash scripts/hardening/run_audit.sh`.

Ranks follow the gym rule: Σ weight × |coefficient| × (improvement over the reference in the metric's better direction). The reference is `odyn` in `scoring/scores_test.json` at 0; larger is better. The "before" numbers are the red team's, measured with the old scorer and old coefficients, so they are not on the same scale as "after".

## What was wrong and what changed

The old hidden test (`eval/test/evaluate.py`) scored raw JSON files written by the method:

- It took `success`, `attempted`, `iterations` and `metadata.max_iter` on trust.
- It charged failed, skipped and missing problems the candidate's own iteration cap.
- It computed failure rates only over "attempted" problems.
- The test problems were public files, loaded through visible, editable code (`data/qplib.py`).
- The declared degenerate experiment was never scored.

The new design:

1. **The evaluator runs the solvers itself.**
   - Every `scripts/solvers/<name>.sh` is called once per instance and tolerance through a fixed command-line contract (`--problem IN.npz --output OUT.npz --tol TOL`). The method name is the file stem; nothing is hard-coded.
   - An evaluator-owned OSQP baseline (`eval/{train,test}/osqp_solver.py`, fixed settings) runs through the same contract.
   - `bash scripts/evaluate_test.sh` with no arguments scores every registered solver plus the baseline.
   - The budget is fixed by `eval/`: 120 CPU-seconds per instance (the paper's 120 s limit), enforced with `ulimit -t` with BLAS threads set to 1, plus a total of 7200 CPU-seconds per solver to keep the hidden test light. The reference uses about 1,900 CPU-s on the hidden test (about 5 minutes on 8 cores, about 32 minutes on 1).
2. **Success is recomputed from raw outputs.**
   - An instance counts as solved only if the returned (x, y, z) passes the paper's own stopping test (Eq. 52). The absolute and relative tolerances are both ε; the evaluator recomputes the test from the point with the true slack s = h − Gx. That covers the equality residual, stationarity, and the NCP residual min(s, z), which handles feasibility, multiplier sign and complementarity.
   - On top of that, the relative duality gap must be at most √ε. This guards against forged multipliers.
   - Status, iteration counts and residuals written by the solver are ignored.
   - Every instance in the fixed manifest is in the denominator. Missing, unreadable, non-finite, crashed or over-budget runs are failures. Failure rates live in [0, 100], so no value can be impossible.
3. **Test inputs live only in `eval/test/`.**
   - The held-out Maros–Meszaros instances are two perturbations per problem, drawn with a seed stored only in `eval/test/manifest.json`. The perturbation is the paper's masked relative perturbation, restricted to feasibility- and convexity-preserving changes: cost vector, increased positive Hessian diagonal entries, relaxed inequality right-hand sides.
   - A degenerate-QP family is generated from a hidden seed.
   - Instances are anonymous files written to a temporary directory.
4. **Problem data is evaluator-owned.**
   - `eval/` loads the `.mat` files with its own code and checks each against a pinned SHA-256; altered data aborts scoring.
   - `scripts/download.sh` is pinned to upstream commit `afa738d9`, which I verified byte for byte against the 138 shipped files.
   - `eval/` imports nothing from `data/` or `method/`.
   - Fixing a latent loader bug: the old loader silently dropped bounds on fixed variables. They are now equality rows.
5. **Metrics.**
   - Scored metrics are now `failure_rate_medium` and `failure_rate_high` (Table III), and `degenerate_failure_rate_high` / `_medium` over a generated family of the three Table IV categories.
   - `mean_iterations_*` was removed. Iteration counts cannot be verified, and they were what let failing methods win.
   - `attempted_count` was removed, because coverage is now part of the denominator.
6. **Scope (scaled resources, same procedure).** The benchmark is the 73 Maros–Meszaros problems the Python reference can hold as dense arrays (n ≤ 1000; Q, A and G at most 2 GB dense), split 37 train / 36 test. This fixes the red team's coverage objection: ODYN previously skipped 33 of the 69 test problems while OSQP attempted all of them. The 65 larger problems are out of scope.
7. **Train/test balance.**
   - Train scores each problem as published plus one perturbation; test scores two hidden perturbations. Train also includes the paper's three degenerate examples.
   - The split was rebalanced twice for comparable difficulty: three problems moved on the old outcomes, then DUAL2 and DUAL4 ↔ DUALC2 and QSC205 under the final success test.
   - Final ODYN failure rates are 20.3 / 25.7 % on train vs 20.8 / 20.8 % on test; OSQP 40.5 / 46.0 % vs 47.2 / 44.4 %.
8. **Environment.** `environment/setup.sh` pins numpy 2.5.4, scipy 1.18.1 and osqp 1.1.3. The unused `proxsuite` package was dropped, so an off-the-shelf solver is not pre-installed.

### Choosing the success test

A first version added a strict duality-gap check (≤ ε) and a strict multiplier-sign check. It rejected many points that the reference's own Eq. (52) test accepts; ODYN is a non-interior method, so small negative multipliers within tolerance are expected. That version inverted the paper's direction: ODYN 47 % vs OSQP 44 % at medium accuracy.

The paper's Table III cannot be based on such a strict check. qpbenchmark's strict validation gives OSQP 25 % success at mid accuracy, whereas the paper reports 55 % (44.7 % failures). So the paper counts each solver's own convergence test at ε_abs = ε_rel = ε. The final test therefore recomputes Eq. (52) from the returned point.

Eq. (52) alone can be forged: cancelling multiplier pairs on a box constraint inflate ‖z‖ and loosen every tolerance. The √ε gap guard rejects such points. On the cached outputs it rejected no OSQP success and no ODYN high-accuracy success, and 14 of 263 ODYN medium "successes". Those 14 had relative gaps up to about 2; for example PRIMALC1 was declared optimal after 2 iterations with a gap ratio of 0.97, which is false convergence.

## Do better results score higher? (hidden test)

| Variant | Before (red team) | After (rank, paired 95 % CI) | MM fail med / high | Degenerate fail med / high |
|---|---:|---:|---|---|
| Reference ODYN | 0 | 0 | 20.8 / 20.8 % | 5.6 / 8.3 % |
| **Better:** twice the iteration cap (6000 / 10000) | **−334.60** | **+8.40** [2.3, 16.7], P(≤ 0) = 0.001 | 13.9 / 15.3 % | 0.0 / 8.3 % |
| **Weaker:** 30-iteration cap | — | **−41.37** [−56.4, −27.1] | 50.0 / 52.8 % | 13.9 / 25.0 % |
| One iteration (red team's weak ablation) | **+271.89** | **−140.90** | 97.2 / 100 % | 100 / 100 % |
| OSQP baseline (eval-owned) | −176.78 | **−35.97** [−55.0, −15.5] | 47.2 / 44.4 % | 2.8 / 33.3 % |

- The red team's attempted regularization tweak (`rho=1e-7`, −12.48 before) was not rerun.
- The confidence intervals come from a paired bootstrap over test problems: each Maros–Meszaros problem with both of its hidden draws, and each degenerate instance, with every method seeing identical instances.
- The better variant reuses the reference's deterministic output wherever the reference stopped before its cap, and recomputes only the capped runs. This is the same device the red team used.

## Shortcuts: fix and score before → after

Each probe was registered as a solver in an isolated copy of the workspace and scored by the unmodified `bash scripts/evaluate_test.sh` with no arguments (`scripts/hardening/cases.py`, `wrap_solver.py`). In every case the reference's own scores inside that run were unchanged.

| Shortcut | Fix | Before | After |
|---|---|---:|---:|
| Success flags: claim success with no solution | success = evaluator's own check of (x, y, z) | +383.62 | **−142.70** |
| Visible cache: replay public outcomes or solutions | hidden perturbed instances; verification. Probe replays the reference's own solutions of the public unperturbed problems, matched by dimensions | +378.25 | **−131.69** (88.9 / 91.7 % failures) |
| Replace the problem loader | eval-owned loader, SHA-256-pinned `.mat` files, instances handed to the solver | +383.46 | **scoring aborts** (an altered `QAFIRO.mat` makes `evaluate_test.sh` exit 1 with no scores written) |
| Negative iteration cap / zero cap, all fail | no iteration metrics; fixed denominator | +162773.12 / +273.12 | **−142.70** (writes nothing) |
| One-iteration run (all fail, cheap) | same | +271.89 | **−140.90** |
| Hide failures as "skipped" | every manifest instance counts | +21.85 | **0.00** (identical to reference) |
| Drop degenerate outcomes | degenerate family generated and scored by eval | +2.37 (tie; experiment unscored) | **−59.19** (refusing degenerate-looking instances fails them) |
| Fake iteration counts | iterations unscored | — | **0.00** |
| Move / corrupt the baseline | baseline owned by `eval/`; `baseline/` is unused | +2.37 (tie) | not rerun; nothing a candidate controls feeds the baseline |
| Pre-write `scores_test.json` | evaluator deletes stale scores and rewrites them | +2.37 (tie) | **0.00** (forged file overwritten) |

## Noise

- **Seeds.** The solver and the instance generation are deterministic; seeds are fixed in the manifests and package versions are pinned.
- **Run-to-run.** An uncached rerun of the reference on the hidden test, on another node, flipped 4 of 216 outcomes: QBORE3D d0 medium, QETAMACR d0 medium and high, and QFORPLAN d1 high. Two went each way, so the net rank change was 0.0. The same 4 boundary instances flipped in the previous job too. They come from floating-point differences between nodes near the CPU budget; one path converges in about 2 CPU-s, another runs into the 120 s limit. Worst case, if all four went one way, is about ±3 rank points.
- **Test sampling.** Splitting the hidden test in half (draw 0 vs draw 1; even vs odd degenerate instances) gives a half-vs-half rank difference of −5.3, so the full test's sampling SD is about 2.6.
- **The paper's effect** (ODYN vs OSQP, 36.0 rank points, CI [15.5, 55.0]) and the better variant (+8.40, CI excluding 0) both exceed this noise.

## Reference score before → after

| | Before (old scorer) | After (verified) |
|---|---|---|
| Hidden-test reference | 16.7 / 22.2 % failures among 36 *attempted* of 69; mean iterations 1715 / 2990 | 20.8 / 20.8 % failures over all 72 instances; degenerate 5.6 / 8.3 % |
| Paper-level, unperturbed (`scores.json`) | 16.4 / 31.5 % of 73 attempted, with 65 skipped | 21.9 / 26.0 % (OSQP 41.1 / 42.5 %); the paper's three degenerate QPs are all solved by both |
| Train | 16.2 / 40.5 % of 37 attempted | 20.3 / 25.7 %; degenerate 5.1 / 12.8 % |

The reproduced ODYN fails about twice as often as the paper's C++ solver (9.7 / 15.5 % on its 103-problem subset), while the ODYN-vs-OSQP gap reproduces. Because the absolute level is not on the paper's scale, Table III is kept under `_paper_results` in `scoring/reference.json`, and `results` holds this gym's paper-level reproduction.

## Headroom

No scored reference metric is at its bound of 0 %: 20.8, 20.8, 5.6 and 8.3 %. The honest better variant raises the score by +8.40, beyond the noise, and the only metric it drives to the bound is degenerate medium. Nothing new was needed for headroom. The previously declared but unscored degenerate experiment is now implemented as a hidden generated family, and it is where OSQP's high-accuracy fragility shows: 33.3 % vs 8.3 %.

## Weights

Experiment weights are unchanged: 0.65 for Maros–Meszaros (Table III) and 0.35 for degenerate (Table IV). Within the degenerate experiment, high accuracy is now primary with coefficient 1.0, and medium has 0.7. At 1e-6 the family barely separates solvers (train: reference and OSQP both fail 2 / 39), while at 1e-9 it exposes the numerical fragility that the paper's degenerate study is about.

## Shortcuts left open

1. **Multiplier inflation on implicitly tight constraints.** Eq. (52)'s relative scales grow with ‖z‖. The gap guard catches inflation whenever it shifts the duality gap, such as box pairs or equality/inequality pairs with different right-hand sides. Constraints that are always tight (equal right-hand sides) can still be inflated without moving the gap. Closing this needs a stricter test, which rejects honest non-interior solutions as shown above. The grader should flag fabricated multipliers.
2. **Relative tolerances on problems with huge finite bounds.** These are lax because they follow the paper's definition (scales include ‖s‖, ‖h‖).
3. **Instance recognition.** The test's base problems are public Maros–Meszaros problems (the complement of train within the 73). Perturbations stop answer replay (−131.7), but not per-problem settings chosen by matching dimensions. Out of bounds per `scoring/DIRECTION.md`.
4. **Calling another QP solver inside a registered solver.** Out of bounds per `scoring/DIRECTION.md`, and nothing extra is pre-installed.
5. **Escaping the CPU budget with child processes.** The limit is per process; a 1200 s wall backstop and per-solver total accounting bound it.
6. **The fixed hidden seed.** Every attempt sees the same hidden instances. This relies on the hidden-test job's filesystem not persisting between attempts.

## Not fixed / not covered

- **Warm-start experiment (paper Fig. 4).** The warm-to-cold iteration ratio is not reproduced or scored; iteration counts are unverifiable. The same holds for iteration and runtime performance profiles (Fig. 3) and the Table IV iteration counts. Those are kept under `_paper_table_iv_iterations`.
- **Absolute level.** The reproduced reference fails about twice as often as the paper's C++ solver, and the 65 large Maros–Meszaros problems are out of scope.
- **Degenerate family at medium accuracy.** OSQP is level with ODYN or slightly better (test 2.8 vs 5.6 %, train 5.1 vs 5.1 %). The paper's direction holds at high accuracy and in the experiment as a whole.
- **Soft validator warning.** `validate.py` warns that `eval/*/evaluate.py` generates data. That is by design: the evaluator generates hidden instances and then reads the method's outputs.
