"""Build small audit evidence after the bundled computational job."""
import json
from pathlib import Path
from harness import CASES
from rank import rank, REFERENCE, COEFFICIENTS

ROOT = Path(__file__).resolve().parent
results = {}
for case in CASES:
    path = ROOT / case / 'summary.json'
    if path.exists(): results[case] = json.loads(path.read_text())
seeds = [results[f'reference_seed_{i}']['rank_improvement'] for i in range(3)
         if f'reference_seed_{i}' in results]
summary = {'results': results,
           'seed_rank_range': [min(seeds), max(seeds)] if seeds else [],
           'seed_rank_spread': max(seeds) - min(seeds) if seeds else None,
           'seed_count': len(seeds),
           'rank_formula': 'sum_experiment weight * sum_metric abs(coefficient) * directional(candidate-reference)',
           'reference_test': REFERENCE['experiments'],
           'bounds': {'failure_rate_medium': [0, 100], 'failure_rate_high': [0, 100],
                      'mean_iterations_medium': [0, None], 'mean_iterations_high': [0, None],
                      'attempted_count': [0, 69]},
           'reference_metrics_at_best_bound': [],
           'implemented_iteration_lower_bound': 'unbounded: raw metadata.max_iter accepts negative numbers',
           'declared_but_unscored_experiment': 'degenerate_problems',
           'declared_but_unscored_weight': 0.35}
(ROOT / 'audit_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
lines = ['# Job evidence', '', '| Run | Rank gain | Medium fail % | High fail % | Medium iterations | High iterations | Coverage |',
         '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
for case, result in results.items():
    m = result['metrics']
    lines.append(f"| {case} | {result['rank_improvement']:.6f} | {m.get('failure_rate_medium', float('nan')):.6f} | {m.get('failure_rate_high', float('nan')):.6f} | {m.get('mean_iterations_medium', float('nan')):.6f} | {m.get('mean_iterations_high', float('nan')):.6f} | {m.get('attempted_count', float('nan')):g} |")
lines += ['', f'Seed count: {len(seeds)}; rank range: {summary["seed_rank_range"]}; spread: {summary["seed_rank_spread"]}.']
(ROOT / 'REPORT_DRAFT.md').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
