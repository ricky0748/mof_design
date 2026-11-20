import json,re
from pathlib import Path
from common import ligand_key
from provenance import verify_frozen,validate_record,signature
from compute_config import MODEL,SETTINGS
from ase.io import read
from relax_one import metrics

p=Path(__file__).resolve().parent;verify_frozen(p,MODEL)
m={r['id']:r for r in map(json.loads,(p/'mofid/results.jsonl').read_text().splitlines())};rows=[];builds={r['name']:r for r in json.loads((p/'build.json').read_text())}
for t in json.loads((p/'selected.json').read_text()):
    name=t['name'];r=validate_record(p/'records'/(name+'.json'),signature(builds[name]['cif'],MODEL,p,SETTINGS));mr=m.get(name,{})
    target=ligand_key(t['smiles']);expected={target};actual={ligand_key(s) for s in mr.get('linkers',[])}
    v=dict(name=name,reason=t['reason'],baseline_geometry=t['baseline']['geometry_valid'],baseline_joint=t['baseline_endpoint']['joint'],status=r['status'],precondition=r.get('precondition'),converged=r.get('converged',False),mace_steps=r.get('steps'),topology=mr.get('result',{}).get('topology'),target_recovered=bool(target and target in actual),exact_linker_set=bool(target and expected==actual),geometry=False)
    if r['status']=='completed':
        a=metrics(read(p/'relaxed'/(name+'.cif')));ratio=a['volume']/r['before']['volume']
        v.update(after=a,geometry=bool(a['natoms']==r['before']['natoms'] and a['dmin']>=.9 and a['fragments']==1 and .75<=ratio<=1.25),volume_ratio=ratio)
        hist=re.findall(r'BFGS:\s+\d+\s+\S+\s+([-+\d.eE]+)\s+([-+\d.eE]+)',(p/'records'/(name+'.opt.log')).read_text())
        v.update(initial_mace_fmax=float(hist[0][1]),final_mace_fmax=float(hist[-1][1]),initial_mace_energy=float(hist[0][0]),final_mace_energy=float(hist[-1][0]))
    v['joint']=bool(v['geometry'] and v['target_recovered'] and mr.get('framework_key'));v['strict_pcu_joint']=bool(v['joint'] and v['exact_linker_set'] and v['topology']=='pcu');rows.append(v)
summary=dict(n=6,failed_cases_recovered=sum(r['strict_pcu_joint'] for r in rows if not r['baseline_joint']),failed_cases_n=sum(not r['baseline_joint'] for r in rows),successful_controls_preserved=sum(r['strict_pcu_joint'] for r in rows if r['baseline_joint']),successful_controls_n=sum(r['baseline_joint'] for r in rows),rows=rows)
(p/'summary.json').write_text(json.dumps(summary,indent=2))
lines=['# 成键约束几何预处理小试结果','', '两失败案例与四成功控制，固定50步几何预处理+100步MACE预算。历史基线为150步MACE。', '', '| 样本 | 旧联合终点 | 预处理通过 | 预处理步数 | MACE步数 | 新严格pcu联合终点 | 收敛 |','|---|---|---|---:|---:|---|---|']
for r in rows:lines.append(f'| {r["name"]} | {r["baseline_joint"]} | {r["precondition"]["passed"] if r["precondition"] else "NA"} | {r["precondition"]["steps"] if r["precondition"] else "NA"} | {r["mace_steps"]} | {r["strict_pcu_joint"]} | {r["converged"]} |')
lines+=['','```json',json.dumps(summary,indent=2),'```','','原始基线保持冻结。这是已观察失败后的诊断试验；正面结果需在独立批次验证。几何目标与物理势能分开报告。']
(p/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8');(p/'ALL_DONE').write_text('done\n');print(json.dumps(summary,indent=2),flush=True)
