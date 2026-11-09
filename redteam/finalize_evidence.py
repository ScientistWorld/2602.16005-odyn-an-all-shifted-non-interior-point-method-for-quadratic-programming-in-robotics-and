"""Lightweight, auditor-only checks of the completed job's saved JSON files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from harness import CASES
from rank import rank

AUDIT = Path(__file__).resolve().parent
FIX = AUDIT / 'fixtures'


def read(path):
    return json.loads(path.read_text())


def raw(case, label):
    return read(AUDIT / case / 'artifacts' / f'{label}.json')


def records(case, label):
    return {item['name']: item for item in raw(case, label)['benchmark']}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    names = read(FIX / 'eval/test/problem_names.json')['problem_names']
    summaries = {case: read(AUDIT / case / 'summary.json') for case in CASES}
    checks = {}
    for case in CASES:
        folder = AUDIT / case
        score = read(folder / 'scores_test.json')
        assert rank(score)['rank_improvement'] == summaries[case]['rank_improvement']
        assert summaries[case]['test_command'] == 'bash scripts/evaluate_test.sh'
        assert summaries[case]['test_command_arguments'] == []
        for filename, expected in summaries[case]['raw_sha256'].items():
            assert digest(folder / 'artifacts' / filename) == expected
        hashes = {}
        for rel, source in (
            ('scripts/evaluate_test.sh', FIX / 'scripts/evaluate_test.sh'),
            ('eval/test/evaluate.py', FIX / 'eval/test/evaluate.py'),
            ('eval/test/problem_names.json', FIX / 'eval/test/problem_names.json'),
            ('eval/train/evaluate.py', FIX / 'eval/train/evaluate.py'),
        ):
            actual = digest(folder / 'workspace' / rel)
            assert actual == digest(source), (case, rel)
            hashes[rel] = actual
        checks[case] = {'rank_recomputed': True, 'raw_hashes_match': True,
                        'pristine_evaluator_sha256': hashes}

    seeds = []
    for seed in range(3):
        case = f'reference_seed_{seed}'
        log = (AUDIT / case / 'artifacts/method.log').read_text()
        commands = [line for line in log.splitlines() if line.startswith('COMMAND ')]
        assert commands and all(f'random.seed({seed})' in line for line in commands)
        seeds.append({'seed': seed, 'rank_improvement': summaries[case]['rank_improvement'],
                      'metrics': summaries[case]['metrics'], 'commands': commands,
                      'raw_sha256': summaries[case]['raw_sha256'],
                      'metadata': {label: raw(case, label)['metadata'] for label in ('medium', 'high')}})
    metric_ranges = {metric: [min(s['metrics'][metric] for s in seeds),
                              max(s['metrics'][metric] for s in seeds)]
                     for metric in seeds[0]['metrics']}

    stronger, reproduction, historical_differences = {}, {}, {}
    for label in ('medium', 'high'):
        old = records('reference_seed_0', label)
        new = records('stronger_more_iterations', label)
        gained = [name for name in names if new[name]['success'] and not old[name]['success']]
        lost = [name for name in names if old[name]['success'] and not new[name]['success']]
        assert gained and not lost
        stronger[label] = {
            'new_successes': [{key: {'before': old[name].get(key), 'after': new[name].get(key)}
                               for key in ('name', 'status', 'iterations', 'primal_residual', 'dual_residual')}
                              for name in gained],
            'lost_successes': lost,
            'reference_seed_0_success_count': sum(old[n]['success'] for n in names),
            'stronger_success_count': sum(new[n]['success'] for n in names),
        }
        odyn = records('packaged_reference', label)
        historical_differences[label] = [
            {'name': name, 'packaged': {key: odyn[name].get(key) for key in ('status', 'success', 'iterations')},
             'fresh_seed_0': {key: old[name].get(key) for key in ('status', 'success', 'iterations')}}
            for name in names
            if (odyn[name]['success'], odyn[name]['iterations']) != (old[name]['success'], old[name]['iterations'])
        ]
        osqp = records('packaged_reference', f'osqp_{label}')
        common = [n for n in names if odyn[n].get('attempted', True) and osqp[n].get('attempted', True)]
        reproduction[label] = {'common_attempted_count': len(common)}
        for method, result in (('odyn', odyn), ('osqp', osqp)):
            failed = sum(not result[n]['success'] for n in common)
            succeeded = sum(result[n]['success'] for n in names)
            reproduction[label][method] = {
                'common_failed_count': failed,
                'common_failure_percent': 100 * failed / len(common),
                'full_test_success_count': succeeded,
                'full_test_count': len(names),
                'full_test_failure_percent_counting_skips': 100 * (len(names) - succeeded) / len(names),
            }

    # Verify the principal quality inversion without importing solver libraries.
    weak = summaries['shortcut_low_budget_weak_variant']
    better = summaries['stronger_more_iterations']
    assert weak['metrics']['failure_rate_medium'] == weak['metrics']['failure_rate_high'] == 100
    assert weak['rank_improvement'] > summaries['reference_seed_0']['rank_improvement']
    assert better['rank_improvement'] < summaries['reference_seed_0']['rank_improvement']
    for label in ('medium', 'high'):
        assert raw('shortcut_low_budget_weak_variant', label)['metadata']['max_iter'] == 1
    for case in ('shortcut_ignore_degenerate', 'shortcut_move_baseline', 'shortcut_write_scores_only'):
        assert summaries[case]['metrics'] == summaries['reference_seed_0']['metrics']

    evidence = {
        'completed_cases': len(CASES), 'case_checks': checks,
        'seed_runs': seeds, 'seed_metric_ranges': metric_ranges,
        'seed_rank_spread': max(s['rank_improvement'] for s in seeds) - min(s['rank_improvement'] for s in seeds),
        'stronger_more_iterations': stronger, 'reproduction_check': reproduction,
        'historical_reference_differences': historical_differences,
        'quality_inversion_verified': True,
        'more_iterations_fixed_skip_penalty_increase': 0.65 * (0.15 * 33 / 69 * 3000 + 0.1 * 33 / 69 * 5000),
    }
    (AUDIT / 'verification.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'Checked {len(CASES)} completed cases, three independent seed command traces, and all evaluator hashes.')
    print(json.dumps({'stronger': stronger, 'reproduction': reproduction}, indent=2))


if __name__ == '__main__':
    main()
