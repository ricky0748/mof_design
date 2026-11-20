import math
import numpy as np
from rdkit import Chem

COO = Chem.MolFromSmarts('[CX3](=[OX1])[O-]')


def acid_molecule(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError('Cannot parse ligand')
    for _, _, oxygen in mol.GetSubstructMatches(COO):
        at = mol.GetAtomWithIdx(oxygen)
        at.SetFormalCharge(0)
        at.SetNumExplicitHs(1)
        at.SetNoImplicit(True)
    Chem.SanitizeMol(mol)
    return mol


def ligand_key(smiles):
    try:
        mol = Chem.RemoveHs(acid_molecule(smiles))
        Chem.RemoveStereochemistry(mol)
        return Chem.MolToSmiles(mol, isomericSmiles=False)
    except Exception:
        return None


def profile(bb):
    symbols = bb.atoms.get_chemical_symbols()
    xs = list(map(int, bb.connection_point_indices))
    if len(xs)!=2:
        raise ValueError('Not two connection points')
    neighbors = {i: set() for i in range(len(symbols))}
    for i,j in bb.bonds:
        neighbors[int(i)].add(int(j)); neighbors[int(j)].add(int(i))
    parent=[]
    for x in xs:
        ps=[i for i in neighbors[x] if symbols[i]!='X']
        if len(ps)!=1 or symbols[ps[0]]!='C':
            raise ValueError('Edge connector parent is not a unique carbon')
        parent.append(ps[0])
    p=bb.atoms.positions
    axis=p[xs[1]]-p[xs[0]];span=float(np.linalg.norm(axis));axis/=span
    vec=[(p[x]-p[par])/np.linalg.norm(p[x]-p[par]) for x,par in zip(xs,parent)]
    angle=lambda v,w:float(np.degrees(np.arccos(np.clip(v@w,-1,1))))
    return dict(angles=[angle(vec[0],-axis),angle(vec[1],axis),angle(vec[0],vec[1])],span=span)


def match(target,reference):
    t,r=target['angles'],reference['angles']
    differences=[max(abs(t[0]-rr[0]),abs(t[1]-rr[1]),abs(t[2]-rr[2]))
                 for rr in (r,[r[1],r[0],r[2]])]
    delta=min(differences);ratio=target['span']/reference['span']
    return dict(max_angle_difference=delta,span_ratio=ratio,
                score=delta+10*abs(math.log(ratio)),
                compatible=delta<=20 and 0.5<=ratio<=2.0)


def carboxylate_node(bb):
    symbols=bb.atoms.get_chemical_symbols()
    neighbors={i:set() for i in range(len(symbols))}
    for i,j in bb.bonds:
        neighbors[int(i)].add(int(j));neighbors[int(j)].add(int(i))
    for x in bb.connection_point_indices:
        ps=[i for i in neighbors[int(x)] if symbols[i]!='X']
        if len(ps)!=1 or symbols[ps[0]]!='C' or sum(symbols[j]=='O' for j in neighbors[ps[0]])!=2:
            return False
    return len(bb.connection_point_indices)>0
