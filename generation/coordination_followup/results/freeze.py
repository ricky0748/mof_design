import json
from pathlib import Path
from provenance import sha
from compute_config import MODEL,SETTINGS
p=Path(__file__).resolve().parent
if (p/'frozen.json').exists():raise RuntimeError('Already frozen')
rows=json.loads((p/'selected.json').read_text())
builds=[dict(name=r['name'],cif=str(p/'raw'/(r['name']+'.cif')),status='built') for r in rows]
(p/'build.json').write_text(json.dumps(builds,indent=2))
inputs=[p/'selected.json',p/'PROTOCOL.md',p/'build.json']+sorted((p/'raw').glob('*.cif'))
f=dict(inputs={str(x.relative_to(p)):sha(x) for x in inputs},scripts={x.name:sha(x) for x in p.glob('*.py')},support=sha(p/'support/anchor_rules.py'),model=sha(MODEL),calculation_settings=SETTINGS,n=len(rows))
(p/'frozen.json').write_text(json.dumps(f,indent=2));print('Frozen',len(rows),'diagnostic tasks')
