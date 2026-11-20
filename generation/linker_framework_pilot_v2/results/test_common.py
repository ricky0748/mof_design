from rdkit import Chem
from common import acid_molecule,ligand_key,match

s='O=C([O-])c1ccc([N+](=O)[O-])cc1C(=O)[O-]'
m=acid_molecule(s)
assert Chem.GetFormalCharge(m)==0
assert sum(a.GetSymbol()=='O' and a.GetFormalCharge()==-1 for a in m.GetAtoms())==1
assert m.GetNumHeavyAtoms()==Chem.MolFromSmiles(s).GetNumHeavyAtoms()
assert ligand_key(s)==ligand_key(Chem.MolToSmiles(m))
phenolate=acid_molecule('[O-]c1ccc(C(=O)[O-])cc1C(=O)[O-]')
assert Chem.GetFormalCharge(phenolate)==-1
p=dict(angles=[30,32,118],span=7.0)
assert match(p,p)['max_angle_difference']==0
assert match(p,dict(angles=[32,30,118],span=7.0))['max_angle_difference']==0
assert not match(p,dict(angles=[0,0,180],span=7))['compatible']
print('carboxylate-only charge normalization and end-swap geometry checks passed')
