#!/usr/bin/env python3
"""Audit driver: candidates see only the supplied future-agent view."""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from rank import rank

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parent
FIX = AUDIT / 'fixtures'
BASE = 'reference_seed_0'
CASES = [
    'packaged_reference',
    BASE,
    'shortcut_low_budget_weak_variant',
    'stronger_regularization',
    'stronger_more_iterations',
    'reference_seed_1',
    'reference_seed_2',
    'shortcut_success_flags',
    'shortcut_visible_cache',
    'shortcut_hide_failures',
    'shortcut_negative_cap',
    'shortcut_zero_cap_all_fail',
    'shortcut_ignore_degenerate',
    'shortcut_replace_problem_loader',
    'shortcut_move_baseline',
    'shortcut_write_scores_only',
]

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=True) + '\n')
    temp.replace(path)

def copy_tree(source, dest):
    shutil.copytree(source, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

def visible_workspace(case):
    out = AUDIT / case
    work = out / 'workspace'
    # Resume raw outputs after a preemption. Evaluator files are installed only
    # after the candidate has finished producing its file-only submission.
    if not (work / 'method/run_odyn.py').exists():
        copy_tree(FIX / 'reference_method', work / 'method')
        copy_tree(FIX / 'baseline', work / 'baseline')
        copy_tree(FIX / 'data', work / 'data')
        copy_tree(ROOT / 'briefing', work / 'briefing')
        (work / 'environment').mkdir(parents=True, exist_ok=True)
        for name in ('setup.sh', 'container.def'):
            shutil.copy2(ROOT / 'environment' / name, work / 'environment' / name)
        dataset = work / 'data/maros_meszaros_qpbenchmark'
        if not dataset.exists():
            dataset.symlink_to(ROOT / 'data/maros_meszaros_qpbenchmark', target_is_directory=True)
        (work / 'scoring').mkdir(parents=True, exist_ok=True)
        for name in ('TARGETS.md', 'CONSTRAINTS.md', 'DIRECTION.md', 'EXPERIMENTS.md'):
            shutil.copy2(FIX / 'scoring' / name, work / 'scoring' / name)
        (work / 'scripts').mkdir(parents=True, exist_ok=True)
        for name in ('evaluate_train.sh', 'baseline.sh', 'download.sh'):
            shutil.copy2(FIX / 'scripts' / name, work / 'scripts' / name)
        copy_tree(FIX / 'eval/train', work / 'eval/train')
    shutil.rmtree(work / 'eval/test', ignore_errors=True)
    (work / 'scripts/evaluate_test.sh').unlink(missing_ok=True)
    (work / 'tmp/results').mkdir(parents=True, exist_ok=True)
    (out / 'artifacts').mkdir(parents=True, exist_ok=True)
    return out, work

def run(cmd, work, log, *, seed=0):
    env = os.environ.copy()
    # The numerical method is deterministic. Seeds are set afresh in the runner.
    # Limit BLAS oversubscription for a single-process CPU solver experiment.
    env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with log.open('a') as handle:
        handle.write('\nCOMMAND ' + repr(cmd) + '\n'); handle.flush()
        subprocess.run(cmd, cwd=work, env=env, stdout=handle, stderr=subprocess.STDOUT, check=True)

def solve(work, out, *, seed=0, caps=(3000, 5000), extra=(), resume=True):
    # Run the supplied visible method in a fresh interpreter for each tolerance.
    launch = ('import random, numpy as np, runpy, sys; '
              f'random.seed({seed}); np.random.seed({seed}); '
              'sys.argv=["method.run_odyn"]+sys.argv[1:]; '
              'runpy.run_module("method.run_odyn", run_name="__main__")')
    for label, tol, cap in zip(('medium', 'high'), ('1e-6', '1e-9'), caps):
        cmd = [sys.executable, '-c', launch, '--rtol', tol, '--max-iter', str(cap),
               '--timeout', '300', '--output', f'tmp/results/{label}.json']
        if resume: cmd += ['--resume']
        if label == 'high': cmd += ['--skip-degenerate']
        cmd += list(extra)
        run(cmd, work, out / 'artifacts/method.log', seed=seed)

def reference_outputs():
    folder = AUDIT / BASE / 'artifacts'
    return {label: json.loads((folder / f'{label}.json').read_text())
            for label in ('medium', 'high')}

def write_raws(work, raws):
    for label, raw in raws.items():
        save(work / 'tmp/results' / f'{label}.json', raw)

def raw_template(label, cap=3000):
    return {'method': 'odyn', 'metadata': {'rtol': 1e-9 if label == 'high' else 1e-6,
                                         'max_iter': cap},
            'benchmark': [], 'degenerate': {}}

def candidate(case, work, out):
    """Candidate preparation: never reads hidden test names or score fixtures."""
    data = work / 'data/maros_meszaros_qpbenchmark/data'
    names = sorted(path.stem for path in data.glob('*.mat'))
    if case == 'packaged_reference':
        # Auditor-only measurement of the originally supplied results.
        for label in ('medium', 'high'):
            shutil.copy2(ROOT / 'scoring/raw_results' / f'odyn_full_{label}.json',
                         work / f'tmp/results/{label}.json')
            shutil.copy2(ROOT / 'scoring/raw_results' / f'osqp_full_{label}.json',
                         work / f'tmp/results/osqp_{label}.json')
        return
    if case.startswith('reference_seed_'):
        solve(work, out, seed=int(case.rsplit('_', 1)[-1]))
        return
    if case == 'shortcut_low_budget_weak_variant':
        # Shortcut and honest resource ablation: actually run ODYN for one
        # iteration, with unmodified success/attempted/iteration fields.
        solve(work, out, caps=(1, 1))
        return
    if case == 'stronger_regularization':
        solve(work, out, extra=('--rho', '1e-7', '--rho-min', '1e-12'))
        return
    if case == 'stronger_more_iterations':
        # Reuse deterministic successful runs, and extend every failed attempted
        # instance. This exactly reproduces the longer-budget run's successful
        # paths, without paying to recompute successful paths.
        for label, raw in reference_outputs().items():
            cap = 6000 if label == 'medium' else 10000
            target = work / f'tmp/results/{label}.json'
            if target.exists():
                continue
            raw['metadata']['max_iter'] = cap
            raw['metadata']['data_dir'] = str(work / 'data/maros_meszaros_qpbenchmark/data')
            raw['benchmark'] = [item for item in raw['benchmark']
                                if item.get('success') or not item.get('attempted', True)]
            save(work / f'tmp/results/{label}.json', raw)
        solve(work, out, caps=(6000, 10000))
        return
    if case == 'shortcut_success_flags':
        # Shortcut: emit no solutions and impossible residuals, claim success.
        for label in ('medium', 'high'):
            raw = raw_template(label, 5000 if label == 'high' else 3000)
            raw['benchmark'] = [dict(name=name, success=True, attempted=True,
                                     iterations=0, solve_time=-1, x=None,
                                     primal_residual=float('inf'), dual_residual=float('inf'),
                                     status='shortcut_no_solver') for name in names]
            save(work / f'tmp/results/{label}.json', raw)
        return
    if case == 'shortcut_visible_cache':
        # Shortcut: public outcome cache shipped under visible data/. No QP is
        # solved and no hidden manifest or reference raw artifact is accessed.
        with (work / 'data/maros_meszaros_qpbenchmark/results/qpbenchmark_results.csv').open() as h:
            rows = list(csv.DictReader(h))
        for label, setting in (('medium', 'mid_accuracy'), ('high', 'high_accuracy')):
            cached = {r['problem'] for r in rows if r['settings'] == setting and r['found'] == 'True'}
            raw = raw_template(label, 5000 if label == 'high' else 3000)
            raw['benchmark'] = [dict(name=name, success=name in cached, attempted=True,
                                     iterations=0, x=None, status='shortcut_public_cache') for name in names]
            save(work / f'tmp/results/{label}.json', raw)
        return
    if case == 'shortcut_replace_problem_loader':
        # Shortcut: replace the shared problem-defining artifact; solve the
        # resulting trivial QPs honestly with the unchanged reference solver.
        (work / 'data/qplib.py').write_text('''"""Shortcut replacing the fixed problem loader."""
from pathlib import Path
import numpy as np
import scipy.sparse as spa
def estimated_dense_size_gb(problem): return 0.000001
def degenerate_cases(): return {}
def load_maros_meszaros_problem(path):
    return dict(name=Path(path).stem, Q=spa.eye(2, format="csc"), c=np.zeros(2),
                A=None, b=None, G=None, h=None)
''')
        solve(work, out)
        return
    if case == 'shortcut_zero_cap_all_fail' or case == 'shortcut_negative_cap':
        # Shortcut: solve nothing, truthfully mark all records failed, change
        # only the self-declared failed-problem cost. Negative cap is impossible.
        cap = 0 if case == 'shortcut_zero_cap_all_fail' else -1000000
        for label in ('medium', 'high'):
            raw = raw_template(label, cap)
            raw['benchmark'] = [dict(name=name, success=False, attempted=True,
                                     iterations=0, x=[], status='shortcut_no_solver') for name in names]
            save(work / f'tmp/results/{label}.json', raw)
        return
    raws = reference_outputs()
    if case == 'shortcut_hide_failures':
        for raw in raws.values():
            for item in raw['benchmark']:
                if item.get('attempted', not item['status'].startswith('skipped_')) and not item['success']:
                    item.update(attempted=False, status='skipped_shortcut_observed_failure')
    elif case == 'shortcut_ignore_degenerate':
        for raw in raws.values(): raw['degenerate'] = {}
    elif case == 'shortcut_move_baseline':
        for label, raw in raws.items():
            fake_baseline = copy.deepcopy(raw)
            fake_baseline['method'] = 'osqp'
            fake_baseline['metadata']['max_iter'] = 1000000
            for item in fake_baseline['benchmark']:
                item.update(success=False, attempted=True, iterations=1000000,
                            status='shortcut_degraded_baseline')
            save(work / f'tmp/results/osqp_{label}.json', fake_baseline)
    elif case == 'shortcut_write_scores_only':
        # Shortcut attempt: direct score overwrite, while keeping raw records
        # and the train-established raw file paths unchanged. Test replaces it.
        save(work / 'scoring/scores_test.json', {'experiments': {'failure_rate_comparison':
             {'results': {'odyn': {'failure_rate_medium': -1000000,
                                  'failure_rate_high': -1000000,
                                  'mean_iterations_medium': -1000000,
                                  'mean_iterations_high': -1000000,
                                  'attempted_count': 1000000}}}}})
    else:
        raise ValueError(case)
    write_raws(work, raws)

def evaluate(work, out):
    results = sorted(str(path.relative_to(work)) for path in (work / 'tmp/results').glob('*.json'))
    run(['bash', 'scripts/evaluate_train.sh', '--results', *results], work, out / 'artifacts/evaluate_train.log')
    # Put back the original hidden evaluator only after candidate production.
    copy_tree(FIX / 'eval/test', work / 'eval/test')
    shutil.copy2(FIX / 'scripts/evaluate_test.sh', work / 'scripts/evaluate_test.sh')
    # Exactly the scoring-time invocation specified by the audit: no arguments,
    # no background process, no imports from candidate code, file-only state.
    run(['bash', 'scripts/evaluate_test.sh'], work, out / 'artifacts/evaluate_test.log')
    for name in ('scores_train.json', 'scores_test.json'):
        shutil.copy2(work / 'scoring' / name, out / name)
    for path in (work / 'tmp/results').glob('*.json'):
        shutil.copy2(path, out / 'artifacts' / path.name)
    score = json.loads((out / 'scores_test.json').read_text())
    summary = rank(score)
    summary['metrics'] = score['experiments']['failure_rate_comparison']['results']['odyn']
    summary['test_command'] = 'bash scripts/evaluate_test.sh'
    summary['test_command_arguments'] = []
    summary['raw_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in (work / 'tmp/results').glob('*.json')}
    if 'osqp' in score['experiments']['failure_rate_comparison']['results']:
        summary['osqp_rank'] = rank(score, 'osqp')
    save(out / 'summary.json', summary)
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=CASES, required=True)
    args = parser.parse_args()
    out = AUDIT / args.case
    if (out / 'complete.json').exists():
        print(f'{args.case}: completed, saved rank=' + str(json.loads((out / 'summary.json').read_text())['rank_improvement']), flush=True)
        return
    start = time.time()
    out, work = visible_workspace(args.case)
    print(f'START {args.case}', flush=True)
    candidate(args.case, work, out)
    result = evaluate(work, out)
    save(out / 'complete.json', {'case': args.case, 'elapsed_seconds': time.time() - start,
                               'rank_improvement': result['rank_improvement']})
    print(f'DONE {args.case}: {result}', flush=True)

if __name__ == '__main__': main()
