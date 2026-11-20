import hashlib,json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=Path('/share/rickyswork/ai_mof/generation/budget_confirmation_20261113');sys.path.insert(0,str(BASE))
from identity_checks import check_identity
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    selected=json.loads((ROOT/'selected.json').read_text());builds={r['selected']['id']:r for r in json.loads((ROOT/'build.json').read_text())};mi={r['id']:r for p in (ROOT/'mofid/records').glob('*.json') for r in [json.loads(p.read_text())]};rows=[];accepted=ROOT/'accepted';accepted.mkdir(exist_ok=True);errors=[]
    frozen=json.loads((ROOT/'build_frozen.json').read_text())
    for n,h in frozen['inputs'].items():
        if sha(ROOT/n)!=h:errors.append('input changed '+n)
    for n,h in frozen['scripts'].items():
        if sha(ROOT/n)!=h:errors.append('script changed '+n)
    for n,h in frozen['support'].items():
        if sha(n)!=h:errors.append('support changed '+n)
    if sha('/share/rickyswork/ai_mof/mace_medium.model')!=frozen['model_sha256']:errors.append('model changed')
    for s in selected:
        b=builds[s['id']];row=dict(id=s['id'],key=s['key'],smiles=s['smiles'],memberships=s['memberships'],build_status=b['status'],strict=False,converged=False)
        if b['status']=='built':
            rec=json.loads((ROOT/'records'/f"{b['name']}.json").read_text());row.update(status=rec['status'],reason=rec.get('reason'),converged=rec.get('converged',False),stages=rec.get('stages',[]))
            for stage in rec.get('stages',[]):
                hist=[json.loads(x) for x in (ROOT/'records'/f"{b['name']}.{stage['stage']}.history.jsonl").read_text().splitlines()]
                if stage['steps']>300 or [x['step'] for x in hist]!=list(range(stage['steps']+1)) or bool(hist[-1]['filter_fmax']<stage['threshold'])!=stage['converged']:errors.append('history mismatch '+b['name'])
            if rec['status']=='completed':
                identity=check_identity(s['smiles'],mi.get(b['name'],{}),'pcu');row.update(identity,geometry=rec['geometry_valid'],strict=bool(rec['geometry_valid'] and identity['strict_identity']),cif=rec['out'],sha256=rec['output_sha256'])
                if sha(rec['out'])!=rec['output_sha256']:errors.append('output changed '+b['name'])
                if row['strict'] and row['converged']:shutil.copy2(rec['out'],accepted/(s['id']+'.cif'));row['accepted_cif']=str(accepted/(s['id']+'.cif'))
        rows.append(row)
    groups=json.loads((ROOT/'groups.json').read_text());summary={}
    for name,g in groups.items():
        rs=[r for r in rows if any(m['group']==name for m in r['memberships'])];summary[name]=dict(generated=600,eligible_sequences=g['eligible_sequences'],eligible_unique=g['eligible_unique'],selected=len(rs),built=sum(r['build_status']=='built' for r in rs),completed=sum(r.get('status')=='completed' for r in rs),converged=sum(r['converged'] for r in rs),strict=sum(r['strict'] for r in rs),accepted=sum(r['strict'] and r['converged'] for r in rs))
    audit=dict(passed=not errors,errors=errors,selected_unique=len(rows),scope='frozen source and output hashes, stage budgets and recorded convergence; no independent force recomputation')
    for n,data in [('structure_results.json',rows),('structure_summary.json',summary),('STRUCTURE_AUDIT.json',audit)]: (ROOT/n).write_text(json.dumps(data,indent=2))
    if errors:raise RuntimeError(errors)
    (ROOT/'STRUCTURE_ANALYSIS_DONE').write_text('complete');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
