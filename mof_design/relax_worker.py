"""Isolated MACE process; uses the existing model, never downloads or trains."""
import sys,time
from pathlib import Path
from .common import write_json,sha

def main():
    source,dest,record,model=sys.argv[1:];start=time.monotonic();rec=dict(status='failed',input_sha256=sha(source),model_sha256=sha(model),stages=[])
    try:
        import torch
        torch.set_num_threads(2)
        from ase.io import read,write
        from ase.filters import FrechetCellFilter
        from ase.optimize import BFGS
        from mace.calculators import mace_mp
        atoms=read(source,store_tags=True)
        if len(atoms)>1000:raise ValueError('relaxation_atom_limit_1000')
        original_symbols=atoms.get_chemical_symbols();rec['declared_natoms']=len(atoms.info.get('_atom_site_label',atoms));rec['initial_volume']=float(atoms.get_volume())
        calc=mace_mp(model=model,default_dtype='float64',device='cuda' if torch.cuda.is_available() else 'cpu')
        for label,threshold in [('coarse',.2),('fine',.05)]:
            atoms.calc=calc;target=FrechetCellFilter(atoms);opt=BFGS(target,logfile=str(Path(record).with_suffix('.'+label+'.opt.log')),maxstep=.05)
            converged=bool(opt.run(fmax=threshold,steps=300));out=Path(dest) if label=='fine' else Path(dest).with_suffix('.coarse.cif');write(out,atoms);atoms=read(out,store_tags=True)
            rec['stages'].append(dict(stage=label,fmax=threshold,steps=opt.nsteps,converged=converged))
        rec.update(status='completed',converged=converged,volume_ratio=float(atoms.get_volume())/rec['initial_volume'],atoms_preserved=bool(atoms.get_chemical_symbols()==original_symbols and len(atoms)==rec['declared_natoms']),output_sha256=sha(dest))
    except Exception as exc:rec['reason']=str(exc)
    rec['seconds']=time.monotonic()-start;write_json(record,rec)
if __name__=='__main__':main()
