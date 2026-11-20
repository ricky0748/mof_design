import json,csv,math
from pathlib import Path
from collections import Counter
import numpy as np
from ase.io import read
from rdkit import Chem
from eval_helpers import evaluate,load_ids
from provenance import verify_frozen,validate_record,signature
from compute_config import MODEL,settings_for
from relax_one import metrics
from analysis_rules import choose_combination,wilson

p=Path(__file__).resolve().parent;verify_frozen(p,MODEL);targets=json.loads((p/'targets.json').read_text());n=len(targets)
builds={r['name']:r for r in json.loads((p/'build.json').read_text())};m=load_ids(p/'mofid/results.jsonl');aliases=json.loads((p/'mofid_aliases.json').read_text());labels={r['id']:r for r in json.loads((p/'training_fragment_audit.json').read_text())['rows']}
rows=[];discrepancies=[]
for t in targets:
    row=dict(id=t['id'],smiles=t['smiles'],sequence_index=t['sequence_index'],training=labels[t['id']],conformers=t['conformers'])
    for arm in ['A300','S300','D7','D19']:
        name=arm+'_'+t['id'];br=builds[name];f=p/'records'/(name+'.json');r={}
        if br['status']=='built':r=validate_record(f,signature(br['cif'],MODEL,p,settings_for(br)))
        v=evaluate(name,t['smiles'],p,m,aliases,builds,expected_topology='pcu' if arm!='A300' else None)
        if r.get('status')=='completed':
            at=read(r['out']);a=metrics(at);raw=read(br['cif'],store_tags=True);declared=len(raw.info['_atom_site_label']);ratio=a['volume']/r['before']['volume']
            geo=bool(a['natoms']==r['before']['natoms']==declared and a['dmin']>=.9 and a['fragments']==1 and .75<=ratio<=1.25)
            if geo!=v['geometry'] or abs(a['dmin']-r['after']['dmin'])>1e-4 or a['fragments']!=r['after']['fragments']:
                discrepancies.append(dict(name=name,in_memory=r['after'],reread=a,geometry_changed=geo!=v['geometry']))
            v.update(geometry=geo,strict_joint=bool(geo and v['strict_identity']),dmin=a['dmin'],fragments=a['fragments'],volume_ratio=ratio,declared_natoms=declared)
        v.update(wall_seconds=r.get('wall_seconds',0.),setup_seconds=r.get('setup_seconds',0.),optimization_seconds=r.get('optimization_seconds',0.),natoms=r.get('before',{}).get('natoms'),atom_steps=r.get('before',{}).get('natoms',0)*r.get('steps',0),derived_from=r.get('derived_from'),budget_steps=br['max_steps'],timeout=br['timeout'])
        row[arm]=v
    row['D']=dict(strict_joint=bool(row['D7']['strict_joint'] or row['D19']['strict_joint']),both_pass=bool(row['D7']['strict_joint'] and row['D19']['strict_joint']),converged_candidate=bool((row['D7']['strict_joint'] and row['D7']['converged']) or (row['D19']['strict_joint'] and row['D19']['converged'])),wall_seconds=row['D7']['wall_seconds']+row['D19']['wall_seconds'],atom_steps=row['D7']['atom_steps']+row['D19']['atom_steps'])
    rows.append(row)
summary=dict(n=n,reread_discrepancies=discrepancies,strategies={})
for strategy in ['A300','S300','D']:
    q=sum(r[strategy]['strict_joint'] for r in rows);cost=sum(r[strategy]['wall_seconds'] for r in rows)
    summary['strategies'][strategy]=dict(success=q,n=n,rate=q/n,wilson95=wilson(q,n),gpu_task_wall_seconds=cost,seconds_per_valid=cost/q if q else None,atom_steps=sum(r[strategy]['atom_steps'] for r in rows))
summary['branch_metrics']={arm:{k:sum(r[arm][k] for r in rows) for k in ['geometry','converged','target_recovered','exact_linker_set','topology_identified','strict_joint']} for arm in ['A300','S300','D7','D19']}
summary['branch_statuses']={arm:Counter(r[arm]['status'] for r in rows) for arm in ['A300','S300','D7','D19']}
summary['paired_S_D']=dict(Counter('both' if r['S300']['strict_joint'] and r['D']['strict_joint'] else 'single_only' if r['S300']['strict_joint'] else 'dual_only' if r['D']['strict_joint'] else 'neither' for r in rows))
summary['both_dual_branches_pass']=sum(r['D']['both_pass'] for r in rows)
summary['dual_converged_candidates']=sum(r['D']['converged_candidate'] for r in rows)
summary['dual_geometry_only_pass']=sum(r['D7']['geometry'] or r['D19']['geometry'] for r in rows)
summary['strata']={key:{str(present):dict(n=sum(r['training'][key]==present for r in rows),**{s:sum(r[s]['strict_joint'] for r in rows if r['training'][key]==present) for s in ['A300','S300','D']}) for present in [True,False]} for key in ['raw_canonical_in_train','normalized_in_train']}
rng=np.random.default_rng(1302);boot={s:[] for s in ['A300','S300','D']};ratios=[];diff=[]
for _ in range(2000):
    sample=[rows[i] for i in rng.integers(0,n,n)];costs={}
    for s in boot:
        q=sum(r[s]['strict_joint'] for r in sample)
        if q:
            v=sum(r[s]['wall_seconds'] for r in sample)/q;boot[s].append(v);costs[s]=v
    if 'D' in costs and 'S300' in costs:ratios.append(costs['D']/costs['S300'])
    diff.append(sum(r['D']['strict_joint']-r['S300']['strict_joint'] for r in sample)/n)
summary['paired_bootstrap']=dict(seed=1302,repetitions=2000,cost_per_valid95={s:dict(interval=np.percentile(v,[2.5,97.5]).tolist() if v else None,nonzero_success_draws=len(v)) for s,v in boot.items()},dual_single_cost_ratio95=np.percentile(ratios,[2.5,97.5]).tolist() if ratios else None,yield_difference95=np.percentile(diff,[2.5,97.5]).tolist())
S=summary['strategies']['S300'];D=summary['strategies']['D'];decision=choose_combination(S['success'],D['success'],S['seconds_per_valid'],D['seconds_per_valid']);summary['decision']=decision
stages=json.loads((p/'stage_times.json').read_text());summary['stage_times']=stages
native=summary['strategies']['A300'];native_full=(native['gpu_task_wall_seconds']+stages['native_prediction']['wall_seconds'])/native['success'] if native['success'] else None
summary['native_cost_including_prediction_per_valid']=native_full
chosen=S if decision['recommendation']=='S' else D if decision['recommendation']=='D' else None
summary['final_recommendation']=decision['recommendation']
if native['success'] and (chosen is None or (native['success']>=chosen['success'] and native_full<=chosen['seconds_per_valid'])):summary['final_recommendation']='A300'
physical=[]
for phase in ['primary','secondary']:physical+=json.loads((p/(phase+'_plan.json')).read_text())['physical_jobs']
summary['physical_formal_jobs']=len(physical);summary['derived_D7_records']=json.loads((p/'secondary_plan.json').read_text())['reused'];summary['physical_formal_wall_seconds']=sum(json.loads((p/'records'/(name+'.json')).read_text())['wall_seconds'] for name in physical)
keys={};allkeys=set()
for row in rows:
    for arm in ['A300','S300','D7','D19']:
        name=arm+'_'+row['id'];mr=m.get(aliases.get(name,name),{});k=mr.get('framework_key')
        if k:allkeys.add(k)
        if k and row[arm]['strict_joint']:keys.setdefault(k,[]).append(name)
matches={};processed=identified=0
for line in Path('/share/rickyswork/ai_mof/generation/mofid_validation/full_reference/results/results.jsonl').open():
    q=json.loads(line);processed+=1;k=q.get('framework_key');identified+=bool(k)
    if k in keys:matches.setdefault(k,[]).append(q['id'])
summary['identity']=dict(unique_valid_frameworks=len(keys),unique_all_identified_frameworks=len(allkeys),reference_processed=processed,reference_identified=identified,reference_partial=processed-identified,matched_valid_identities=len(matches),unmatched_valid_identities=len(keys)-len(matches),matches=[dict(samples=keys[k],training_ids=v) for k,v in matches.items()])
axis_angles=[v for r in rows for c in r['conformers'].values() for v in c['profile']['angles'][:2]]
summary['scope']=dict(heavy_atoms=[min(Chem.MolFromSmiles(r['smiles']).GetNumHeavyAtoms() for r in rows),max(Chem.MolFromSmiles(r['smiles']).GetNumHeavyAtoms() for r in rows)],organic_elements=sorted({a.GetSymbol() for r in rows for a in Chem.MolFromSmiles(r['smiles']).GetAtoms()}),connection_axis_angles=[min(axis_angles),max(axis_angles)] if axis_angles else None,retained_atoms={arm:[min((r[arm]['natoms'] for r in rows if r[arm]['natoms'] is not None),default=None),max((r[arm]['natoms'] for r in rows if r[arm]['natoms'] is not None),default=None)] for arm in ['A300','S300','D7','D19']})
(p/'pairs.json').write_text(json.dumps(rows,indent=2));(p/'summary.json').write_text(json.dumps(summary,indent=2))
flat=[]
for row in rows:
    f=dict(id=row['id'],smiles=row['smiles'],sequence_index=row['sequence_index'],normalized_in_train=row['training']['normalized_in_train'])
    for arm in ['A300','S300','D7','D19','D']:
        for k,v in row[arm].items():f[arm+'_'+k]=v
    flat.append(f)
with (p/'pairs.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
lines=['# 同预算组合路线确认结果','',f'固定600条序列，排除历史58种身份，冻结{n}种新连接体。A300原生；S300单构象7；D为7/19各150步。严格终点使用最终CIF、完整连接体类型集合和预期拓扑。', '', '| 策略 | 严格成功 | 成功率Wilson95% | 任务墙钟秒 | 秒/有效框架 |','|---|---:|---|---:|---:|']
for s in ['A300','S300','D']:
    v=summary['strategies'][s];ci=v['wilson95'];lines.append(f'| {s} | {v["success"]}/{n} | {ci[0]:.1%}–{ci[1]:.1%} | {v["gpu_task_wall_seconds"]:.1f} | {v["seconds_per_valid"] if v["seconds_per_valid"] is not None else "NA"} |')
lines+=['', '预登记选择：'+summary['final_recommendation']+'；S/D规则原因：'+decision['reason']+'。', '', '任务墙钟是GPU分配给进程的端到端时间，包含加载与退出，非核函数计时。D7若复用早收敛S终态，逻辑成本仍完整计入D；物理执行成本另列。原生坐标预测成本另列。', '', '```json',json.dumps(summary,ensure_ascii=False,indent=2),'```', '', '本阶段结果限于本批固定目标、二羧酸连接体、固定pcu/Zn4O与所用势能模型。统计已包含失败/超时，无追加修复；条件响应、热力学稳定性和吸附性能另评。']
(p/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(summary,indent=2),flush=True)
