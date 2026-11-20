import json,sys
from pathlib import Path
from collections import Counter
from rdkit import Chem,RDLogger
from common import ligand_key
from provenance import sha
RDLogger.DisableLog('rdApp.*')
p=Path(__file__).resolve().parent;sys.path.insert(0,str(p/'support'))
from filter_generated_sbus import split_seq,is_metal,has_carbon
selected=json.loads((p/'selected.json').read_text())
composition=lambda mol:tuple(sorted(Counter(a.GetAtomicNum() for a in mol.GetAtoms() if a.GetAtomicNum()!=1).items()))
wanted={composition(Chem.MolFromSmiles(r['smiles'])) for r in selected}
source=Path('/share/rickyswork/ai_mof/generation/pilots/MOFFlow-2/data/seqs/mof_sequence_train.json');data=json.loads(source.read_text());values=list(data.values()) if isinstance(data,dict) else data
pieces=set()
for v in values:pieces.update(split_seq(v['seq'] if isinstance(v,dict) else str(v)))
pieces={s for s in pieces if not is_metal(s) and has_carbon(s)}
raw=set();normalized=set();invalid=matched=0
for s in pieces:
    mol=Chem.MolFromSmiles(s)
    if mol is None:invalid+=1;continue
    if composition(mol) not in wanted:continue
    matched+=1;raw.add(Chem.MolToSmiles(mol));key=ligand_key(s)
    if key:normalized.add(key)
rows=[dict(id=r['id'],raw_canonical_in_train=r['smiles'] in raw,normalized_in_train=ligand_key(r['smiles']) in normalized) for r in selected]
(p/'training_fragment_audit.json').write_text(json.dumps(dict(training_sequences=len(values),unique_organic_strings=len(pieces),composition_candidates=matched,unparsed_unique_strings=invalid,source_sha256=sha(source),rows=rows,calculated_after_selection=True),indent=2))
print('Labels complete; normalized external',sum(not r['normalized_in_train'] for r in rows),flush=True)
