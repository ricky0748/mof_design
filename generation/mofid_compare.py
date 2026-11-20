#!/usr/bin/env python3
"""Compare only successfully resolved MOFid identities; preserve reference coverage."""
import argparse
import csv
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('reference')
    ap.add_argument('generated')
    ap.add_argument('out')
    ap.add_argument('--expected-reference', type=int, required=True)
    a = ap.parse_args()
    refs = [json.loads(x) for x in Path(a.reference).read_text().splitlines() if x.strip()]
    gen = [json.loads(x) for x in Path(a.generated).read_text().splitlines() if x.strip()]
    framework, chemistry, linkers = {}, {}, set()
    for r in refs:
        if r.get('framework_key'):
            framework.setdefault(r['framework_key'], []).append(r['id'])
        if r.get('chemistry_key'):
            chemistry.setdefault(r['chemistry_key'], []).append(r['id'])
        linkers.update(r.get('linkers', []))
    complete = len(refs) == a.expected_reference and all(r.get('framework_key') for r in refs)
    rows = []
    for r in gen:
        key = r.get('framework_key')
        hits = framework.get(key, []) if key else []
        rows.append(dict(id=r['id'], cohort=r['cohort'], extraction_status=r['status'],
                         framework_match='matched' if hits else ('unresolved' if not key else
                         ('absent_complete_reference' if complete else 'no_match_in_processed_reference')),
                         reference_hits=';'.join(hits[:20]),
                         chemistry_match=bool(r.get('chemistry_key') in chemistry),
                         extracted_linkers=len(r.get('linkers', [])),
                         unmatched_linkers=json.dumps([s for s in r.get('linkers', []) if s not in linkers])))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if rows:
        with (out / 'matches.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    summary = dict(reference_expected=a.expected_reference, reference_processed=len(refs),
                   reference_identified=sum(bool(r.get('framework_key')) for r in refs),
                   reference_coverage_complete=complete, generated_processed=len(gen),
                   generated_identified=sum(bool(r.get('framework_key')) for r in gen),
                   exact_framework_matches=sum(r['framework_match'] == 'matched' for r in rows))
    (out / 'comparison.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
