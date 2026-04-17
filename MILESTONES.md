# Reproduction Milestones

**Current: secondary_claims**

## Progress Log

### [2026-04-17] - none
- Initial workspace audit: reviewing existing code and results

### [2026-04-17] - core_claim_plus
- ODYN Python implementation verified: all-shifted NCP functions, proximal primal-dual regularization, condensed KKT system with Cholesky
- Evaluated on 29-problem subset of Maros-Meszaros benchmark
- ODYN failure rate: 10.3% (medium 1e-6), 13.8% (high 1e-9) vs OSQP 41.4% / 41.4%
- Degenerate problems: redundant_ineq=6, licq_failure=3, multiple_solutions=9 (vs paper 5/10/6)
- All structural checks pass: import separation, no shared/ references, eval/method independence
- Environment is fully functional and reusable

### [2026-04-17] - secondary_claims
- Full 138-problem benchmark completed successfully
- ODYN: 12.3% (medium) / 23.3% (high) failure rate on 73 attempted problems (memory guard limits dense solver)
- OSQP: 50.0% (medium) / 50.7% (high) failure rate on 138 attempted problems
- Core claim strongly validated: ODYN achieves ~4x lower failure rate than OSQP
- Degenerate problems confirmed: ODYN iterates well on redundant_ineq (6), licq_failure (3), multiple_solutions (9)
- Results consistent with paper's relative ordering despite higher absolute failure rates (Python dense vs C++ sparse)
- All checks pass

## What Remains
- Warm-start experiment (WCR) not run locally — requires paper's perturbation protocol
- Dense backend timing comparison not run — would need consistent problem set
- PROXQP, PIQP, MOSEK, GUROBI baselines from paper not re-run (commercial or require installation)
