#!/usr/bin/env python3
"""Run isolated MOFid subprocesses from a manifest, with resumable JSON records.

Inside the official MOFid environment:
  python mofid_validate.py manifest.jsonl output_dir --workers 8
Manifest fields: id, cif, cohort, [source_key]. All paths must be absolute.
Only identified topologies qualify for full framework identity comparisons.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def identity(result):
    # Use parsed fields, not the display MOFid containing filename/version data.
    components = sorted(set(result.get('smiles', '').split('.')) - {''})
    topology = str(result.get('topology', ''))
    cat = result.get('cat')
    fragments_ok = bool(components) and not any(x in {'*', 'ERROR', 'NA'} for x in components)
    topology_ok = bool(topology) and all(
        x.strip().upper() not in {'', 'NA', 'ERROR', 'UNKNOWN', 'TIMEOUT', 'MISMATCH'}
        and not x.strip().upper().startswith(('UNKNOWN', 'ERROR'))
        for x in topology.split(','))
    chemistry = '.'.join(components) if fragments_ok else None
    return {
        'chemistry_key': chemistry,
        'framework_key': json.dumps([chemistry, topology, cat], separators=(',', ':'))
        if chemistry and topology_ok and cat is not None else None,
        'linkers': sorted(set(result.get('smiles_linkers', []))),
        'topology_resolved': topology_ok,
    }


def run_one(row, root, timeout):
    token = hashlib.sha256((row['cohort'] + '\0' + row['id']).encode()).hexdigest()
    dest = root / 'records' / (token + '.json')
    source = Path(row['cif'])
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if dest.exists():
        old = json.loads(dest.read_text())
        if old.get('source_sha256') == source_hash:
            return old
    work = root / 'raw' / token
    work.mkdir(parents=True, exist_ok=True)
    code = ('import json,sys; from mofid.run_mofid import cif2mofid; '
            'r=cif2mofid(sys.argv[1],sys.argv[2]); '
            'print("RESULT_JSON="+json.dumps(r))')
    record = dict(row, source_sha256=source_hash)
    start = time.monotonic()
    with (work / 'stdout.log').open('w') as stdout, (work / 'stderr.log').open('w') as stderr:
        proc = subprocess.Popen([sys.executable, '-c', code, str(source), str(work)],
                                stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            proc.wait(timeout=timeout)
            record['returncode'] = proc.returncode
            results = [line[len('RESULT_JSON='):] for line in (work / 'stdout.log').read_text().splitlines()
                       if line.startswith('RESULT_JSON=')]
            if proc.returncode == 0 and results:
                record['result'] = json.loads(results[-1])
                record.update(identity(record['result']))
                record['status'] = 'identified' if record['framework_key'] else 'partial'
            else:
                record['status'] = 'failed'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            record['status'] = 'timeout'
    record['seconds'] = round(time.monotonic() - start, 3)
    temp = dest.with_suffix('.tmp')
    temp.write_text(json.dumps(record, ensure_ascii=False))
    temp.replace(dest)
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest')
    ap.add_argument('out')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--timeout', type=int, default=180)
    args = ap.parse_args()
    root = Path(args.out).resolve()
    (root / 'records').mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in Path(args.manifest).read_text().splitlines() if line.strip()]
    statuses = {}
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(run_one, row, root, args.timeout) for row in rows]
        with (root / 'results.jsonl').open('w') as stream:
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                try:
                    rec = future.result()
                except Exception as exc:
                    raise RuntimeError('MOFid batch stopped; inspect source path or environment') from exc
                stream.write(json.dumps(rec, ensure_ascii=False) + '\n')
                stream.flush()
                statuses[rec['status']] = statuses.get(rec['status'], 0) + 1
                if i % 10 == 0 or i == len(rows):
                    print(i, '/', len(rows), statuses, flush=True)
    (root / 'summary.json').write_text(json.dumps({'total': len(rows), 'statuses': statuses}, indent=2))


if __name__ == '__main__':
    main()
