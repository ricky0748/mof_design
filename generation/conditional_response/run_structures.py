import concurrent.futures,hashlib,json,os,signal,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PY='/home/ruiqi/miniconda3/envs/mofsimbench/bin/python'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    frozen=json.loads((ROOT/'build_frozen.json').read_text())
    for n,h in frozen['inputs'].items():assert sha(ROOT/n)==h
    for n,h in frozen['scripts'].items():assert sha(ROOT/n)==h
    for n,h in frozen['support'].items():assert sha(n)==h
    assert sha('/share/rickyswork/ai_mof/mace_medium.model')==frozen['model_sha256']
    for d in ['jobs','records','relaxed','logs']:(ROOT/d).mkdir(exist_ok=True)
    jobs=[r for r in json.loads((ROOT/'build.json').read_text()) if r['status']=='built']
    for r in jobs:(ROOT/'jobs'/f"{r['name']}.json").write_text(json.dumps(r,indent=2))
    def worker(slot):
        for r in jobs[slot::8]:
            name=r['name'];dest=ROOT/'records'/f'{name}.json'
            if dest.exists():raise RuntimeError('refusing overwrite '+name)
            env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(slot),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2');start=time.monotonic()
            with (ROOT/'logs'/f'{name}.log').open('w') as log:
                p=subprocess.Popen([PY,str(ROOT/'relax.py'),str(ROOT/'jobs'/f'{name}.json')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:p.wait(timeout=2500)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            if not dest.exists():dest.write_text(json.dumps(dict(job=r,status='unresolved',reason='timeout_or_exit_'+str(p.returncode),seconds=time.monotonic()-start)))
            print(name,json.loads(dest.read_text())['status'],flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(worker,range(8)))
    manifest=[]
    for r in jobs:
        rec=json.loads((ROOT/'records'/f"{r['name']}.json").read_text())
        if rec['status']=='completed':manifest.append(dict(id=r['name'],cohort='conditional_response_20261116',cif=rec['out']))
    (ROOT/'manifest.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in manifest));(ROOT/'STRUCTURES_DONE').write_text(str(len(manifest)))
if __name__=='__main__':main()
