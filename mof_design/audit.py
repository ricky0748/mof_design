"""Read-only acceptance audit for a completed task and its delivered package."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from .common import read_json,sha,inside,TERMINAL

def audit(task,check_assets=True):
    task=Path(task).resolve();errors=[];status=read_json(task/'status.json');request=read_json(task/'request.json');provenance=read_json(task/'provenance.json');records=read_json(task/'candidates.json');manifest=read_json(task/'manifest.json');accepted=[r for r in records if r['status']=='accepted']
    if status['status'] not in TERMINAL:errors.append('task_not_terminal')
    if len(accepted)!=len(manifest) or status['accepted']!=len(accepted):errors.append('accepted_count_mismatch')
    if status['attempted']!=len(records) or len(records)>request['max_attempts']:errors.append('attempt_count_mismatch')
    if status['status']=='completed' and len(accepted)!=request['num_candidates']:errors.append('completed_without_requested_count')
    if sha(task/'request.json')!=provenance['request_sha256'] or sha(task/'scene.json')!=provenance['scene_sha256']:errors.append('request_or_scene_changed')
    if check_assets:
        for p,digest in provenance['asset_sha256'].items():
            if not Path(p).is_file() or sha(p)!=digest:errors.append('asset_changed: '+p)
        package=Path(__file__).resolve().parent
        for p,digest in provenance['module_sha256'].items():
            if not (package/p).is_file() or sha(package/p)!=digest:errors.append('module_changed: '+p)
    with zipfile.ZipFile(task/'candidates.zip') as z:
        if z.testzip():errors.append('zip_crc_error')
        for row in manifest:
            p=inside(task/row['cif'],task/'cifs')
            if sha(p)!=row['sha256'] or hashlib.sha256(z.read(row['cif'])).hexdigest()!=row['sha256']:errors.append('candidate_hash_mismatch: '+row['id'])
            record=next((r for r in accepted if r['id']==row['id']),None)
            if not record or not record['validation']['final_geometry']['geometry_passed']:errors.append('geometry_missing: '+row['id'])
            if request['validation']['relax'] and not record.get('validation',{}).get('relaxation',{}).get('converged'):errors.append('convergence_missing: '+row['id'])
            if request['validation']['mofid'] and record.get('validation',{}).get('mofid',{}).get('status')!='identified':errors.append('identity_missing: '+row['id'])
        if len([n for n in z.namelist() if n.startswith('cifs/') and n.endswith('.cif')])!=len(manifest):errors.append('zip_candidate_count_mismatch')
    return dict(passed=not errors,errors=errors,task_id=status['task_id'],status=status['status'],attempts=len(records),accepted=len(manifest),assets_checked=check_assets,scope='recorded outcomes, package integrity and provenance; not independent energy/force recomputation')

if __name__=='__main__':
    result=audit(sys.argv[1],check_assets='--portable' not in sys.argv);print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['passed'] else 1)
