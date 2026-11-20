import argparse
from collections import Counter
import csv,json,math
from pathlib import Path
from common import ligand_key


def load_ids(path):
    return {r['id']:r for r in map(json.loads,path.read_text().splitlines())} if path.exists() else {}


def evaluate(name,target,base,mofid,aliases=None,builds=None):
    canonical=(aliases or {}).get(name,name)
    p=base/'records'/(name+'.json')
    r=json.loads(p.read_text()) if p.exists() else dict(status=(builds or {}).get(name,{}).get('status','not_built'))
    m=mofid.get(canonical,{})
    expected=ligand_key(target) if target else None
    recovered=bool(expected and expected in [ligand_key(s) for s in m.get('linkers',[])])
    geo=bool(r.get('geometry_valid'));topo=bool(m.get('framework_key'))
    return dict(status=r['status'],geometry=geo,converged=bool(r.get('converged')),
        target_recovered=recovered,topology_identified=topo,joint=geo and topo and recovered,
        topology=m.get('result',{}).get('topology'),mofid_status=m.get('status','not_run'),
        reused_from=r.get('reused_from'),seconds=r.get('seconds'),steps=r.get('steps'),
        dmin=r.get('after',{}).get('dmin'),fragments=r.get('after',{}).get('fragments'),
        volume_ratio=r.get('volume_ratio'),target_key=expected)


def paired(rows,left,right):
    c=Counter('both' if r[left]['joint'] and r[right]['joint'] else 'left_only' if r[left]['joint'] else 'right_only' if r[right]['joint'] else 'neither' for r in rows)
    a,b=c['left_only'],c['right_only'];n=a+b
    return dict(c,exact_mcnemar_p=min(1,2*sum(math.comb(n,k) for k in range(min(a,b)+1))/2**n) if n else 1)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--controls-only',action='store_true');a=ap.parse_args();out=Path(a.out).resolve()
    controls=json.loads((out/'controls.json').read_text())
    cm=load_ids(out/'mofid_controls/results.jsonl');ca=json.loads((out/'controls_run.json').read_text())['aliases']
    control_results={r['id']:evaluate('control_'+r['id'],r.get('smiles'),out,cm,ca) for r in controls}
    calibration=dict(linear_positive_pass=control_results['C_BDC']['joint'],results=control_results)
    (out/'calibration.json').write_text(json.dumps(calibration,ensure_ascii=False,indent=2))
    if a.controls_only:
        print(json.dumps(calibration,indent=2));return
    if not calibration['linear_positive_pass']:raise RuntimeError('Linear calibration failed')
    old=Path('/share/rickyswork/ai_mof/generation/linker_framework_pilot_20261113')
    om=load_ids(old/'mofid/results.jsonl');oldpairs={r['id']:r for r in json.loads((old/'pairs.json').read_text())}
    bm={r['name']:r for r in json.loads((out/'build.json').read_text())}
    nm=load_ids(out/'mofid/results.jsonl');run=json.loads((out/'run.json').read_text())
    targets=json.loads((out/'targets.json').read_text());decisions={d['id']:d for d in json.loads((out/'decisions.json').read_text())}
    templates={t['name']:t for t in json.loads((out/'templates.json').read_text())}
    rows=[]
    for t in targets:
        id=t['id'];s=t['smiles']
        row=dict(id=id,smiles=s,novel=t['novel'],source=t['source_name'],normalization_changed=t['normalization_changed'])
        row['A']=evaluate('A_'+id,s,old,om)
        row['B1']=evaluate('B_'+id,s,old,om,builds={'B_'+id:dict(status='incompatible')})
        for arm in ('U','M'):row[arm]=evaluate(arm+'_'+id,s,out,nm,run['aliases'],bm)
        chosen=decisions[id]['match']
        row['chosen_match']=chosen;row['matched_template']=templates[chosen['template']] if chosen else None
        row['same_U_M_structure']=run['fingerprints'].get('U_'+id) is not None and run['fingerprints'].get('U_'+id)==run['fingerprints'].get('M_'+id)
        row['legacy_A_target_recovered']=oldpairs[id]['A']['target_recovered']
        rows.append(row)
    summary={}
    for arm in ('A','B1','U','M'):
        summary[arm]={k:sum(r[arm][k] for r in rows) for k in ('geometry','converged','target_recovered','topology_identified','joint')}
        summary[arm]['n']=20;summary[arm]['statuses']=Counter(r[arm]['status'] for r in rows)
    summary.update(U_vs_B1=paired(rows,'B1','U'),M_vs_U=paired(rows,'U','M'),M_vs_A=paired(rows,'A','M'),
        same_U_M_structures=sum(r['same_U_M_structure'] for r in rows),
        unique_formal_relaxations=len(run['canonical_jobs']),formal_aliases=len(run['aliases']),
        corrected_normalizations=[r['id'] for r in rows if r['normalization_changed']],
        A_recovery_count_legacy=sum(r['legacy_A_target_recovered'] for r in rows),
        strata={str(n):{'n':sum(r['novel']==n for r in rows),**{arm:sum(r[arm]['joint'] for r in rows if r['novel']==n) for arm in ('A','B1','U','M')}} for n in (True,False)})
    (out/'pairs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(out/'summary.json').write_text(json.dumps(summary,indent=2))
    flat=[]
    for r in rows:
        d={k:r[k] for k in ('id','source','novel','normalization_changed','same_U_M_structure')}
        d['template']=r['chosen_match']['template'] if r['chosen_match'] else None
        for arm in ('A','B1','U','M'):
            for k,v in r[arm].items():d[arm+'_'+k]=v
        flat.append(d)
    with (out/'pairs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    lines=['# 连接体—框架组合小试 v2','', '2026-11-13，同一20个连接体；A和B1复用v1计算，连接体恢复按仅中和羧酸根的函数重算。',
        '', 'A：原生V框架；B1：固定pcu/N16加直线20°门槛；U：固定pcu/N16不作直线预拒绝；M：相对已观测参考连接方向与长度匹配。',
        '', '| 指标（分母20） | A | B1 | U | M |','|---|---:|---:|---:|---:|']
    for key,label in [('geometry','预算内几何有效'),('converged','150步内收敛'),('target_recovered','恢复目标连接体'),('topology_identified','完整拓扑身份'),('joint','联合主终点')]:
        lines.append('| '+label+' | '+' | '.join(str(summary[arm][key])+'/20' for arm in ('A','B1','U','M'))+' |')
    lines+=['', '## 实际结构与计算覆盖', '',
        f'U/M完全相同初始结构：{summary["same_U_M_structures"]}/20。正式唯一弛豫{summary["unique_formal_relaxations"]}次、别名复用{summary["formal_aliases"]}个；同一结构不当成模板改变收益。',
        '', '归一化更正样本：'+json.dumps(summary['corrected_normalizations'])+'；旧A目标恢复数'+str(summary['A_recovery_count_legacy'])+'，更正后'+str(summary['A']['target_recovered'])+'。',
        '', '## 配对与分层', '', '```json', json.dumps({k:summary[k] for k in ('U_vs_B1','M_vs_U','M_vs_A','strata')},ensure_ascii=False,indent=2),'```',
        '', '## 解释范围', '',
        'U−B1用于检验直线门槛造成的拒绝；M−U用于比较几何匹配策略。M改变节点/拓扑时，是构建方案整体干预。模板池以既有几何有效为条件，其完整化学与拓扑身份仍在本轮独立核查。',
        '', '同一历史20样本上调试后的诊断性结果需要独立批次确认。几何有效与优化收敛分开；部分解析、工具失败、无匹配和超时保留在原始分母。',
        '', '## 逐样本', '', '| ID | 训练外 | M模板 | U主终点 | M主终点 | 同一初始结构 |','|---|---|---|---|---|---|']
    for r in rows:lines.append(f'| {r["id"]} | {r["novel"]} | {r["chosen_match"]["template"] if r["chosen_match"] else "无匹配"} | {r["U"]["joint"]} | {r["M"]["joint"]} | {r["same_U_M_structure"]} |')
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');(out/'ALL_DONE').write_text('done\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
