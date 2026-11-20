import json,csv,re
from pathlib import Path
from collections import Counter
from ase.io import read
from common import ligand_key
from eval_helpers import evaluate,load_ids,paired
from relax_one import metrics
from provenance import verify_frozen
from compute_config import MODEL

p=Path(__file__).resolve().parent;verify_frozen(p,MODEL)
targets=json.loads((p/'targets.json').read_text());n=len(targets);run=json.loads((p/'run.json').read_text());m=load_ids(p/'mofid/results.jsonl');builds={r['name']:r for r in json.loads((p/'build.json').read_text())}
rows=[];discrepancies=[]
for t in targets:
    row=dict(id=t['id'],smiles=t['smiles'],sequence_index=t['sequence_index'],conformers=t['conformers'])
    for arm in ['A','U7','U19']:
        name=arm+'_'+t['id'];v=evaluate(name,t['smiles'],p,m,run['aliases'],builds,expected_topology='pcu' if arm!='A' else None);canonical=run['aliases'].get(name,name)
        if v['status']=='completed':
            rec=json.loads((p/'records'/(name+'.json')).read_text());at=read(p/'relaxed'/(canonical+'.cif'));a=metrics(at);ratio=a['volume']/rec['before']['volume']
            geo=bool(a['natoms']==rec['before']['natoms'] and a['dmin']>=.9 and a['fragments']==1 and .75<=ratio<=1.25)
            if geo!=v['geometry'] or a['natoms']!=rec['after']['natoms'] or abs(a['dmin']-rec['after']['dmin'])>1e-4 or a['fragments']!=rec['after']['fragments']:
                discrepancies.append(dict(name=name,in_memory=rec['after'],reread=a,geometry_changed=geo!=v['geometry']))
            v.update(geometry=geo,joint=geo and v['topology_identified'] and v['target_recovered'],strict_joint=geo and v['strict_identity'],dmin=a['dmin'],fragments=a['fragments'],volume_ratio=ratio)
        row[arm]=v
    rows.append(row)
summary=dict(n=n,arms={arm:{k:sum(r[arm][k] for r in rows) for k in ['geometry','converged','target_recovered','topology_identified','joint','strict_joint']} for arm in ['A','U7','U19']},
    statuses={arm:Counter(r[arm]['status'] for r in rows) for arm in ['A','U7','U19']},
    paired_A_U7=paired(rows,'A','U7'),paired_A_U19=paired(rows,'A','U19'),
    both_seeds_pass=sum(r['U7']['joint'] and r['U19']['joint'] for r in rows),either_seed_pass=sum(r['U7']['joint'] or r['U19']['joint'] for r in rows),
    both_seeds_strict_pass=sum(r['U7']['strict_joint'] and r['U19']['strict_joint'] for r in rows),either_seed_strict_pass=sum(r['U7']['strict_joint'] or r['U19']['strict_joint'] for r in rows),
    same_seed_success_status=sum(r['U7']['joint']==r['U19']['joint'] for r in rows),
    expected_pcu={arm:sum(r[arm]['topology']=='pcu' and r[arm]['topology_identified'] for r in rows) for arm in ['U7','U19']},
    unique_formal_jobs=len(run['canonical_jobs']),aliases=run['aliases'],reread_discrepancies=discrepancies,
    old_gate={arm:dict(rejected=sum(str(seed) in r['conformers'] and max(r['conformers'][str(seed)]['profile']['angles'][:2])>20 for r in rows),rejected_and_pass=sum(str(seed) in r['conformers'] and max(r['conformers'][str(seed)]['profile']['angles'][:2])>20 and r[arm]['joint'] for r in rows)) for arm,seed in [('U7',7),('U19',19)]})
key_samples={}
for t in targets:
    for arm in ['U7','U19']:
        name=arm+'_'+t['id'];k=m.get(run['aliases'].get(name,name),{}).get('framework_key')
        if k:key_samples.setdefault(k,[]).append(name)
hits={};processed=identified=0
for line in Path('/share/rickyswork/ai_mof/generation/mofid_validation/full_reference/results/results.jsonl').open():
    q=json.loads(line);processed+=1;k=q.get('framework_key');identified+=bool(k)
    if k in key_samples:hits.setdefault(k,[]).append(q['id'])
valid_keys={m[run['aliases'].get(arm+'_'+r['id'],arm+'_'+r['id'])]['framework_key'] for r in rows for arm in ['U7','U19'] if r[arm]['strict_joint']}
summary.update(unique_U_frameworks=len(key_samples),unique_valid_U_frameworks=len(valid_keys),reference_processed=processed,reference_identified=identified,training_matches=[dict(samples=key_samples[k],training_ids=v) for k,v in hits.items()],physical_relaxation_seconds=sum(json.loads((p/'records'/(name+'.json')).read_text()).get('seconds',0) for name in run['canonical_jobs']))
(p/'pairs.json').write_text(json.dumps(rows,indent=2));(p/'summary.json').write_text(json.dumps(summary,indent=2))
flat=[]
for r in rows:
    f={k:r[k] for k in ['id','smiles','sequence_index']}
    for arm in ['A','U7','U19']:
        for k,v in r[arm].items():f[arm+'_'+k]=v
    flat.append(f)
with (p/'pairs.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
lines=['# 全新生成批次与双构象种子结果','',f'序列种子719固定生成200条；排除旧40种连接体后，冻结实际{n}种连接体。A原生，U7/U19为固定pcu/N16与构象种子7/19。', '',f'| 指标（分母{n}） | A | U7 | U19 |','|---|---:|---:|---:|']
for k,label in [('geometry','几何有效'),('converged','150步收敛'),('target_recovered','目标连接体出现'),('topology_identified','完整拓扑身份'),('joint','历史联合终点（目标出现）'),('strict_joint','严格联合终点（完整连接体类型集合及预期拓扑）')]:lines.append('| '+label+' | '+' | '.join(f'{summary["arms"][a][k]}/{n}' for a in ['A','U7','U19'])+' |')
lines+=['',f'两构象种子均通过：{summary["both_seeds_pass"]}/{n}；至少一种通过：{summary["either_seed_pass"]}/{n}。两项分开报告，不能把择优后的结果称为单次生成成功率。', '', '```json',json.dumps(summary,ensure_ascii=False,indent=2),'```', '', '组装同时改变节点、拓扑和初始坐标；结果评价整个重建方案。该批次固定目标条件，目标响应、配位应变、热力学稳定性和吸附性能另评。主表以最终CIF复读指标为准，内存与复读差异逐条列出。']
(p/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8');(p/'ALL_DONE').write_text('done\n');print(json.dumps(summary,indent=2),flush=True)
