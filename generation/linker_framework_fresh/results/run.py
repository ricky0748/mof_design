import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,signal,subprocess,time
from pathlib import Path
import numpy as np
from ase.io import read
from compute_config import MODEL, SETTINGS
from provenance import signature, validate_record, verify_frozen, sha

PY='/home/ruiqi/miniconda3/envs/mofsimbench/bin/python'


def fingerprint(path):
    a=read(path)
    text=json.dumps([a.numbers.tolist(),np.round(a.cell.array,8).tolist(),np.round(a.positions,8).tolist()],separators=(',',':'))
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--controls-only',action='store_true');a=ap.parse_args()
    out=Path(a.out).resolve()
    verify_frozen(out,MODEL)
    for d in ('records','relaxed','logs'): (out/d).mkdir(exist_ok=True)
    builds=json.loads((out/('controls_build.json' if a.controls_only else 'build.json')).read_text())
    canonical={};jobs=[];aliases={};fingerprints={}
    for row in builds:
        if row['status']!='built':continue
        fp=fingerprint(row['cif']);fingerprints[row['name']]=fp
        if fp in canonical:aliases[row['name']]=canonical[fp]
        else:
            canonical[fp]=row['name'];jobs.append(row)
    # Validate every reusable result before any worker starts or metadata changes.
    signatures={row['name']:signature(row['cif'],MODEL,out,SETTINGS) for row in jobs}
    for row in jobs:
        record=out/'records'/(row['name']+'.json')
        if record.exists():validate_record(record,signatures[row['name']])
    name='controls_run' if a.controls_only else 'run'
    (out/(name+'.json')).write_text(json.dumps(dict(canonical_jobs=[j['name'] for j in jobs],aliases=aliases,fingerprints=fingerprints),indent=2))
    def worker(slot):
        for row in jobs[slot::8]:
            key=row['name'];record=out/'records'/(key+'.json')
            env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(slot),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
            if not record.exists():
                start=time.monotonic()
                with (out/'logs'/(key+'.log')).open('w') as log:
                    p=subprocess.Popen([PY,str(out/'relax_one.py'),'--cif',row['cif'],'--out',str(out/'relaxed'/(key+'.cif')),'--record',str(record)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    try:p.wait(timeout=SETTINGS['timeout'])
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid,signal.SIGKILL);p.wait()
                        record.write_text(json.dumps(dict(status='unresolved',reason='timeout_600_seconds',seconds=round(time.monotonic()-start,3))))
                if not record.exists():record.write_text(json.dumps(dict(status='failed',reason='exit_'+str(p.returncode))))
                if signature(row['cif'],MODEL,out,SETTINGS)!=signatures[key]:
                    raise RuntimeError('Calculation inputs changed while running: '+key)
                r=json.loads(record.read_text());r['calculation_signature']=signatures[key]
                if r['status']=='completed':r['output_sha256']=sha(r['out'])
                temp=record.with_suffix('.signed.tmp');temp.write_text(json.dumps(r,indent=2));temp.replace(record)
            print(key,json.loads(record.read_text()).get('status'),flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:list(ex.map(worker,range(8)))
    for alias,source in aliases.items():
        r=json.loads((out/'records'/(source+'.json')).read_text());r['reused_from']=source
        (out/'records'/(alias+'.json')).write_text(json.dumps(r,indent=2))
    manifest=[]
    for row in jobs:
        r=json.loads((out/'records'/(row['name']+'.json')).read_text())
        if r['status']=='completed' and Path(r['out']).exists():manifest.append(dict(id=row['name'],cohort='fresh719',cif=r['out']))
    (out/('controls_manifest.jsonl' if a.controls_only else 'manifest.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in manifest))
    print('unique physical runs',len(jobs),'aliases',len(aliases),'MOFid inputs',len(manifest),flush=True)


if __name__=='__main__':main()

