import numpy as np
from ase.calculators.calculator import Calculator,all_changes
from ase.io import read,write
from ase.optimize import BFGS

def chemical_bonds(at):
    info=at.info;labels=info['_atom_site_label'];idx={x:i for i,x in enumerate(labels)}
    bonds=sorted({tuple(sorted((idx[a],idx[b]))) for a,b in zip(info['_geom_bond_atom_site_label_1'],info['_geom_bond_atom_site_label_2']) if idx[a]!=idx[b]})
    if not bonds:raise ValueError('Missing construction bond table')
    return bonds

class StericCalculator(Calculator):
    implemented_properties=['energy','forces']
    def __init__(self,reference,bonds,target=1.2,repulsion=100.,bond=100.,position=1.):
        super().__init__();self.reference=reference.positions.copy();self.bonds=set(bonds);self.target=target;self.kr=repulsion;self.kb=bond;self.kp=position
        self.ii,self.jj=np.triu_indices(len(reference),1)
        self.bond_mask=np.array([(i,j) in self.bonds for i,j in zip(self.ii,self.jj)])
        self.r0=reference.get_all_distances(mic=True)[self.ii,self.jj]
        self.reference_distances={ij:reference.get_distance(*ij,mic=True) for ij in bonds}
    def calculate(self,atoms=None,properties=['energy'],system_changes=all_changes):
        super().calculate(atoms,properties,system_changes);a=self.atoms
        forces=-self.kp*(a.positions-self.reference);energy=.5*self.kp*np.sum((a.positions-self.reference)**2)
        vec=a.get_all_distances(mic=True,vector=True)[self.ii,self.jj];d=np.linalg.norm(vec,axis=1)
        if np.any(d<1e-9):raise ValueError('Coincident atoms cannot define a displacement direction')
        active=self.bond_mask|(d<self.target)
        k=np.where(self.bond_mask,self.kb,self.kr);delta=np.where(self.bond_mask,d-self.r0,d-self.target)
        energy+=float(np.sum(.5*k[active]*delta[active]**2))
        f=(k[active]*delta[active]/d[active])[:,None]*vec[active]
        np.add.at(forces,self.ii[active],f);np.add.at(forces,self.jj[active],-f)
        self.results=dict(energy=float(energy),forces=forces)

def precondition(cif,out,record_path,settings):
    at=read(cif,store_tags=True);bonds=chemical_bonds(at);reference=at.copy()
    calc=StericCalculator(reference,bonds,target=settings['precondition_target'],repulsion=settings['precondition_repulsion'],bond=settings['precondition_bond'],position=settings['precondition_position'])
    at.calc=calc;nonbonded_min=float(calc.r0[~calc.bond_mask].min())
    opt=BFGS(at,logfile=str(record_path),maxstep=settings['maxstep'])
    if nonbonded_min<settings['precondition_target']:opt.run(fmax=settings['fmax'],steps=settings['precondition_steps'])
    shifts=[abs(at.get_distance(i,j,mic=True)-r) for (i,j),r in calc.reference_distances.items()]
    distances=at.get_all_distances(mic=True);np.fill_diagonal(distances,np.inf);dmin=float(distances.min());maxshift=max(shifts)
    write(out,at)
    return at,dict(steps=opt.nsteps,initial_nonbonded_min=nonbonded_min,dmin=dmin,max_bond_shift=maxshift,
                   geometry_objective=float(at.get_potential_energy()),passed=bool(dmin>=settings['precondition_min_distance'] and maxshift<=settings['precondition_max_bond_shift']))
