# Evaluation

This page defines how a candidate convex-QP solver is evaluated. It describes the task, the solver interface, and the metrics; solver design choices belong elsewhere.

## What is scored

The evaluator runs your solver itself on instances it constructs, checks every returned point with its own residual computation, and reports **failure rates**. Lower is better.

| Experiment | Metric | Meaning |
|---|---|---|
| `failure_rate_comparison` | `failure_rate_medium` (primary), `failure_rate_high` | % of Maros–Meszaros instances without a verified solution at tolerance 1e-6 / 1e-9 |
| `degenerate_problems` | `degenerate_failure_rate_high` (primary), `degenerate_failure_rate_medium` | % of degenerate instances without a verified solution at 1e-9 / 1e-6 |

Every instance in the fixed manifest is in the denominator. A missing, unreadable, wrongly shaped, or non-finite output counts as a failure, as do a crash and an over-budget run. Status strings, iteration counts, or residuals written by the solver are never used for scoring. Wall-clock time is not scored.

## Instances

The evaluator loads each problem as `minimize 1/2 x'Qx + c'x subject to Ax = b, Gx <= h`, with Q symmetric positive semidefinite.

- **Maros–Meszaros**: the subset of the standard test set whose data fit in 2 GB as dense arrays with at most 1000 variables (73 problems). The problems are split into a visible train slice (37) and a held-out test slice (36), balanced for difficulty. Variable bounds are explicit inequality rows, and fixed variables become equality rows. The `.mat` files are checked against pinned SHA-256 hashes; altered data aborts scoring.
  - The train slice scores each problem as published plus one small perturbation.
  - The test slice scores two hidden perturbations of each problem.
  - Perturbations are masked relative changes (at most min(10%, 20) entries): of the cost vector, an only-increasing change to positive Hessian diagonal entries, and an only-relaxing change to inequality right-hand sides. Feasibility and convexity are preserved.
- **Degenerate QPs**: generated families with a known degenerate optimum. There are 12 instances of each kind, n ∈ {8, 16, 32, 64}; the test family uses a hidden seed. The train slice also includes the three small degenerate examples from the source paper. The three kinds are:
  - redundant active inequalities (duplicated, rescaled, and looser parallel copies; more active rows than variables; weakly active constraints);
  - constraint-qualification failure (equality rows repeated as inequalities and duplicated, variables pinned at active bounds, cost data spanning many orders of magnitude);
  - non-unique solutions (positive-semidefinite Hessian with a flat optimal face, plus always-active zero rows `0'x <= 0`).

## Success test

For tolerance ε ∈ {1e-6, 1e-9}, the returned point (x, y, z) is checked with slack s = h − Gx. Norms are ∞-norms; the absolute and relative tolerances are both ε.

- equality residual: ‖Ax − b‖ ≤ ε (1 + max(‖Ax‖, ‖b‖))
- stationarity: ‖Qx + c + Aᵀy + Gᵀz‖ ≤ ε (1 + max(‖Qx‖, ‖c‖, ‖Aᵀy‖, ‖Gᵀz‖))
- complementarity (also enforces inequality feasibility and z ≥ 0): ‖min(s, z)‖ ≤ ε (1 + max(‖s‖, ‖z‖))
- relative duality gap: |xᵀQx + cᵀx + bᵀy + hᵀz| ≤ √ε (1 + max(|xᵀQx|, |cᵀx|, |bᵀy + hᵀz|))

## Budget

Each solve gets **120 CPU-seconds**. The solver process and its threads are limited with `ulimit -t`, BLAS thread variables are set to 1, and there is a generous wall-clock backstop. Each solver also gets **7200 CPU-seconds in total** per evaluation; instances that remain after this is exhausted count as failures.

## Solver contract

Register a solver by adding an executable `scripts/solvers/<name>.sh`. Its file stem is the method name in every scores file; `osqp` is reserved for the evaluator's baseline. The evaluator calls it once per instance and tolerance, with the workspace root as working directory:

```
bash scripts/solvers/<name>.sh --problem INSTANCE.npz --output SOLUTION.npz --tol TOL
```

- `INSTANCE.npz` holds `n, m, p`; CSC arrays `Q_data/Q_indices/Q_indptr` (n×n); `A_*` (m×n) and `G_*` (p×n); and vectors `c, b, h`.
- The solver writes `SOLUTION.npz` with `x` (n), `y` (m), `z` (p), using the sign convention `Qx + c + Aᵀy + Gᵀz = 0`, `z ≥ 0`.
- Extra entries such as `iterations` or `status` are kept as unscored diagnostics.
- `data/qp_format.py` reads and writes this format.
- Instances are anonymous files. The tolerance is the only other input, and nothing else about the instance is passed.

## Running

```
bash scripts/evaluate_train.sh       # visible train slice   -> scoring/scores_train.json
bash scripts/evaluate.sh             # published problems     -> scoring/scores.json
bash scripts/evaluate_test.sh        # held-out slice (hidden) -> scoring/scores_test.json
```

Each run scores every registered solver plus the baseline: OSQP with fixed settings (eps_abs = eps_rel = ε; 4000 / 8000 iterations). `--solvers NAME ...` restricts a development run. Per-instance outcomes, including residual ratios and failure reasons, are written to `tmp/eval_runs/<slice>/outcomes.jsonl`. The optional `QP_GYM_EVAL_CACHE=<dir>` reuses raw outputs of unchanged solver code; scores are always recomputed from the raw outputs.

## Ranking

Methods are compared with the coefficients and weights in `scoring/reference.json`: 0.65 for the Maros–Meszaros experiment and 0.35 for the degenerate experiment. Within the Maros–Meszaros experiment high-accuracy failures count 0.7 as much as medium; within the degenerate experiment medium-accuracy failures count 0.7 as much as high. Improvements are taken in each metric's better direction.
