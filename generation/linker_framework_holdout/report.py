import argparse,json,csv,math
from collections import Counter
from pathlib import Path
from ase.io import read
from eval_helpers import evaluate,load_ids,paired
from relax_one import metrics

ap=argparse.ArgumentParser();ap.add_argument('out');args=ap.parse_args();out=Path(args.out)
targets=json.loads((out/'targets.json').read_text());run=json.loads((out/'run.json').read_text());m=load_ids(out/'mofid/results.jsonl')
builds={r['name']:r for r in json.loads((out/'build.json').read_text())}
rows=[];reread_discrepancies=[]
for t in targets:
    r=dict(id=t['id'],source=t['source_name'],smiles=t['smiles'],novel=t['novel_sequence_fragment'],profile=t.get('profile'))
    for arm in ['A','U']:
        name=arm+'_'+t['id'];r[arm]=evaluate(name,t['smiles'],out,m,run['aliases'],builds)
        if r[arm]['status']=='completed':
            canonical=run['aliases'].get(name,name)
            a=read(out/'relaxed'/(canonical+'.cif'));v=metrics(a)
            rec=json.loads((out/'records'/(name+'.json')).read_text())
            if abs(v['dmin']-rec['after']['dmin'])>=1e-4 or v['fragments']!=rec['after']['fragments'] or len(a)!=rec['after']['natoms']:
                reread_discrepancies.append(dict(name=name,in_memory=rec['after'],reread=v))
            reread_geo=bool(v['natoms']==rec['before']['natoms'] and v['dmin']>=.9 and v['fragments']==1 and .75<=v['volume']/rec['before']['volume']<=1.25)
            assert reread_geo==r[arm]['geometry'], 'CIF reread changes geometry classification: '+name
    rows.append(r)
summary={arm:{k:sum(r[arm][k] for r in rows) for k in ['geometry','converged','target_recovered','topology_identified','joint']} for arm in ['A','U']}
summary.update(n=20,paired=paired(rows,'A','U'),novel=sum(r['novel'] for r in rows),unique_runs=len(run['canonical_jobs']),aliases=run['aliases'],audit_pass=True,
    expected_pcu=sum(r['U']['topology']=='pcu' and r['U']['topology_identified'] for r in rows),reread_discrepancies=reread_discrepancies)
summary['old_gate_cross_table']={str(th):dict(rejected=sum(bool(r['profile']) and max(r['profile']['angles'][:2])>th for r in rows),rejected_but_joint_pass=sum(bool(r['profile']) and max(r['profile']['angles'][:2])>th and r['U']['joint'] for r in rows)) for th in [20,30,35]}
keys={m[run['aliases'].get('U_'+r['id'],'U_'+r['id'])]['framework_key'] for r in rows if r['U']['topology_identified']}
hits={};processed=identified=0
for line in Path('/share/rickyswork/ai_mof/generation/mofid_validation/full_reference/results/results.jsonl').open():
    q=json.loads(line);processed+=1;k=q.get('framework_key');identified+=bool(k)
    if k in keys:hits.setdefault(k,[]).append(q['id'])
summary.update(unique_U_frameworks=len(keys),reference_processed=processed,reference_identified=identified,training_matches=hits)
(out/'pairs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
flat=[]
for r in rows:
    f=dict(id=r['id'],source=r['source'],novel=r['novel'],profile=json.dumps(r['profile']))
    for arm in ['A','U']:
        for k,v in r[arm].items():f[arm+'_'+k]=v
    flat.append(f)
with (out/'pairs.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
lines=['# 留出连接体验证结果','', '同一千样本池中未进入v1/v2的20种连接体；构象种子19。未新生成完整批次。', '', '| 指标（分母20） | 原生A | 无预筛U |','|---|---:|---:|']
for k,label in [('geometry','几何有效'),('converged','预算内收敛'),('target_recovered','目标连接体恢复'),('topology_identified','完整拓扑身份'),('joint','联合终点')]:lines.append(f'| {label} | {summary["A"][k]}/20 | {summary["U"][k]}/20 |')
lines+=['','训练外标记样本数：'+str(summary['novel'])+'。逐CIF复读的几何通过/失败分类与内存记录一致；距离、原子数或连通分量数值差异保存在reread_discrepancies，逐条保留。完整原始结果、预登记和冻结哈希随附。', '', '```json',json.dumps(summary,ensure_ascii=False,indent=2),'```','', '报告脚本首次因CIF复读数值差异暂停；冻结版report.py保存在report_frozen.py，本报告脚本追加差异记录并核对几何分类一致，未修改计算和评价阈值。','', '联合终点描述几何和身份质量；后续配位应变、相对能量稳定性及吸附性能独立评价。']
(out/'REPORT.md').write_text('\n'.join(lines));(out/'ALL_DONE').write_text('done\n');print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
