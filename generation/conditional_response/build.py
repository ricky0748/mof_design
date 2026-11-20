import hashlib,json,sys,time
from pathlib import Path
from rdkit import Chem
import pormake as pm
ROOT=Path(__file__).resolve().parent;BASE=Path('/share/rickyswork/ai_mof/generation/budget_confirmation_20261113')
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'support'))
from common import acid_molecule,ligand_key,profile
from build_helpers import build
from anchor_rules import Config,find_anchors,apply_node,embed,place_x,to_pormake_xyz
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    if (ROOT/'build_frozen.json').exists():raise RuntimeError('Already built')
    selection=json.loads((ROOT/'selection_frozen.json').read_text())
    for n,h in selection['outputs'].items():assert sha(ROOT/n)==h
    for n in ['bb','raw']:(ROOT/n).mkdir(exist_ok=True)
    jobs=[]
    for row in json.loads((ROOT/'selected.json').read_text()):
        start=time.monotonic();name='S_'+row['id']
        try:
            cfg=Config(seed=7);mol=acid_molecule(row['smiles']);anchors=apply_node(find_anchors(mol,cfg),'Zn4O');mh=embed(mol,7)
            if mh is None:raise ValueError('embedding_failed')
            if ligand_key(Chem.MolToSmiles(Chem.RemoveHs(mh)))!=row['key']:raise ValueError('identity_changed')
            place_x(mh,anchors,cfg);bb=ROOT/'bb'/(row['id']+'.xyz');bb.write_text(to_pormake_xyz(mh,anchors,cfg));p=profile(pm.BuildingBlock(str(bb)))
            rec=build(row['id'],'S',str(bb),dict(topology='pcu',node='N16'),ROOT);rec.update(bb_sha256=sha(bb),profile=p)
        except Exception as exc:rec=dict(name=name,status='embedding_or_build_failed',reason=repr(exc))
        rec.update(selected=row,preparation_seconds=time.monotonic()-start);jobs.append(rec);print(name,rec['status'],flush=True)
    (ROOT/'build.json').write_text(json.dumps(jobs,indent=2));model='/share/rickyswork/ai_mof/mace_medium.model';db=pm.Database()
    freeze=dict(inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'PROTOCOL.md',ROOT/'selected.json',ROOT/'build.json']+list((ROOT/'raw').glob('*.cif'))},model_sha256=sha(model),scripts={p.name:sha(p) for p in ROOT.glob('*.py')},support={str(p):sha(p) for p in [BASE/'common.py',BASE/'build_helpers.py',BASE/'support/anchor_rules.py',Path('/share/rickyswork/ai_mof/generation/convergence_sensitivity_20261116/worker.py'),db.bb_dir/'N16.xyz',db.topo_dir/'pcu.cgd']})
    (ROOT/'build_frozen.json').write_text(json.dumps(freeze,indent=2))
if __name__=='__main__':main()
