"""Check recorded forces, source immutability, history completeness and output hashes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    frozen=json.loads((ROOT/'frozen.json').read_text());errors=[];checked=0
    for name,digest in frozen['scripts'].items():
        if sha(ROOT/name)!=digest:errors.append('script changed '+name)
    if sha(ROOT/'PROTOCOL.md')!=frozen['protocol_sha256']:errors.append('protocol changed')
    if sha('/share/rickyswork/ai_mof/mace_medium.model')!=frozen['model_sha256']:errors.append('model changed')
    for job in frozen['jobs']:
        name=job['name'];r=json.loads((ROOT/'records'/f'{name}.json').read_text())
        if sha(job['cif'])!=job['input_sha256']:errors.append('baseline changed '+name)
        if r['status']!='completed':continue
        h=[json.loads(s) for s in (ROOT/'records'/f'{name}.history.jsonl').read_text().splitlines()]
        if [v['step'] for v in h]!=list(range(r['steps']+1)):errors.append('history gap '+name)
        if r['steps']>300:errors.append('budget exceeded '+name)
        if bool(h[-1]['filter_fmax']<.05)!=r['converged']:errors.append('convergence mismatch '+name)
        if sha(r['out'])!=r['output_sha256']:errors.append('output changed '+name)
        checked+=1
    result=dict(passed=not errors,logical_jobs=len(frozen['jobs']),completed_checked=checked,errors=errors,scope='hashes, declared budgets and recorded optimizer convergence; not independent force recomputation')
    (ROOT/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
