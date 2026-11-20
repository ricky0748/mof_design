import json
from pathlib import Path
from provenance import sha
from compute_config import MODEL,SETTINGS
p=Path(__file__).resolve().parent
if (p/'frozen.json').exists():raise RuntimeError('Already frozen')
rows=json.loads((p/'selected.json').read_text());builds=[dict(name=r['name'],cif=str(p/'raw'/(r['name']+'.cif')),status='built') for r in rows]
(p/'build.json').write_text(json.dumps(builds,indent=2))
files=[p/'selected.json',p/'PROTOCOL.md',p/'build.json']+list((p/'raw').glob('*.cif'))
f=dict(n=len(rows),inputs={str(q.relative_to(p)):sha(q) for q in files},scripts={q.name:sha(q) for q in p.glob('*.py')},model=sha(MODEL),support=sha(p/'support/anchor_rules.py'),calculation_settings=SETTINGS)
(p/'frozen.json').write_text(json.dumps(f,indent=2));print('Frozen six diagnostic tasks',flush=True)
