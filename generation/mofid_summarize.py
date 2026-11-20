#!/usr/bin/env python3
"""Summarize MOFid extraction and check HKUST-1 invariance controls."""
from collections import Counter, defaultdict
import json
from pathlib import Path

root = Path('/share/rickyswork/ai_mof/generation/mofid_validation')
report = {}
for group in ('generated', 'training_smoke', 'controls/results'):
    path = root / group / 'results.jsonl'
    if not path.exists():
        continue
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    stats = defaultdict(Counter)
    for r in rows:
        stats[r['cohort']][r['status']] += 1
        stats[r['cohort']]['total'] += 1
        if r.get('chemistry_key'):
            stats[r['cohort']]['chemistry_extracted'] += 1
    report[group] = dict(stats)
    if group == 'controls/results':
        keys = {r.get('framework_key') for r in rows}
        report['control_invariance_pass'] = len(rows) == 3 and len(keys) == 1 and None not in keys
        if not report['control_invariance_pass']:
            raise AssertionError('HKUST-1 identity changed under rename/supercell')
    if group == 'generated':
        by_name = defaultdict(dict)
        for r in rows:
            by_name[r['id']][r['cohort']] = r
        pairs = Counter()
        for pair in by_name.values():
            if 'mofflow2_raw' in pair and 'mofflow2_relaxed_valid' in pair:
                raw, relax = pair['mofflow2_raw'], pair['mofflow2_relaxed_valid']
                pairs['paired'] += 1
                if raw.get('chemistry_key') and relax.get('chemistry_key'):
                    pairs['chemistry_comparable'] += 1
                    pairs['same_chemistry'] += raw['chemistry_key'] == relax['chemistry_key']
                if raw.get('framework_key') and relax.get('framework_key'):
                    pairs['framework_comparable'] += 1
                    pairs['same_framework'] += raw['framework_key'] == relax['framework_key']
        report['raw_relaxed_pairs'] = pairs
(root / 'extraction_summary.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
