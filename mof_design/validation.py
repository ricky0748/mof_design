"""Explicit validation levels: composition/geometry, optional relaxation and MOFid."""
import os
from pathlib import Path
import subprocess
import sys
from .common import read_json,write_json,sha

METALS=set('Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr'.split())

def geometry(path,max_atoms=1000):
    import numpy as np
    from ase.io import read
    from ase.neighborlist import NeighborList,natural_cutoffs
    from scipy.sparse.csgraph import connected_components
    atoms=read(path,store_tags=True)
    if len(atoms)>max_atoms:raise ValueError('max_atoms_exceeded')
    declared=len(atoms.info.get('_atom_site_label',atoms))
    if not len(atoms) or not np.isfinite(atoms.positions).all() or not np.isfinite(atoms.cell.array).all() or atoms.get_volume()<=0:raise ValueError('invalid numeric geometry')
    d=atoms.get_all_distances(mic=True);np.fill_diagonal(d,np.inf)
    nl=NeighborList(natural_cutoffs(atoms,mult=1.15),skin=0.,self_interaction=False,bothways=True);nl.update(atoms)
    components=int(connected_components(nl.get_connectivity_matrix(sparse=True),directed=False)[0]);symbols=atoms.get_chemical_symbols();elements=sorted(set(symbols))
    stats=dict(natoms=len(atoms),declared_natoms=declared,elements=elements,volume=float(atoms.get_volume()),minimum_distance=float(d.min()) if len(atoms)>1 else None,components=components,composition_only_chemistry=bool('C' in elements and set(elements)&METALS),symbols=symbols)
    stats['geometry_passed']=bool(len(atoms)==declared and len(atoms)>1 and stats['minimum_distance']>=.9 and components==1 and stats['composition_only_chemistry'])
    return stats

def check_constraints(metrics,source_topology,constraints):
    elements=set(metrics['elements']);reasons=[]
    if metrics['natoms']>constraints['max_atoms']:reasons.append('max_atoms_exceeded')
    if constraints.get('allowed_elements') and not elements<=set(constraints['allowed_elements']):reasons.append('elements_outside_allowed_set')
    if elements&set(constraints.get('forbidden_elements',[])):reasons.append('forbidden_elements')
    if constraints.get('topologies') and source_topology not in constraints['topologies']:reasons.append('source_topology_not_allowed')
    return reasons

def relax(source,dest,task,candidate_id,runtime):
    cfg=runtime['relaxation'];record=Path(task)/'validation'/f'{candidate_id}.relax.json';log=record.with_suffix('.log')
    command=[cfg['python'],'-m','mof_design.relax_worker',str(source),str(dest),str(record),cfg['model']]
    env=os.environ.copy();env['OMP_NUM_THREADS']='2';env['OPENBLAS_NUM_THREADS']='2'
    with log.open('w',encoding='utf-8') as f:
        try:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=cfg.get('timeout_seconds',1200))
        except subprocess.TimeoutExpired:raise RuntimeError('relaxation_timeout')
    if r.returncode or not record.exists():raise RuntimeError('relaxation_failed; see '+str(log.name))
    rec=read_json(record)
    if rec.get('status')!='completed':raise RuntimeError(rec.get('reason','relaxation_failed'))
    return rec

def mofid(source,task,candidate_id,runtime):
    cfg=runtime['mofid'];root=Path(task)/'validation'/f'{candidate_id}.mofid';root.mkdir()
    manifest=root/'inputs.jsonl';manifest.write_text(__import__('json').dumps(dict(id=candidate_id,cohort='mof_design',cif=str(Path(source).resolve())))+'\n')
    env=os.environ.copy();env['PYTHONPATH']=cfg['pythonpath'];env['PATH']=cfg['java_bin']+os.pathsep+env.get('PATH','')
    with (root/'runtime.log').open('w',encoding='utf-8') as f:
        try:r=subprocess.run([cfg['python'],cfg['script'],str(manifest),str(root/'results'),'--workers','1','--timeout',str(cfg.get('timeout_seconds',180))],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=cfg.get('timeout_seconds',180)+30)
        except subprocess.TimeoutExpired:raise RuntimeError('mofid_timeout')
    records=list((root/'results'/'records').glob('*.json'))
    if r.returncode or len(records)!=1:raise RuntimeError('mofid_no_result')
    rec=read_json(records[0])
    if rec.get('source_sha256')!=sha(source):raise RuntimeError('mofid_source_hash_mismatch')
    return rec

def normalized_linker(smiles):
    from rdkit import Chem
    mol=Chem.MolFromSmiles(smiles)
    if mol is None:return None
    for _,_,o in mol.GetSubstructMatches(Chem.MolFromSmarts('[CX3](=[OX1])[O-]')):
        at=mol.GetAtomWithIdx(o);at.SetFormalCharge(0);at.SetNumExplicitHs(1);at.SetNoImplicit(True)
    Chem.SanitizeMol(mol);mol=Chem.RemoveHs(mol);Chem.RemoveStereochemistry(mol)
    return Chem.MolToSmiles(mol,isomericSmiles=False)
