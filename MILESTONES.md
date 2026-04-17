# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-04-17] - none
- Initial workspace audit: reviewing existing code and results

### [2026-04-17] - core_claim_plus
- ODYN Python implementation verified: all-shifted NCP functions, proximal primal-dual regularization, condensed KKT system with Cholesky
- Evaluated on 29-problem subset of Maros-Meszaros benchmark
- ODYN failure rate: 10.3% (medium 1e-6), 13.8% (high 1e-9) vs paper 9.7%/15.5%
- OSQP baseline: 41.4% failure rate at both tolerances vs paper 44.7%/49.5%
- Degenerate problems evaluated: redundant_ineq=6, licq_failure=3, multiple_solutions=9 (vs paper 5/10/6)
- All structural checks pass: import separation, no shared/ references, eval/method independence
- Environment is fully functional and reusable

### [2026-04-17] - core_claim_plus (running full benchmark)
- Submitting full 138-problem benchmark run to get results closer to paper's numbers
- Previous 29-problem results already demonstrate core claim
