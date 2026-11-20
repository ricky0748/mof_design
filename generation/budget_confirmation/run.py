import argparse,json,os,signal,subprocess,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from ase.io import read
from provenance import signature,sha,verify_frozen,validate_record
from compute_config import MODEL,settings_for,reusable_early_result

PY='/home/ruiqi/miniconda3/envs/mofsimbench/bin/python'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--phase',choices=['controls','primary','secondary','manifest'],required=True);a=ap.parse_args();out=Path(a.out).resolve();verify_frozen(out,MODEL)
    for d in ['records','relaxed','logs']:(out/d).mkdir(exist_ok=True)
    controls=a.phase=='controls';builds=json.loads((out/('controls_build.json' if controls else 'build.json')).read_text());allrows={r['name']:r for r in builds}
    if a.phase=='manifest':
        canonical={};aliases={};manifest=[]
        for row in builds:
            path=out/'records'/(row['name']+'.json')
            if not path.exists():continue
            rec=validate_record(path,signature(row['cif'],MODEL,out,settings_for(row)))
            if rec['status']!='completed':continue
            key=rec['output_sha256']
            if key in canonical:aliases[row['name']]=canonical[key]
            else:
                canonical[key]=row['name'];manifest.append(dict(id=row['name'],cohort='budget1301',cif=rec['out']))
        (out/'mofid_aliases.json').write_text(json.dumps(aliases,indent=2));(out/'manifest.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in manifest));print('MOFid inputs',len(manifest),'aliases',len(aliases),flush=True);return
    if a.phase=='primary' and not (out/'CONTROLS_PASS').exists():raise RuntimeError('Controls not verified')
    jobs=[r for r in builds if r['status']=='built' and (controls or (r['name'].startswith('D7_') if a.phase=='secondary' else not r['name'].startswith('D7_')))]
    signatures={r['name']:signature(r['cif'],MODEL,out,settings_for(r)) for r in jobs}
    for row in jobs:
        f=out/'records'/(row['name']+'.json')
        if f.exists():validate_record(f,signatures[row['name']])
    reused=[];physical=[]
    for row in jobs:
        key=row['name'];f=out/'records'/(key+'.json')
        if a.phase=='secondary' and not f.exists():
            source='S300_'+key.removeprefix('D7_');sf=out/'records'/(source+'.json');sr=allrows[source]
            rec=validate_record(sf,signature(sr['cif'],MODEL,out,settings_for(sr)))
            if reusable_early_result(rec,signatures[key]):
                derived={**rec,'calculation_signature':signatures[key],'max_steps':150,'derived_from':source,'derived_source_record_sha256':sha(sf),'reuse_policy':'converged-within-150steps-and-600seconds','physical_seconds':0.0}
                f.write_text(json.dumps(derived,indent=2));reused.append(key);print(key,'reused early converged',flush=True);continue
        if f.exists() and json.loads(f.read_text()).get('derived_from'):reused.append(key)
        else:physical.append(row)
    (out/(a.phase+'_plan.json')).write_text(json.dumps(dict(physical_jobs=[r['name'] for r in physical],reused=reused),indent=2))
    def worker(slot):
        for row in physical[slot::8]:
            key=row['name'];record=out/'records'/(key+'.json');settings=settings_for(row)
            if not record.exists():
                env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(slot),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2');start=time.monotonic()
                with (out/'logs'/(key+'.log')).open('w') as log:
                    proc=subprocess.Popen([PY,str(out/'relax_one.py'),'--cif',row['cif'],'--out',str(out/'relaxed'/(key+'.cif')),'--record',str(record),'--steps',str(row['max_steps'])],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    try:proc.wait(timeout=row['timeout'])
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGKILL);proc.wait();record.write_text(json.dumps(dict(status='unresolved',reason='timeout',seconds=time.monotonic()-start)))
                if not record.exists():record.write_text(json.dumps(dict(status='failed',reason='exit_'+str(proc.returncode))))
                rec=json.loads(record.read_text());rec.update(wall_seconds=time.monotonic()-start,calculation_signature=signatures[key],physical_seconds=time.monotonic()-start)
                if signature(row['cif'],MODEL,out,settings)!=signatures[key]:raise RuntimeError('Input changed while running '+key)
                if rec['status']=='completed':rec['output_sha256']=sha(rec['out'])
                tmp=record.with_suffix('.signed.tmp');tmp.write_text(json.dumps(rec,indent=2));tmp.replace(record)
            print(key,json.loads(record.read_text())['status'],flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(worker,range(8)))
    if controls:
        manifest=[dict(id=r['name'],cohort='budget_controls',cif=json.loads((out/'records'/(r['name']+'.json')).read_text())['out']) for r in physical if json.loads((out/'records'/(r['name']+'.json')).read_text())['status']=='completed']
        (out/'controls_manifest.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in manifest))

if __name__=='__main__':main()
