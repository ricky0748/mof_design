#!/usr/bin/env python3
"""Matched MACE treatment for both arms, with explicit budget and convergence."""
import argparse
import json
from pathlib import Path
import time
import warnings
from compute_config import MODEL, SETTINGS as S
warnings.filterwarnings('ignore')


def metrics(at):
    import numpy as np
    from ase.neighborlist import natural_cutoffs, NeighborList
    from scipy.sparse.csgraph import connected_components
    distances = at.get_all_distances(mic=True)
    np.fill_diagonal(distances, np.inf)
    nl = NeighborList(natural_cutoffs(at, mult=S['neighbor_multiplier']), skin=S['neighbor_skin'], self_interaction=False, bothways=True)
    nl.update(at)
    count, _ = connected_components(nl.get_connectivity_matrix(sparse=True).tocsr(), directed=False)
    return dict(natoms=len(at), volume=float(at.get_volume()),
                dmin=float(distances.min()), fragments=int(count))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cif', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--record', required=True)
    args = ap.parse_args()
    started = time.monotonic()
    rec = dict(cif=args.cif, out=args.out, status='failed')
    try:
        import torch
        torch.set_num_threads(S['threads'])
        from ase.io import read, write
        from ase.optimize import BFGS
        from ase.filters import FrechetCellFilter
        from mace.calculators import mace_mp
        atoms = read(args.cif)
        rec['before'] = metrics(atoms)
        if len(atoms)>S['atom_limit']:
            rec.update(status='unresolved', reason='over_1000_atoms')
        else:
            from steric import precondition
            prepath=Path(args.out).with_name(Path(args.out).stem+'.pre.cif')
            atoms,pre=precondition(args.cif,prepath,Path(args.record).with_suffix('.pre.log'),S)
            rec['precondition']=pre;rec['preconditioned_cif']=str(prepath)
            if not pre['passed']:
                rec.update(status='precondition_failed',reason='minimum_distance_or_bond_shift')
                rec['seconds']=round(time.monotonic()-started,3)
                Path(args.record).write_text(json.dumps(rec,indent=2));return
            atoms.calc = mace_mp(model=MODEL,
                                 default_dtype=S['dtype'], device='cuda')
            target = FrechetCellFilter(atoms)
            opt = BFGS(target, logfile=str(Path(args.record).with_suffix('.opt.log')), maxstep=S['maxstep'])
            converged = bool(opt.run(fmax=S['fmax'], steps=S['steps']))
            rec['after'] = metrics(atoms)
            ratio = rec['after']['volume']/rec['before']['volume']
            a = rec['after']
            rec.update(status='completed', converged=converged, steps=opt.nsteps,
                       volume_ratio=ratio,
                       geometry_valid=bool(a['natoms']==rec['before']['natoms'] and
                          a['dmin']>=S['minimum_distance'] and a['fragments']==1 and S['minimum_volume_ratio']<=ratio<=S['maximum_volume_ratio']))
            write(args.out, atoms)
    except Exception as exc:
        rec.update(reason=type(exc).__name__+': '+str(exc))
    rec['seconds'] = round(time.monotonic()-started, 3)
    Path(args.record).write_text(json.dumps(rec, indent=2))
    print(json.dumps(rec), flush=True)


if __name__ == '__main__':
    main()
