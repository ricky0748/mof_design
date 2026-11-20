import argparse,hashlib,json,signal,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,'/share/rickyswork/ai_mof/generation/convergence_sensitivity_20261116')
from worker import metrics
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def timeout(signum,frame):raise TimeoutError('stage_1200_seconds')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('job');a=ap.parse_args();source=Path(a.job);root=source.parent.parent;job=json.loads(source.read_text());name=job['name'];rec=dict(job=job,status='failed',stages=[]);start=time.monotonic()
    try:
        import torch
        torch.set_num_threads(2)
        from ase.io import read,write
        from ase.optimize import BFGS
        from ase.filters import FrechetCellFilter
        from mace.calculators import mace_mp
        atoms=read(job['cif'],store_tags=True);declared=len(atoms.info['_atom_site_label']);rec.update(input_sha256=sha(job['cif']),declared_natoms=declared,before=metrics(atoms))
        if len(atoms)>1000:raise ValueError('over_1000_atoms')
        calc=mace_mp(model='/share/rickyswork/ai_mof/mace_medium.model',default_dtype='float64',device='cuda');signal.signal(signal.SIGALRM,timeout)
        for label,threshold in [('coarse',.2),('fine',.05)]:
            stage_start=time.monotonic();signal.alarm(1200);atoms.calc=calc;target=FrechetCellFilter(atoms);opt=BFGS(target,logfile=str(root/'records'/f'{name}.{label}.opt.log'),maxstep=.05)
            with (root/'records'/f'{name}.{label}.history.jsonl').open('w') as history:
                def snapshot():
                    row=dict(step=opt.nsteps,energy=float(atoms.get_potential_energy()),atomic_fmax=float(np.linalg.norm(atoms.get_forces(),axis=1).max()),filter_fmax=float(np.linalg.norm(target.get_forces(),axis=1).max()),volume=float(atoms.get_volume()));history.write(json.dumps(row)+'\n');history.flush()
                opt.attach(snapshot,interval=1);converged=bool(opt.run(fmax=threshold,steps=300))
            out=root/'relaxed'/f'{name}.{label}.cif';write(out,atoms);atoms=read(out,store_tags=True);signal.alarm(0);rec['stages'].append(dict(stage=label,threshold=threshold,steps=opt.nsteps,converged=converged,seconds=time.monotonic()-stage_start,out=str(out),sha256=sha(out)))
            (root/'records'/f'{name}.progress.json').write_text(json.dumps(rec,indent=2))
        after=metrics(atoms);ratio=after['volume']/rec['before']['volume'];rec.update(status='completed',converged=rec['stages'][-1]['converged'],out=str(out),output_sha256=sha(out),after=after,volume_ratio=ratio,geometry_valid=bool(len(atoms)==rec['before']['natoms']==declared and after['dmin']>=.9 and after['fragments']==1 and .75<=ratio<=1.25))
    except Exception as exc:rec['reason']=repr(exc)
    finally:signal.alarm(0)
    rec['seconds']=time.monotonic()-start;(root/'records'/f'{name}.json').write_text(json.dumps(rec,indent=2))
if __name__=='__main__':main()
