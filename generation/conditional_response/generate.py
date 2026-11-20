import concurrent.futures,hashlib,json,os,subprocess,time
from pathlib import Path
import numpy as np
import yaml
ROOT=Path(__file__).resolve().parent
MODEL=Path('/share/rickyswork/ai_mof/generation/pilots/MOFFlow-2')
OLD=Path('/share/rickyswork/ai_mof/generation/budget_confirmation_20261113/seq_module_cond')
PY='/share/rickyswork/ai_mof/envs/mofflow2/bin/python'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    if (ROOT/'generation_frozen.json').exists():raise RuntimeError('Already frozen; refusing rerun')
    props=[r['prop'] for r in json.loads((MODEL/'data/seqs/mof_sequence_train.json').read_text()).values()];a=np.array(props,dtype=float)
    stats=dict(n=len(a),min=float(a.min()),max=float(a.max()),quantiles=dict(zip(['q01','q10','q50','q90','q99'],np.quantile(a,[.01,.1,.5,.9,.99]).tolist())))
    (ROOT/'training_property_range.json').write_text(json.dumps(stats,indent=2))
    if not (np.isfinite(a).all() and a.min()<=2<=a.max() and a.min()<=5<=a.max()):raise RuntimeError('Targets outside finite training range')
    groups=[]
    for seed in [1601,1602]:
        for target in [2.,5.]:
            group=f's{seed}_t{int(target)}';out=ROOT/group;out.mkdir();ckpt=out/'seq_module_cond';ckpt.mkdir();(ckpt/'ckpt.pt').symlink_to(OLD/'ckpt.pt');(ckpt/'config.yaml').write_text((OLD/'config.yaml').read_text())
            groups.append(dict(group=group,seed=seed,target=target,out=str(out)))
    sources=[OLD/'ckpt.pt',OLD/'config.yaml',MODEL/'experiments/predict_seq.py',MODEL/'data/dataset_seq.py',MODEL/'data/seqs/vocab.json',MODEL/'data/seqs/mof_sequence_train.json']
    freeze=dict(groups=groups,settings=dict(samples=600,batch_size=50,temperature=1.),protocol_sha256=sha(ROOT/'PROTOCOL.md'),sources={str(p):sha(p) for p in sources},scripts={p.name:sha(p) for p in ROOT.glob('*.py')})
    (ROOT/'generation_frozen.json').write_text(json.dumps(freeze,indent=2))
    def run(item):
        slot,row=item;out=Path(row['out']);env=os.environ.copy();env.update(PROJECT_ROOT=str(MODEL),PYTHONPATH=str(MODEL),CUDA_VISIBLE_DEVICES=str(slot),LD_LIBRARY_PATH='/share/rickyswork/ai_mof/envs/mofflow2/lib:'+env.get('LD_LIBRARY_PATH',''),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
        cmd=[PY,'-m','experiments.predict_seq',f'inference.ckpt_path={out}/seq_module_cond/ckpt.pt',f"inference.seed={row['seed']}",'inference.total_samples=600','inference.temperature=1.0',f"inference.target_property={row['target']}",'inference.batch_size=50',f'hydra.run.dir={out}/hydra'];start=time.monotonic()
        with (out/'generation.log').open('w') as log:r=subprocess.run(cmd,cwd=MODEL,env=env,stdout=log,stderr=subprocess.STDOUT)
        (out/'runtime.json').write_text(json.dumps(dict(returncode=r.returncode,seconds=time.monotonic()-start,command=cmd),indent=2))
        if r.returncode:raise RuntimeError('Generation failed '+row['group'])
        print(row['group'],'generated',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(run,enumerate(groups)))
    (ROOT/'GENERATION_DONE').write_text('4 groups, 2400 samples')
if __name__=='__main__':main()
