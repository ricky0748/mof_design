import json,sys,shutil
from pathlib import Path
from rdkit import Chem
import pormake as pm
from common import acid_molecule,profile
from build_helpers import build
from provenance import sha,verify_frozen
from compute_config import MODEL,SETTINGS
from eval_helpers import evaluate,load_ids

p=Path(__file__).resolve().parent;sys.path.insert(0,str(p/'support'))
from anchor_rules import Config,find_anchors,apply_node,embed,place_x,to_pormake_xyz
def make_bb(row,seed):
    cfg=Config(seed=seed);mol=acid_molecule(row['smiles']);anchors=apply_node(find_anchors(mol,cfg),'Zn4O');mh=embed(mol,seed)
    if mh is None:raise ValueError('embedding_failed')
    place_x(mh,anchors,cfg);dest=p/'bb'/(row['id']+'_'+str(seed)+'.xyz');dest.write_text(to_pormake_xyz(mh,anchors,cfg))
    return dict(path=str(dest),sha256=sha(dest),profile=profile(pm.BuildingBlock(str(dest))))

if '--formal' not in sys.argv:
    if (p/'frozen.json').exists():raise RuntimeError('Already frozen')
    for n,h in json.loads((p/'selection_frozen.json').read_text())['inputs'].items():assert sha(p/n)==h
    for d in ['raw','bb']:(p/d).mkdir(exist_ok=True)
    selected=json.loads((p/'selected.json').read_text());targets=[];formal=[];controls=[]
    mapping={r['id']:r for r in json.loads((p/'native_mapping.json').read_text())}
    for row in selected:
        t=dict(row);t['conformers']={};native=mapping.get(row['id'],dict(status='preprocessing_failed'))
        if native['status']=='built':
            dest=p/'raw'/('A_'+row['id']+'.cif');shutil.copyfile(native['cif'],dest);formal.append(dict(name='A_'+row['id'],status='built',cif=str(dest)))
        else:formal.append(dict(name='A_'+row['id'],status=native['status']))
        for seed in [7,19]:
            arm='U'+str(seed)
            try:
                bb=make_bb(row,seed);t['conformers'][str(seed)]=bb
                formal.append(build(row['id'],arm,bb['path'],dict(topology='pcu',node='N16'),p))
            except Exception as e:formal.append(dict(name=arm+'_'+row['id'],status='embedding_or_build_failed',reason=str(e)))
        targets.append(t)
    for seed in [7,19]:
        c=dict(id='BDC'+str(seed),smiles='O=C(O)c1ccc(C(=O)O)cc1');bb=make_bb(c,seed)
        controls.append(build(c['id'],'control',bb['path'],dict(topology='pcu',node='N16'),p))
    for name,data in [('targets.json',targets),('pending_build.json',formal),('controls_build.json',controls)]:
        (p/name).write_text(json.dumps(data,indent=2))
    inputs=[p/n for n in ['PROTOCOL.md','selected.json','selection_frozen.json','targets.json','pending_build.json','controls_build.json','native_mapping.json','generation_frozen.json']]+list((p/'raw').glob('*.cif'))+list((p/'bb').glob('*.xyz'))
    (p/'frozen.json').write_text(json.dumps(dict(n=len(selected),inputs={str(q.relative_to(p)):sha(q) for q in inputs},scripts={q.name:sha(q) for q in p.glob('*.py')},support=sha(p/'support/anchor_rules.py'),model=sha(MODEL),calculation_settings=SETTINGS),indent=2))
    print('Frozen',len(selected),'three-arm targets',flush=True)
else:
    verify_frozen(p,MODEL);m=load_ids(p/'mofid_controls/results.jsonl');run=json.loads((p/'controls_run.json').read_text());cal={}
    for seed in [7,19]:
        name='control_BDC'+str(seed);cal[name]=evaluate(name,'O=C(O)c1ccc(C(=O)O)cc1',p,m,run['aliases'])
        if not cal[name]['joint'] or cal[name]['topology']!='pcu':raise RuntimeError('Calibration failed '+name)
    (p/'calibration.json').write_text(json.dumps(cal,indent=2));shutil.copyfile(p/'pending_build.json',p/'build.json');print('Controls passed; formal enabled',flush=True)
