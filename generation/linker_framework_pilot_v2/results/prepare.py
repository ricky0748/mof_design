"""Freeze target geometries, qualified EGMOF reference templates and decisions."""
import argparse
from collections import Counter
import csv,hashlib,json,sys
from pathlib import Path
import numpy as np
from rdkit import Chem,RDLogger
import pormake as pm
from common import acid_molecule,profile,match,carboxylate_node
RDLogger.DisableLog('rdApp.*')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def target_bb(row,out):
    from anchor_rules import Config,find_anchors,apply_node,embed,place_x,to_pormake_xyz
    cfg=Config(seed=7)
    mol=acid_molecule(row['smiles'])
    anchors=apply_node(find_anchors(mol,cfg),'Zn4O')
    if sum(a.primary for a in anchors)!=2:
        raise ValueError('Need exactly two carboxylate anchors')
    mh=embed(mol,7)
    if mh is None:raise ValueError('Embedding failed')
    place_x(mh,anchors,cfg)
    canonical=Chem.MolToSmiles(Chem.RemoveHs(mh))
    if canonical!=Chem.MolToSmiles(mol):raise ValueError('Ligand changed')
    path=out/'bb'/(row['id']+'.xyz')
    path.write_text(to_pormake_xyz(mh,anchors,cfg))
    return dict(id=row['id'],smiles=row['smiles'],neutral_smiles=canonical,
                bb=str(path),bb_sha256=sha(path),profile=profile(pm.BuildingBlock(str(path))))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');a=ap.parse_args();out=Path(a.out).resolve()
    if (out/'frozen.json').exists():raise RuntimeError('Do not overwrite frozen v2')
    sys.path.insert(0,str(out/'support'))
    (out/'bb').mkdir(exist_ok=True)
    root=Path('/share/rickyswork/ai_mof');old=root/'generation/linker_framework_pilot_20261113'
    selected=json.loads((old/'selected.json').read_text())
    (out/'selected_v1.json').write_bytes((old/'selected.json').read_bytes())
    targets=[]
    for r in selected:
        t=target_bb(r,out);t.update(source_seq_idx=r['source_seq_idx'],source_name=r['source_name'],
            novel=r['novel_sequence_fragment'],source_metals=r['source_metals'],
            old_neutral_smiles=r['neutral_smiles'],normalization_changed=t['neutral_smiles']!=r['neutral_smiles'])
        targets.append(t)
    db=pm.Database();cache={};templates=[];excluded=[]
    source=root/'generation/pilots/EGMOF/scale1000'
    combined=source/'plausibility/combined.csv'
    for row in csv.DictReader(combined.open()):
        if row['final_valid']!='True':continue
        name=row['name'];ts=name.split('+');ns=[x for x in ts[1:] if x.startswith('N')];es=[x for x in ts[1:] if x.startswith('E')]
        if len(ns)!=1 or len(es)!=1 or es[0]=='E0':continue
        try:
            for key in ns+es:
                if key not in cache:cache[key]=db.get_bb(key)
            node,edge=cache[ns[0]],cache[es[0]]
            if not carboxylate_node(node):raise ValueError('node_not_all_carboxylate_connectors')
            node_metals=sorted(set(node.atoms.get_chemical_symbols()) & {'Zn','Cu','Zr','V','Cd','Co','Ni','Fe','Mn','Cr','Al'})
            if not node_metals:raise ValueError('no_supported_metal_in_node')
            topo=db.get_topo(ts[0])
            if len(topo.unique_node_types)!=1 or len(topo.unique_cn)!=1 or int(topo.unique_cn[0])!=node.n_connection_points:
                raise ValueError('not_single_matching_node_type')
            f=source/'cif'/(name+'.cif')
            templates.append(dict(name=name,topology=ts[0],node=ns[0],edge=es[0],profile=profile(edge),
                node_metals=node_metals,
                source_cif=str(f),source_sha256=sha(f),
                node_sha256=sha(db.bb_dir/(ns[0]+'.xyz')),edge_sha256=sha(db.bb_dir/(es[0]+'.xyz')),
                topology_sha256=sha(db.topo_dir/(ts[0]+'.cgd'))))
        except Exception as exc:excluded.append(dict(name=name,reason=str(exc)))
    if not templates:raise RuntimeError('No qualified templates')
    decisions=[];all_scores=[]
    for target in targets:
        scores=[dict(template=t['name'],**match(target['profile'],t['profile'])) for t in templates]
        ranked=sorted((s for s in scores if s['compatible']),key=lambda s:(s['score'],s['template']))
        decisions.append(dict(id=target['id'],match=ranked[0] if ranked else None))
        all_scores.append(dict(id=target['id'],scores=scores))
    matched=[d['match']['template'] for d in decisions if d['match']]
    most=sorted(Counter(matched).items(),key=lambda x:(-x[1],x[0]))[0][0] if matched else templates[0]['name']
    ipc=target_bb(dict(id='C_IPC',smiles='O=C(O)c1cccc(C(=O)O)c1'),out)
    ranks=sorted((dict(template=t['name'],**match(ipc['profile'],t['profile'])) for t in templates
                  if match(ipc['profile'],t['profile'])['compatible']),key=lambda s:(s['score'],s['template']))
    if not ranks:raise RuntimeError('No bent calibration match')
    bdc=target_bb(dict(id='C_BDC',smiles='O=C(O)c1ccc(C(=O)O)cc1'),out)
    controls=[dict(**bdc,arm='control',template=dict(topology='pcu',node='N16'),kind='ligand'),
              dict(**ipc,arm='control',template=next(t for t in templates if t['name']==ranks[0]['template']),kind='ligand'),
              dict(id='C_STOCK',arm='control',template=next(t for t in templates if t['name']==most),kind='stock')]
    for name,data in [('targets.json',targets),('templates.json',templates),('excluded_templates.json',excluded),
                      ('decisions.json',decisions),('all_scores.json',all_scores),('controls.json',controls)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
    frozen=dict(date='2026-11-13',stage='before_new_framework_build_and_relax',n=20,
        selected_v1_sha256=sha(old/'selected.json'),template_source_sha256=sha(combined),templates=len(templates),
        matched=len(matched),selected_templates=Counter(matched),normalization_corrections=[r['id'] for r in targets if r['normalization_changed']],
        parameters=dict(seed=7,max_angle_difference=20,span_ratio=[.5,2.0],score='max_angle_difference+10*abs(log(span_ratio))',steps=150,fmax=.2,maxstep=.05,timeout=600,atom_limit=1000),
        protocol_sha256=sha(out/'PROTOCOL.md'),model_sha256=sha(root/'mace_medium.model'),
        inputs_sha256={x:sha(out/x) for x in ['targets.json','templates.json','decisions.json','controls.json']},
        scripts_sha256={p.name:sha(p) for p in out.glob('*.py')},support_sha256=sha(out/'support/anchor_rules.py'))
    if frozen['model_sha256']!=json.loads((old/'frozen.json').read_text())['model_sha256']:
        raise RuntimeError('MACE model changed since v1')
    (out/'frozen.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2))
    print(json.dumps(frozen,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
