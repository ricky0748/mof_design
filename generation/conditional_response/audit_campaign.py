import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    errors=[];gen=json.loads((ROOT/'generation_frozen.json').read_text());sel=json.loads((ROOT/'selection_frozen.json').read_text());groups=json.loads((ROOT/'groups.json').read_text());selected=json.loads((ROOT/'selected.json').read_text())
    for n,h in gen['sources'].items():
        if sha(n)!=h:errors.append('generation source changed '+n)
    for n,h in gen['scripts'].items():
        if sha(ROOT/n)!=h:errors.append('generation script changed '+n)
    if sha(ROOT/'PROTOCOL.md')!=gen['protocol_sha256']:errors.append('protocol changed')
    for n,h in sel['sources'].items():
        if sha(n)!=h:errors.append('selection source changed '+n)
    for n,h in sel['outputs'].items():
        if sha(ROOT/n)!=h:errors.append('selection output changed '+n)
    if sha(ROOT/'select_candidates.py')!=sel['selection_script_sha256']:errors.append('selection script changed')
    for name,g in groups.items():
        if g['eligible_sequences']+sum(g['exclusions'].values())!=600:errors.append('funnel denominator '+name)
        if sum(r['count'] for r in g['pool'])!=g['eligible_sequences']:errors.append('frequency mismatch '+name)
        expected=[r['key'] for r in sorted(g['pool'],key=lambda r:r['rank'])[:15]]
        observed=[r['key'] for r in selected if any(m['group']==name for m in r['memberships'])]
        if set(expected)!=set(observed):errors.append('selection mismatch '+name)
        if len(observed)!=g['selected']:errors.append('membership mismatch '+name)
    if len({r['key'] for r in selected})!=len(selected):errors.append('selected duplicate identity')
    if not json.loads((ROOT/'STRUCTURE_AUDIT.json').read_text())['passed']:errors.append('structure audit failed')
    if (ROOT/'performance/AUDIT.json').exists() and not json.loads((ROOT/'performance/AUDIT.json').read_text())['passed']:errors.append('performance audit failed')
    result=dict(passed=not errors,errors=errors,generated=2400,selected_unique=len(selected),memberships=sum(len(r['memberships']) for r in selected),scope='generation/selection source hashes, denominators and fixed rank sampling; structure/performance audits linked')
    (ROOT/'CAMPAIGN_AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
