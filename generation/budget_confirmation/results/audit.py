import json,sys
from pathlib import Path
from provenance import sha,verify_frozen,signature,validate_record
from compute_config import MODEL,settings_for,reusable_early_result
from common import ligand_key

p=Path(__file__).resolve().parent;verify_frozen(p,MODEL);g=json.loads((p/'generation_frozen.json').read_text());f=json.loads((p/'frozen.json').read_text())
assert sha(p/'PROTOCOL.md')==g['protocol'] and sha(p/'pipeline.sh')==g['pipeline']
for n,h in g['scripts'].items():assert sha(p/n)==h,n
for n,h in g['sources'].items():assert sha(n)==h,n
for n,h in g['local_configs'].items():assert sha(p/n)==h,n
for n,h in f['libraries'].items():assert sha(n)==h,n
selected=json.loads((p/'selected.json').read_text());sequences=json.loads((p/'inference/temp_1.0_target-5.0/preds_samples-600.json').read_text());n=len(selected);assert len(sequences)==600 and 0<n<=30
prior={ligand_key(r['smiles']) for name in ['linker_framework_pilot_20261113','linker_framework_holdout_20261113','linker_framework_fresh_20261113'] for r in json.loads((p.parent/name/'selected.json').read_text())}
assert len(prior)==58 and len({r['key'] for r in selected})==n and not prior&{r['key'] for r in selected}
assert all(sequences[r['sequence_index']]==r['sequence'] for r in selected)
pool=json.loads((p/'eligible_pool.json').read_text());assert [r['key'] for r in selected]==[r['key'] for r in sorted(pool,key=lambda r:r['rank'])[:30]]
mapping=json.loads((p/'native_mapping.json').read_text());assert len({r['selected_index'] for r in mapping})==len(mapping)
assert all(selected[r['selected_index']]['id']==r['id'] for r in mapping)
builds={r['name']:r for r in json.loads((p/'build.json').read_text())};verified=[];derived=[]
for name,row in builds.items():
    if row['status']!='built':continue
    rec=validate_record(p/'records'/(name+'.json'),signature(row['cif'],MODEL,p,settings_for(row)))
    if rec.get('derived_from'):
        src=rec['derived_from'];sp=p/'records'/(src+'.json');source=validate_record(sp,signature(builds[src]['cif'],MODEL,p,settings_for(builds[src])))
        assert sha(sp)==rec['derived_source_record_sha256']
        assert reusable_early_result(source,rec['calculation_signature'])
        assert rec['output_sha256']==source['output_sha256'] and rec['steps']<=150 and rec['wall_seconds']<=600
        derived.append(name)
    verified.append(name)
pairs=json.loads((p/'pairs.json').read_text());s=json.loads((p/'summary.json').read_text());assert len(pairs)==n
for arm in ['A300','S300','D']:
    assert sum(r[arm]['strict_joint'] for r in pairs)==s['strategies'][arm]['success']
    assert abs(sum(r[arm]['wall_seconds'] for r in pairs)-s['strategies'][arm]['gpu_task_wall_seconds'])<1e-5
physical=[]
for phase in ['primary','secondary']:physical+=json.loads((p/(phase+'_plan.json')).read_text())['physical_jobs']
assert len(physical)==len(set(physical)) and not set(physical)&set(derived)
assert len(physical)+len(derived)==len(verified)
assert s['physical_formal_jobs']==len(physical)
a=dict(passed=True,generated_sequences=600,selected=n,prior_identities_excluded=58,source_hashes_verified=True,signed_logical_records=len(verified),physical_formal_jobs=len(physical),derived_D7_records=len(derived),derived_budgets_valid=True,native_mappings=len(mapping),reread_discrepancies=s['reread_discrepancies'],report_totals_verified=True)
(p/'AUDIT.json').write_text(json.dumps(a,indent=2));(p/'ALL_DONE').write_text('audited phase complete\n');print(json.dumps(a,indent=2),flush=True)
