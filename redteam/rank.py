"""Auditor-only additive ranking, using direction and ABS(coefficient)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REFERENCE = json.loads((ROOT / 'fixtures/scoring/scores_test.json').read_text())
COEFFICIENTS = json.loads((ROOT / 'fixtures/scoring/reference.json').read_text())

def rank(scores, method='odyn'):
    total, contributions = 0.0, {}
    for name, exp in COEFFICIENTS['experiments'].items():
        base = REFERENCE['experiments'].get(name, {}).get('results', {}).get('odyn', {})
        candidate = scores['experiments'].get(name, {}).get('results', {}).get(method, {})
        for metric, spec in exp['metrics'].items():
            if metric not in base or metric not in candidate:
                continue
            difference = candidate[metric] - base[metric]
            better = difference if spec['higher_is_better'] else -difference
            value = exp['weight'] * abs(spec['coefficient']) * better
            contributions[f'{name}/{metric}'] = value
            total += value
    return {'rank_improvement': total, 'contributions': contributions}
