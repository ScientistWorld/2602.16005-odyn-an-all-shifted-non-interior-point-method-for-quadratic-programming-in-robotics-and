"""Compare scoring-only fresh-job results with the earlier per-case scores."""
import hashlib
import json
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
results = {}
for script in sorted(AUDIT.glob('*/run.sh')):
    folder = script.parent
    original = (folder / 'scores_test.json').read_bytes()
    fresh = (folder / 'scores_test_fresh_job.json').read_bytes()
    assert original == fresh, folder.name
    results[folder.name] = {
        'byte_identical': True,
        'scores_test_sha256': hashlib.sha256(fresh).hexdigest(),
        'test_command': 'bash scripts/evaluate_test.sh',
        'test_command_arguments': [],
        'rank_improvement': json.loads((folder / 'summary.json').read_text())['rank_improvement'],
    }
assert len(results) == 16
output = {'case_count': len(results), 'all_scores_identical': True,
          'job_script': 'redteam/evaluate_fresh_job.sh',
          'purpose': 'Scoring-only job submitted after the solver/candidate job exited; no candidate process survives.',
          'results': results}
(AUDIT / 'fresh_job_verification.json').write_text(json.dumps(output, indent=2) + '\n')
print(f'All {len(results)} saved submissions have identical scores in the fresh scoring-only job.')
