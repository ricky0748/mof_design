import argparse,hashlib,json,sys,shutil
from pathlib import Path
from rdkit import Chem
import pormake as pm
from common import acid_molecule,ligand_key,profile
from build_helpers import build

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2))
def bb(row,out):
    from anchor_rules import Config,find_anchors,apply_node,embed,place_x,to_pormake_xyz
    cfg=Config(seed=19);mol=acid_molecule(row['smiles'])
    anchors=apply_node(find_anchors(mol,cfg),'Zn4O')
    if len(anchors)!=2 or any(a.rule!='carboxylate' for a in anchors):raise ValueError('anchor mismatch')
    mh=embed(mol,19)
    if mh is None:raise ValueError('embedding failed')
    place_x(mh,anchors,cfg)
    p=out/'bb'/(row['id']+'.xyz');p.write_text(to_pormake_xyz(mh,anchors,cfg))
    return dict(bb=str(p),bb_sha256=sha(p),profile=profile(pm.BuildingBlock(str(p))))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--formal',action='store_true');a=ap.parse_args()
    out=Path(a.out).resolve();sys.path.insert(0,str(out/'support'))
    for d in ['bb','raw']:(out/d).mkdir(exist_ok=True)
    old=Path('/share/rickyswork/ai_mof/generation/linker_framework_pilot_20261113')
    if not a.formal:
        if (out/'frozen.json').exists():raise RuntimeError('Already frozen')
        used={ligand_key(r['smiles']) for r in json.loads((old/'selected.json').read_text())}
        pool=json.loads((old/'eligible_pool.json').read_text());unique={}
        for r in pool:
            key=ligand_key(r['smiles'])
            if key not in used and key not in unique:unique[key]=r
        rows=sorted(unique.values(),key=lambda r:hashlib.sha256(('holdout-20261113|'+ligand_key(r['smiles'])).encode()).hexdigest())[:20]
        if len(rows)!=20:raise RuntimeError('Insufficient holdout')
        for i,r in enumerate(rows):r['id']=f'H{i+1:02d}'
        write(out/'selected.json',rows)
        targets=[]
        for r in rows:
            t=dict(r)
            try:t.update(bb(r,out),embedding_status='ok')
            except Exception as e:t.update(embedding_status='failed',reason=str(e))
            targets.append(t)
        write(out/'targets.json',targets)
        c=dict(id='C_BDC',smiles='O=C(O)c1ccc(C(=O)O)cc1');c.update(bb(c,out));write(out/'controls.json',[c])
        write(out/'frozen.json',dict(n=20,pool_after_exclusion=len(unique),novel=sum(r['novel_sequence_fragment'] for r in rows),seed=19,
            inputs={p.name:sha(p) for p in [out/'selected.json',out/'targets.json',out/'controls.json',out/'PROTOCOL.md']},
            sources={p.name:sha(p) for p in [old/'eligible_pool.json',old/'selected.json']},
            scripts={p.name:sha(p) for p in out.glob('*.py')},support=sha(out/'support/anchor_rules.py'),
            model=sha('/share/rickyswork/ai_mof/mace_medium.model'),source_cifs={r['id']:sha(r['source_cif']) for r in rows}))
        result=build('C_BDC','control',c['bb'],dict(topology='pcu',node='N16'),out)
        write(out/'controls_build.json',[result]);print('frozen',len(rows),'novel',sum(r['novel_sequence_fragment'] for r in rows),flush=True)
    else:
        from eval_helpers import evaluate,load_ids
        c=evaluate('control_C_BDC','O=C(O)c1ccc(C(=O)O)cc1',out,load_ids(out/'mofid_controls/results.jsonl'))
        write(out/'calibration.json',c)
        if not c['joint']:raise RuntimeError('Calibration failed')
        frozen=json.loads((out/'frozen.json').read_text())
        for n,h in frozen['inputs'].items():
            if sha(out/n)!=h:raise RuntimeError('Frozen input changed')
        records=[]
        for r in json.loads((out/'targets.json').read_text()):
            if sha(r['source_cif'])!=frozen['source_cifs'][r['id']]:raise RuntimeError('Source CIF changed')
            dest=out/'raw'/('A_'+r['id']+'.cif');shutil.copyfile(r['source_cif'],dest)
            records.append(dict(name='A_'+r['id'],cif=str(dest),status='built'))
            if r['embedding_status']=='ok':
                if sha(r['bb'])!=r['bb_sha256']:raise RuntimeError('BB changed')
                records.append(build(r['id'],'U',r['bb'],dict(topology='pcu',node='N16'),out))
            else:records.append(dict(name='U_'+r['id'],status='embedding_failed'))
        write(out/'build.json',records);print('formal builds',len(records),flush=True)
if __name__=='__main__':main()
