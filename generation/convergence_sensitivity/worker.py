import argparse, json, time, hashlib
from pathlib import Path
import numpy as np

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def metrics(at):
    from ase.neighborlist import NeighborList,natural_cutoffs
    from scipy.sparse.csgraph import connected_components
    d=at.get_all_distances(mic=True); np.fill_diagonal(d,np.inf)
    nl=NeighborList(natural_cutoffs(at,mult=1.15),skin=0.,self_interaction=False,bothways=True);nl.update(at)
    result=dict(natoms=len(at),volume=float(at.get_volume()),dmin=float(d.min()),fragments=int(connected_components(nl.get_connectivity_matrix(sparse=True),directed=False)[0]),cell=at.cell.cellpar().tolist())
    zn=[i for i,s in enumerate(at.symbols) if s=='Zn'];ox=[i for i,s in enumerate(at.symbols) if s=='O']
    for cutoff in [2.3,2.5,2.7]:
        counts=[];angles=[]
        for z in zn:
            ns=[o for o in ox if at.get_distance(z,o,mic=True)<=cutoff];counts.append(len(ns))
            if len(ns)==4:
                v=at.get_distances(z,ns,mic=True,vector=True);v/=np.linalg.norm(v,axis=1)[:,None]
                angles.extend(float(np.degrees(np.arccos(np.clip(v[i]@v[j],-1,1)))) for i in range(4) for j in range(i+1,4))
        result['coord_'+str(cutoff)]=dict(cn=counts,angle_rms=float(np.sqrt(np.mean((np.array(angles)-109.47122063449)**2))) if angles else None)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('job');a=ap.parse_args();job=json.loads(Path(a.job).read_text());root=Path(a.job).parent.parent
    name=job['name'];rec=dict(job=job,status='failed');start=time.monotonic()
    try:
        import torch
        torch.set_num_threads(2)
        from ase.io import read,write
        from ase.optimize import BFGS
        from ase.filters import FrechetCellFilter
        from mace.calculators import mace_mp
        model='/share/rickyswork/ai_mof/mace_medium.model'
        atoms=read(job['cif'],store_tags=True);before=atoms.copy();rec.update(input_sha256=sha(job['cif']),model_sha256=sha(model),before=metrics(atoms),declared_natoms=len(atoms.info['_atom_site_label']))
        atoms.calc=mace_mp(model=model,default_dtype='float64',device='cuda');target=FrechetCellFilter(atoms)
        opt=BFGS(target,logfile=str(root/'records'/f'{name}.opt.log'),maxstep=.05)
        with (root/'records'/f'{name}.history.jsonl').open('w') as history:
            def snapshot():
                f=atoms.get_forces();gf=target.get_forces()
                row=dict(step=opt.nsteps,energy=float(atoms.get_potential_energy()),atomic_fmax=float(np.linalg.norm(f,axis=1).max()),filter_fmax=float(np.linalg.norm(gf,axis=1).max()),volume=float(atoms.get_volume()))
                history.write(json.dumps(row)+'\n');history.flush()
            opt.attach(snapshot,interval=1);converged=bool(opt.run(fmax=.05,steps=300))
        out=root/'relaxed'/f'{name}.cif';write(out,atoms);after=read(out,store_tags=True);am=metrics(after)
        delta=after.get_scaled_positions()-before.get_scaled_positions();delta-=np.rint(delta);delta-=np.median(delta,axis=0);delta-=np.rint(delta);dis=np.linalg.norm(delta@before.cell.array,axis=1)
        orig=job['original_volume'];rec.update(status='completed',converged=converged,steps=opt.nsteps,after=am,out=str(out),output_sha256=sha(out),volume_ratio_to_original=am['volume']/orig,volume_ratio_to_start=am['volume']/rec['before']['volume'],displacement_rms=float(np.sqrt(np.mean(dis**2))),displacement_max=float(dis.max()),geometry_valid=bool(len(after)==len(before)==rec['declared_natoms'] and am['dmin']>=.9 and am['fragments']==1 and .75<=am['volume']/orig<=1.25))
    except Exception as exc:rec['reason']=repr(exc)
    rec['seconds']=time.monotonic()-start;(root/'records'/f'{name}.json').write_text(json.dumps(rec,indent=2))
if __name__=='__main__':main()
