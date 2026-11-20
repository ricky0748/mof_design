import json
from pathlib import Path
from provenance import verify_frozen
from compute_config import MODEL
from eval_helpers import evaluate,load_ids
p=Path(__file__).resolve().parent;verify_frozen(p,MODEL);m=load_ids(p/'mofid_controls/results.jsonl');results={}
for seed in [7,19]:
    name='control_BDC'+str(seed);results[name]=evaluate(name,'O=C(O)c1ccc(C(=O)O)cc1',p,m,expected_topology='pcu')
    if not results[name]['strict_joint']:raise RuntimeError('Calibration failed: '+name)
(p/'calibration.json').write_text(json.dumps(results,indent=2));(p/'CONTROLS_PASS').write_text('strict controls verified\n');print('Both strict BDC controls passed',flush=True)
