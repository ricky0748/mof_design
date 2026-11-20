import json
import os
from pathlib import Path
import zipfile
from .common import read_json,sha,write_json,inside

def finalize(task):
    task=Path(task);status=read_json(task/'status.json');request=read_json(task/'request.json');records=read_json(task/'candidates.json')
    accepted=[r for r in records if r['status']=='accepted'];entries=[]
    for row in accepted:
        p=inside(task/row['cif'],task/'cifs')
        if sha(p)!=row['sha256']:raise ValueError('delivered CIF hash mismatch: '+row['id'])
        entries.append(dict(id=row['id'],cif=row['cif'],sha256=row['sha256'],source_key=row['source_key'],engine=request['engine'],scene=request['scene'],validation_level=row['validation_level'],identity_verified=row['identity_verified']))
    summary=dict(task_id=status['task_id'],status=status['status'],requested=request['num_candidates'],attempted=len(records),accepted=len(entries),unfilled=max(0,request['num_candidates']-len(entries)),scene=request['scene'],engine=request['engine'],deduplication='source combination and exact bytes; full framework identity additionally checked when MOFid enabled',chemical_checks='composition and configured constraints; additional linker identity check for exploration with MOFid',not_assessed=['experimental_synthesizability','thermodynamic_stability','unconfigured_application_performance'])
    write_json(task/'manifest.json',entries);write_json(task/'summary.json',summary)
    from .report import render_report
    render_report(task,summary)
    from .material_report import render_material_reports
    material_files=render_material_reports(task)
    files=['request.json','scene.json','status.json','summary.json','manifest.json','candidates.json','provenance.json','REPORT.md','REPORT.html','events.jsonl']+[r['cif'] for r in entries]
    temporary=task/'candidates.zip.tmp'
    files+=material_files
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in files:
            p=inside(task/name,task)
            if p.exists():z.write(p,name)
    os.replace(temporary,task/'candidates.zip')
    return summary
