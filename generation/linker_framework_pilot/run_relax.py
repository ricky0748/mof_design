#!/usr/bin/env python3
"""Bounded GPU scheduler: at most one trial per assigned GPU."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

PY = '/home/ruiqi/miniconda3/envs/mofsimbench/bin/python'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--controls-only', action='store_true')
    args = ap.parse_args(); out = Path(args.out).resolve()
    for name in ('records', 'relaxed', 'logs'):
        (out/name).mkdir(exist_ok=True)
    if args.controls_only:
        jobs = [dict(id=r['id'], arm='control', cif=r['cif']) for r in json.loads((out/'controls_build.json').read_text()) if r['status']=='built']
    else:
        controls = [json.loads(p.read_text()) for p in (out/'records').glob('control_*.json')]
        if len(controls)!=2 or not all(r.get('geometry_valid') for r in controls):
            raise RuntimeError('Positive control geometry did not pass; stop before selected trial relaxation.')
        builds = {r['id']:r for r in json.loads((out/'build.json').read_text())}
        selected = json.loads((out/'selected.json').read_text())
        jobs = []
        for row in selected:
            source = Path(row['source_cif'])
            if hashlib.sha256(source.read_bytes()).hexdigest()!=row['source_sha256']:
                raise RuntimeError('Frozen native source changed')
            dest = out/'raw'/('A_'+row['id']+'.cif')
            shutil.copyfile(source, dest)
            jobs.append(dict(id=row['id'], arm='A', cif=str(dest)))
            b = builds[row['id']]
            if b['status']=='built':
                jobs.append(dict(id=row['id'], arm='B', cif=b['cif']))
    (out/('controls_jobs.json' if args.controls_only else 'jobs.json')).write_text(json.dumps(jobs, indent=2))

    def worker(slot):
        for row in jobs[slot::8]:
            name = row['arm']+'_'+row['id']
            record = out/'records'/(name+'.json')
            if record.exists():
                continue
            env = os.environ.copy()
            env.update(CUDA_VISIBLE_DEVICES=str(slot), OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
            start = time.monotonic()
            with (out/'logs'/(name+'.log')).open('w') as log:
                p = subprocess.Popen([PY,str(out/'relax_one.py'),'--cif',row['cif'],
                    '--out',str(out/'relaxed'/(name+'.cif')),'--record',str(record)],
                    env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    p.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    import signal
                    os.killpg(p.pid, signal.SIGKILL); p.wait()
                    record.write_text(json.dumps(dict(status='unresolved',reason='timeout_600_seconds',
                        cif=row['cif'],seconds=round(time.monotonic()-start,2))))
            if not record.exists():
                record.write_text(json.dumps(dict(status='failed',reason='process_exit_'+str(p.returncode),cif=row['cif'])))
            print(name,json.loads(record.read_text()).get('status'),flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(worker,range(8)))
    (out/('CONTROLS_RELAX_DONE' if args.controls_only else 'RELAX_DONE')).write_text('done\n')


if __name__ == '__main__':
    main()
