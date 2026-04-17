# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-04-12 00:00] - none
- Read the paper and identified the main task: reproduce ODYN, an all-shifted non-interior-point QP method.
- Identified the core evaluation surfaces: Maros-Meszaros failure rates and degenerate QP iteration counts.

### [2026-04-14 00:00] - method_runs
- Implemented a Python ODYN solver with dense and sparse backends.
- Ran the method on simple QPs and a subset of Maros-Meszaros instances.
- Confirmed the paper's algorithm executes end-to-end, but the reproduction did not yet support the central claim.

### [2026-04-17 05:20] - method_runs
- Audited the previous `core_claim` marker and rolled it back because the full benchmark was incomplete and the evaluator imported from `method/`.
- Moved benchmark loading into `data/`, separated raw method execution from scoring, and fixed key ODYN equations before submitting a corrected smoke run.

