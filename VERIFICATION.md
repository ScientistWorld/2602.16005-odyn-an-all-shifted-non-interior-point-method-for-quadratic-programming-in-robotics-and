> **Superseded (hardening iteration, 2026-11-09):** the evaluation described below (scoring raw result files by their self-reported success flags, iteration counts and attempted counts) was replaced. The evaluators now run the registered solvers themselves on evaluator-built instances and verify every returned point. See `HARDENING.md` and `briefing/evaluation.md`.

# Verification Report

## Initial Assessment
The workspace had a historical `secondary_claims` log entry, but the active `MILESTONES.md` header had already been corrected to `core_claim_plus`. That correction is justified: the implemented solver is the paper's actual ODYN-style QP algorithm rather than a surrogate, and the core robustness claim is supported against OSQP on the packaged benchmark artifacts, but the paper's warm-start WCR secondary claim is documented and not yet reproduced or scored.

## Issues Found
- Critical: the prior verification report still claimed `secondary_claims`, conflicting with the active milestone and the missing warm-start WCR experiment.
- Minor: `scripts/evaluate.sh` defaulted to a temporary result path, so standalone evaluation could fail on a clean checkout even though packaged raw artifacts exist.
- Minor: `briefing/evaluation.md` named the proposed solver in a method-agnostic problem-definition file.
- Minor: `scoring/DIRECTION.md` used a narrower solver-family phrase than necessary for a method-safe direction document.
- Cosmetic: ignored container artifacts remain under `environment/`, and unrelated root/system files are dirty in git. They are ignored or outside this verification change and were left untouched.

## Fixes Applied
- Rewrote this verification report to align with `core_claim_plus` and document why `secondary_claims` is not claimed.
- Updated `eval/benchmark.py`, `eval/train/evaluate.py`, `eval/test/evaluate.py`, and `scripts/evaluate.sh` so standalone scoring discovers `scoring/raw_results/*.json` before falling back to `tmp/results/*.json`.
- Removed the proposed-solver target table from `briefing/evaluation.md` and replaced it with neutral scoring guidance.
- Generalized `scoring/DIRECTION.md` to describe numerical QP solver research without exposing a paper-specific algorithm family.
- Verified the dataset archive URL with `curl -I -L --max-time 15`; it resolves to a 200 `application/zip` response from GitHub codeload.

## Final Judgment
The workspace is ready to serve as a partial but meaningful research gym. Improve-mode agents can build on the checked-in ODYN implementation and raw artifacts; from-scratch agents can use the method-agnostic problem, data, and evaluation files without seeing the solver design. The scoring contract measures robustness benefits and coverage/convergence constraints, avoids wall-clock metrics and reproduction-error metrics, and `scripts/evaluate.sh` now works standalone from packaged artifacts.

Validation passed with `python3 validate.py --compare`. Lightweight syntax checks also passed for the touched Python and shell files.

- Milestone: core_claim_plus
- Ready for gym use: partial
- Confidence: medium
- Key limitation: warm-start WCR and other secondary paper experiments remain unreproduced, so the gym currently covers failure-rate robustness and degenerate-case diagnostics only.
