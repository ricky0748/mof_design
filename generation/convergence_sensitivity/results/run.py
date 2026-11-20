import concurrent.futures,hashlib,json,os,signal,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=Path('/share/rickyswork/ai_mof/generation/budget_confirmation_20261113')
PY='/home/ruiqi/miniconda3/envs/mofsimbench/bin/python'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    for d in ['jobs','records','relaxed','logs']:(ROOT/d).mkdir(exist_ok=True)
    pairs=json.loads((BASE/'pairs.json').read_text());jobs=[]
    for pair in pairs:
        for arm in (['S300','D19'] if pair['id'] in ['B02','B15','B25','B29'] else ['S300']):
            name=arm+'_'+pair['id'];old=json.loads((BASE/'records'/f'{name}.json').read_text());source=BASE/'relaxed'/f'{name}.cif'
            if old['status']!='completed':raise RuntimeError(name+' lacks completed baseline')
            if old.get('output_sha256') and sha(source)!=old['output_sha256']:raise RuntimeError('hash mismatch '+name)
            row=dict(name=name,id=pair['id'],arm=arm,smiles=pair['smiles'],cif=str(source),input_sha256=sha(source),original_volume=old['before']['volume'],baseline_strict=pair[arm]['strict_joint'],baseline_converged=old['converged'],baseline_steps=old['steps'])
            jobs.append(row);(ROOT/'jobs'/f'{name}.json').write_text(json.dumps(row,indent=2))
    freeze=dict(jobs=jobs,model_sha256=sha('/share/rickyswork/ai_mof/mace_medium.model'),scripts={p.name:sha(p) for p in ROOT.glob('*.py')},protocol_sha256=sha(ROOT/'PROTOCOL.md'),settings=dict(fmax=.05,steps=300,timeout=1200,maxstep=.05))
    (ROOT/'frozen.json').write_text(json.dumps(freeze,indent=2))
    def worker(slot):
        for row in jobs[slot::8]:
            name=row['name'];dest=ROOT/'records'/f'{name}.json'
            if dest.exists():raise RuntimeError('Refusing overwrite '+name)
            env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(slot),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
            start=time.monotonic()
            with (ROOT/'logs'/f'{name}.log').open('w') as log:
                p=subprocess.Popen([PY,str(ROOT/'worker.py'),str(ROOT/'jobs'/f'{name}.json')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:p.wait(timeout=1200)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            if not dest.exists():dest.write_text(json.dumps(dict(job=row,status='unresolved',reason='timeout_or_exit_'+str(p.returncode),seconds=time.monotonic()-start)))
            print(name,json.loads(dest.read_text())['status'],flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(worker,range(8)))
    manifest=[dict(id=r['name'],cohort='convergence_20261116',cif=str(ROOT/'relaxed'/f"{r['name']}.cif")) for r in jobs if json.loads((ROOT/'records'/f"{r['name']}.json").read_text())['status']=='completed']
    (ROOT/'manifest.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in manifest));(ROOT/'RELAX_DONE').write_text(str(len(manifest)))
if __name__=='__main__':main()
