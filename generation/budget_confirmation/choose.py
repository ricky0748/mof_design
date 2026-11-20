import json,sys,hashlib
from collections import Counter
from pathlib import Path
from rdkit import Chem,RDLogger
from common import acid_molecule,ligand_key
from provenance import sha

p=Path(__file__).resolve().parent;sys.path.insert(0,str(p/'support'))
from filter_generated_sbus import split_seq,is_metal,has_carbon,check_sbu,NODE_ANIONS
from anchor_rules import find_anchors
RDLogger.DisableLog('rdApp.*')
if (p/'selection_frozen.json').exists():raise RuntimeError('Selection frozen')
source=p/'inference/temp_1.0_target-5.0/preds_samples-600.json';seqs=json.loads(source.read_text())
assert len(seqs)==600
prior=Path('/share/rickyswork/ai_mof/generation')
used={ligand_key(r['smiles']) for directory in ['linker_framework_pilot_20261113','linker_framework_holdout_20261113','linker_framework_fresh_20261113'] for r in json.loads((prior/directory/'selected.json').read_text())}
pool={};excluded=[]
for i,s in enumerate(seqs):
    reason=None;org=set();metals=[]
    try:
        for part in split_seq(s):
            if is_metal(part):metals.append(part);continue
            if not has_carbon(part):
                if part not in NODE_ANIONS:raise ValueError('non_mof_guest')
                continue
            ok,why,info=check_sbu(part)
            if not ok:raise ValueError('chemical_filter:'+','.join(why))
            mol=Chem.MolFromSmiles(part);org.add(Chem.MolToSmiles(mol))
        if not metals:raise ValueError('no_metal')
        if len(org)!=1:raise ValueError('not_single_organic_linker')
        smi=next(iter(org));mol=acid_molecule(smi);anchors=find_anchors(mol)
        if mol.GetNumHeavyAtoms()>60:raise ValueError('over_60_heavy_atoms')
        if len(anchors)!=2 or any(a.rule!='carboxylate' for a in anchors):raise ValueError('not_two_carboxylates')
        key=ligand_key(smi)
        if key in used:raise ValueError('previously_tested_identity')
        if key in pool:raise ValueError('duplicate_identity_in_fresh_batch')
        pool[key]=dict(smiles=smi,key=key,sequence_index=i,sequence=s,rank=hashlib.sha256(('budget1301|'+key).encode()).hexdigest())
    except Exception as e:excluded.append(dict(sequence_index=i,reason=str(e)))
rows=sorted(pool.values(),key=lambda r:r['rank'])[:30]
for i,r in enumerate(rows):r['id']=f'B{i+1:02d}'
for n,v in [('selected.json',rows),('eligible_pool.json',list(pool.values())),('exclusions.json',excluded),('selected_sequences.json',[r['sequence'] for r in rows])]:
    (p/n).write_text(json.dumps(v,indent=2))
(p/'selection_frozen.json').write_text(json.dumps(dict(n=len(rows),generated=len(seqs),eligible=len(pool),exclusions=Counter(r['reason'] for r in excluded),inputs={n:sha(p/n) for n in ['selected.json','eligible_pool.json','selected_sequences.json']},source_sha256=sha(source)),indent=2))
print('Frozen selection',len(rows),'of',len(pool),'eligible new identities',flush=True)
if not rows:raise RuntimeError('No eligible new identities; no resampling')
