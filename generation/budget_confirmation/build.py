import json,sys,shutil,time
from pathlib import Path
from rdkit import Chem
import pormake as pm
from common import acid_molecule,profile,ligand_key
from build_helpers import build
from provenance import sha
from compute_config import MODEL,SETTINGS

p=Path(__file__).resolve().parent;sys.path.insert(0,str(p/'support'))
from anchor_rules import Config,find_anchors,apply_node,embed,place_x,to_pormake_xyz
def make_bb(row,seed):
    start=time.monotonic();cfg=Config(seed=seed);mol=acid_molecule(row['smiles']);anchors=apply_node(find_anchors(mol,cfg),'Zn4O');mh=embed(mol,seed)
    if mh is None:raise ValueError('embedding_failed')
    if ligand_key(Chem.MolToSmiles(Chem.RemoveHs(mh)))!=ligand_key(row['smiles']):raise ValueError('ligand_changed')
    place_x(mh,anchors,cfg);dest=p/'bb'/(row['id']+'_'+str(seed)+'.xyz');dest.write_text(to_pormake_xyz(mh,anchors,cfg))
    return dict(path=str(dest),sha256=sha(dest),profile=profile(pm.BuildingBlock(str(dest))),embedding_seconds=time.monotonic()-start)
def budget(row,steps):return {**row,'max_steps':steps,'timeout':1200 if steps==300 else 600}

if (p/'frozen.json').exists():raise RuntimeError('Already frozen')
for n,h in json.loads((p/'selection_frozen.json').read_text())['inputs'].items():assert sha(p/n)==h
for d in ['raw','bb']:(p/d).mkdir(exist_ok=True)
selected=json.loads((p/'selected.json').read_text());mapping={r['id']:r for r in json.loads((p/'native_mapping.json').read_text())}
targets=[];formal=[];controls=[]
for row in selected:
    t=dict(row);t['conformers']={};native=mapping.get(row['id'],dict(status='preprocessing_failed'))
    if native['status']=='built':
        dest=p/'raw'/('A300_'+row['id']+'.cif');shutil.copyfile(native['cif'],dest);formal.append(budget(dict(name='A300_'+row['id'],status='built',cif=str(dest)),300))
    else:formal.append(budget(dict(name='A300_'+row['id'],status=native['status']),300))
    for seed,arm,steps in [(7,'S300',300),(19,'D19',150)]:
        try:
            bb=make_bb(row,seed);t['conformers'][str(seed)]=bb
            rec=budget(build(row['id'],arm,bb['path'],dict(topology='pcu',node='N16'),p),steps)
            t['conformers'][str(seed)]['build_seconds']=rec.get('seconds',0)
        except Exception as e:rec=budget(dict(name=arm+'_'+row['id'],status='embedding_or_build_failed',reason=str(e)),steps)
        formal.append(rec)
        if seed==7:formal.append(budget({**rec,'name':'D7_'+row['id'],'role':'logical_150_from_same_seed7_input'},150))
    targets.append(t)
for seed,steps in [(7,300),(19,150)]:
    row=dict(id='BDC'+str(seed),smiles='O=C(O)c1ccc(C(=O)O)cc1');bb=make_bb(row,seed)
    controls.append(budget(build(row['id'],'control',bb['path'],dict(topology='pcu',node='N16'),p),steps))
for name,data in [('targets.json',targets),('build.json',formal),('controls_build.json',controls)]:
    (p/name).write_text(json.dumps(data,indent=2))
db=pm.Database();libraries=[db.bb_dir/'N16.xyz',db.topo_dir/'pcu.cgd']
files=[p/n for n in ['PROTOCOL.md','selected.json','selection_frozen.json','targets.json','build.json','controls_build.json','native_mapping.json','generation_frozen.json']]+list((p/'raw').glob('*.cif'))+list((p/'bb').glob('*.xyz'))
(p/'frozen.json').write_text(json.dumps(dict(n=len(selected),inputs={str(q.relative_to(p)):sha(q) for q in files},scripts={q.name:sha(q) for q in p.glob('*.py')},support=sha(p/'support/anchor_rules.py'),model=sha(MODEL),calculation_settings=SETTINGS,libraries={str(q):sha(q) for q in libraries}),indent=2))
print('Frozen',len(selected),'targets with four logical branches',flush=True)
