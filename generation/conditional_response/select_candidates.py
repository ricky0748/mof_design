import hashlib,json,sys
from collections import Counter
from pathlib import Path
from rdkit import Chem,RDLogger
ROOT=Path(__file__).resolve().parent
BASE=Path('/share/rickyswork/ai_mof/generation/budget_confirmation_20261113')
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'support'))
from common import acid_molecule,ligand_key
from filter_generated_sbus import split_seq,is_metal,has_carbon,check_sbu,NODE_ANIONS
from anchor_rules import find_anchors
RDLogger.DisableLog('rdApp.*')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def extract(seq):
    org=set();metals=[]
    for part in split_seq(seq):
        if is_metal(part):metals.append(part);continue
        if not has_carbon(part):
            if part not in NODE_ANIONS:raise ValueError('non_mof_guest')
            continue
        ok,why,_=check_sbu(part)
        if not ok:raise ValueError('chemical_filter:'+','.join(why))
        org.add(Chem.MolToSmiles(Chem.MolFromSmiles(part)))
    if not metals:raise ValueError('no_metal')
    if len(org)!=1:raise ValueError('not_single_organic_linker')
    smi=next(iter(org));mol=acid_molecule(smi);anchors=find_anchors(mol)
    if mol.GetNumHeavyAtoms()>60:raise ValueError('over_60_heavy_atoms')
    if len(anchors)!=2 or any(a.rule!='carboxylate' for a in anchors):raise ValueError('not_two_carboxylates')
    key=ligand_key(smi)
    if not key:raise ValueError('identity_failed')
    return dict(key=key,smiles=smi,heavy_atoms=mol.GetNumHeavyAtoms(),rings=mol.GetRingInfo().NumRings(),formal_charge=sum(a.GetFormalCharge() for a in mol.GetAtoms()))
def main():
    if (ROOT/'selection_frozen.json').exists():raise RuntimeError('Selection already frozen')
    freeze=json.loads((ROOT/'generation_frozen.json').read_text());groups={};unique={};sources={};raw={};allrecords=[]
    for g in freeze['groups']:
        name=g['group'];source=ROOT/name/f"inference/temp_1.0_target-{g['target']}/preds_samples-600.json";seqs=json.loads(source.read_text());assert len(seqs)==600;raw[name]=seqs;sources[str(source)]=sha(source);pool={};reasons=Counter();valid=0
        cfg=ROOT/name/f"inference/temp_1.0_target-{g['target']}/config.yaml"
        import yaml
        effective=yaml.safe_load(cfg.read_text())['inference']
        for k,v in [('seed',g['seed']),('target_property',g['target']),('batch_size',50),('total_samples',600),('temperature',1.)]:
            if effective[k]!=v:raise RuntimeError('Effective config mismatch '+name+' '+k)
        sources[str(cfg)]=sha(cfg)
        for i,s in enumerate(seqs):
            rec=dict(group=name,index=i)
            try:
                item=extract(s);valid+=1;key=item['key'];item.update(sequence=s,sequence_index=i,rank=hashlib.sha256(('conditional1600|'+key).encode()).hexdigest())
                if key not in pool:pool[key]={**item,'count':0}
                pool[key]['count']+=1;rec.update(status='eligible',key=key)
            except Exception as exc:reasons[str(exc)]+=1;rec.update(status='excluded',reason=str(exc))
            allrecords.append(rec)
        selected=sorted(pool.values(),key=lambda r:r['rank'])[:15]
        for item in selected:
            key=item['key']
            if key not in unique:unique[key]={**item,'memberships':[]}
            unique[key]['memberships'].append(dict(group=name,count=item['count'],sequence_index=item['sequence_index']))
        groups[name]=dict(seed=g['seed'],target=g['target'],generated=600,eligible_sequences=valid,eligible_unique=len(pool),selected=len(selected),exclusions=dict(reasons),pool=list(pool.values()),selected_keys=[r['key'] for r in selected])
    selected=sorted(unique.values(),key=lambda r:r['rank'])
    for i,r in enumerate(selected):r['id']=f'C{i+1:03d}'
    paired={}
    for seed in [1601,1602]:
        a,b=f's{seed}_t2',f's{seed}_t5';ka=set(r['key'] for r in groups[a]['pool']);kb=set(r['key'] for r in groups[b]['pool']);paired[str(seed)]=dict(raw_sequence_changed=sum(x!=y for x,y in zip(raw[a],raw[b])),n=600,eligible_identity_intersection=len(ka&kb),eligible_identity_union=len(ka|kb),jaccard=len(ka&kb)/len(ka|kb) if ka|kb else None)
    for filename,data in [('groups.json',groups),('selected.json',selected),('sequence_records.json',allrecords),('response_summary.json',dict(groups={k:{x:v for x,v in g.items() if x not in ['pool','selected_keys']} for k,g in groups.items()},paired=paired,unique_selected=len(selected)))]:
        (ROOT/filename).write_text(json.dumps(data,indent=2))
    (ROOT/'selection_frozen.json').write_text(json.dumps(dict(sources=sources,outputs={n:sha(ROOT/n) for n in ['groups.json','selected.json','sequence_records.json','response_summary.json']},selection_script_sha256=sha(__file__)),indent=2))
    print((ROOT/'response_summary.json').read_text(),flush=True)
if __name__=='__main__':main()
