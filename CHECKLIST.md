# Reproduction Checklist

## Briefing
- [x] `briefing/problem.md` (method-agnostic)
- [x] `briefing/evaluation.md` (method-agnostic)
- [x] `briefing/method.md`
- [x] `briefing/overview.md`

## Scoring
- [x] `scoring/reference.json` — paper's reported numbers
- [x] Workspace validated via `python validate.py`
- [x] `scoring/scores.json` — current reproduced numbers
- [x] `scoring/TARGETS.md`
- [x] `scoring/CONSTRAINTS.md`
- [x] `scoring/DIRECTION.md`

## Code
- [x] Evaluation code in `eval/`
- [x] Method implementation in `method/`
- [x] Baseline implementation in `baseline/`

## Scripts
- [x] `scripts/evaluate.sh`
- [x] `scripts/reproduce.sh`
- [x] `scripts/download.sh`
- [x] `scripts/baseline.sh`

## Environment
- [x] `environment/container.def` + `environment/setup.sh`

## Data
- [x] Dataset acquired in `data/`
- [x] No pretrained models required

## Milestones
- [x] `method_runs` — executes end-to-end without errors
- [x] `core_claim` — minimum experiment supports central claim
- [x] `core_claim_plus` — additional settings
- [x] `secondary_claims`
- [ ] `majority`
- [ ] `near_complete`
- [ ] `full`
