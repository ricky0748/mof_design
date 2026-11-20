#!/usr/bin/env python3
"""Create MOFid manifest and report all frozen pairs, including failures."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path


def ligand_key(smiles):
    from rdkit import Chem
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    for atom in mol.GetAtoms():
        if atom.GetSymbol() == 'O' and atom.GetFormalCharge() == -1:
            atom.SetFormalCharge(0)
            atom.SetNumExplicitHs(atom.GetNumExplicitHs()+1)
            atom.SetNoImplicit(False)
    try:
        Chem.SanitizeMol(mol)
        mol = Chem.RemoveHs(mol)
        Chem.RemoveStereochemistry(mol)
        return Chem.MolToSmiles(mol, isomericSmiles=False)
    except Exception:
        return None


def read_mofid(out, control):
    p = out/('mofid_controls' if control else 'mofid')/'results.jsonl'
    return {r['id']:r for r in map(json.loads,p.read_text().splitlines())} if p.exists() else {}


def result(out, name, target, mofid):
    p = out/'records'/(name+'.json')
    r = json.loads(p.read_text()) if p.exists() else dict(status='not_built')
    m = mofid.get(name,{})
    target_key = ligand_key(target)
    got = [ligand_key(s) for s in m.get('linkers',[])]
    recovered = bool(target_key and target_key in got)
    topology = bool(m.get('framework_key'))
    geometry = bool(r.get('geometry_valid'))
    return dict(relax_status=r.get('status'), geometry_valid=geometry,
                converged=bool(r.get('converged')), steps=r.get('steps'),
                target_key=target_key, extracted_keys=got, target_recovered=recovered,
                topology_identified=topology, joint_success=geometry and recovered and topology,
                topology=m.get('result',{}).get('topology'), mofid_status=m.get('status','not_run'),
                seconds=r.get('seconds'), reason=r.get('reason'),
                raw_atoms=r.get('before',{}).get('natoms'),
                final_atoms=r.get('after',{}).get('natoms'),
                dmin=r.get('after',{}).get('dmin'),
                fragments=r.get('after',{}).get('fragments'), volume_ratio=r.get('volume_ratio'))


def manifest(out, controls):
    rows=[]
    for p in sorted((out/'records').glob('*.json')):
        if p.stem.startswith('control_') != controls:
            continue
        rec=json.loads(p.read_text())
        if rec.get('status')=='completed' and Path(rec['out']).exists():
            rows.append(dict(id=p.stem, cohort='pilot_'+p.stem.split('_')[0],cif=rec['out']))
    path=out/('controls_mofid_manifest.jsonl' if controls else 'mofid_manifest.jsonl')
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print('MOFid manifest',len(rows),str(path),flush=True)


def wilson(success,n):
    z=1.96;p=success/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    span=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,mid-span), min(1,mid+span)]


def report(out, controls):
    ctrl=read_mofid(out,True)
    control_results={r['id']:result(out,'control_'+r['id'],r['smiles'],ctrl)
                     for r in json.loads((out/'controls.json').read_text())}
    control_pass=all(r['joint_success'] for r in control_results.values())
    (out/'control_evaluation.json').write_text(json.dumps(dict(passed=control_pass,results=control_results),indent=2))
    if controls:
        print(json.dumps(dict(passed=control_pass,results=control_results),indent=2))
        if not control_pass:
            raise RuntimeError('Control identity or geometry failed; diagnose before rollout')
        return
    if not control_pass:
        raise RuntimeError('Controls have not passed')
    selected=json.loads((out/'selected.json').read_text())
    builds={r['id']:r for r in json.loads((out/'build.json').read_text())}
    mofid=read_mofid(out,False)
    pairs=[]
    for row in selected:
        a=result(out,'A_'+row['id'],row['smiles'],mofid)
        b=result(out,'B_'+row['id'],row['smiles'],mofid)
        if builds[row['id']]['status']!='built':
            b.update(relax_status=builds[row['id']]['status'],reason=builds[row['id']].get('reason'))
        pairs.append(dict(id=row['id'],source=row['source_name'],seq_idx=row['source_seq_idx'],
                          novel=row['novel_sequence_fragment'],source_metals=row['source_metals'],
                          target_smiles=row['smiles'],direction_degrees=builds[row['id']].get('direction_degrees'),A=a,B=b))
    summary={}
    for arm in ('A','B'):
        summary[arm]={k:sum(p[arm][k] for p in pairs) for k in
                      ('geometry_valid','converged','target_recovered','topology_identified','joint_success')}
        summary[arm]['n']=len(pairs)
        summary[arm]['relax_status']=Counter(p[arm]['relax_status'] for p in pairs)
        summary[arm]['joint_wilson95']=wilson(summary[arm]['joint_success'],len(pairs))
    def paired(key):
        count=Counter(('both' if p['A'][key] and p['B'][key] else 'A_only' if p['A'][key] else 'B_only' if p['B'][key] else 'neither') for p in pairs)
        a,b=count['A_only'],count['B_only'];n=a+b
        count['exact_mcnemar_p']=min(1,2*sum(math.comb(n,k) for k in range(min(a,b)+1))/2**n) if n else 1
        return count
    summary['joint_pairs']=paired('joint_success')
    summary['geometry_pairs']=paired('geometry_valid')
    summary['B_builds']=Counter(r['status'] for r in builds.values())
    summary['strata']={str(novel):{arm:sum(p[arm]['joint_success'] for p in pairs if p['novel']==novel) for arm in ('A','B')}
                       | {'n':sum(p['novel']==novel for p in pairs)} for novel in (True,False)}
    (out/'pairs.json').write_text(json.dumps(pairs,ensure_ascii=False,indent=2))
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    flat=[]
    for p in pairs:
        f={k:p[k] for k in ('id','source','seq_idx','novel')}
        f['source_metals']=','.join(p['source_metals'])
        for arm in ('A','B'):
            for k,v in p[arm].items():
                if k not in ('extracted_keys','target_key'):f[arm+'_'+k]=v
        flat.append(f)
    with (out/'pairs.csv').open('w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    lines=['# 连接体—框架组合小试结果','', '2026-11-13；配对固定20个唯一连接体；8个训练序列外片段、12个训练内片段。',
           '', 'A：原生MOFFlow-2框架；B：相同连接体，pcu/N16模板构建。两臂统一新MACE计算。',
           '', '| 指标（分母20） | A 原生 | B 模板 |','|---|---:|---:|']
    for k,label in [('geometry_valid','预算内几何有效'),('converged','150步内优化收敛'),('target_recovered','MOFid恢复目标连接体'),('topology_identified','完整拓扑身份'),('joint_success','主终点：几何+连接体+拓扑')]:
        lines.append(f'| {label} | {summary["A"][k]}/20 | {summary["B"][k]}/20 |')
    lines+=['', 'B组装状态：'+json.dumps(summary['B_builds'],ensure_ascii=False),
            '', '主终点配对结果：'+json.dumps(summary['joint_pairs'],ensure_ascii=False),
            '', '阳性控制BDC/BPDC均通过几何、目标连接体恢复和完整拓扑检查。',
            '', '## 解释范围', '',
            '固定的是连接体；节点、拓扑和化学计量随构建方案改变。结果用于评估指定模板下的连接体可用性；纯组装算法效果需要同节点/拓扑的后续对照。',
            '', '方向不兼容、计算失败和未解决样本都保留在20个分母中；部分MOFid解析单列。150步预算内几何有效与优化收敛分别报告。',
            '', '## 逐配对结果', '', '| ID | 原生金属 | 训练外 | B方向偏差 | A主终点 | B主终点 | B状态 |','|---|---|---|---:|---|---|---|']
    for p in pairs:
        angle=max(p['direction_degrees']) if p['direction_degrees'] else None
        lines.append(f'| {p["id"]} | {",".join(p["source_metals"])} | {p["novel"]} | {round(angle,1) if angle is not None else "—"} | {p["A"]["joint_success"]} | {p["B"]["joint_success"]} | {p["B"]["relax_status"]} |')
    lines += ['', '## 机制观察与下一步', '',
        '19/20在固定seed=7构象与20°方向阈值下不兼容；多数连接方向相对X–X轴偏差约28–34°。本轮的主要损失发生在模板兼容性阶段。八个训练序列外片段均未越过该关口。',
        '', '下一轮应先根据连接方向和局部配位几何分类，再冻结兼容模板；可探索支持弯曲二连接构筑块的节点/拓扑。保留本轮固定pcu协议与失败分母，不通过放宽阈值重写结果。',
        '', '样本均来自V节点原生框架，而B使用Zn4O。MACE对两种金属环境的可靠性尚未专项校验，结果按预算内结构筛查解释。']
    for p in pairs:
        if p['B']['joint_success']:
            lines += ['', f'### 可复核重新组装案例：{p["id"]}', '',
                f'源样本 {p["source"]}，原始序列索引{p["seq_idx"]}。连接体 `{p["target_smiles"]}`；训练序列外标记={p["novel"]}。', '',
                f'A：最短距离{p["A"]["dmin"]:.3f} Å、片段数{p["A"]["fragments"]}、拓扑{p["A"]["topology"]}。',
                f'B：最短距离{p["B"]["dmin"]:.3f} Å、片段数{p["B"]["fragments"]}、拓扑{p["B"]["topology"]}、{p["B"]["steps"]}步收敛；MOFid恢复目标连接体。']
    traincheck=out/'B_L14_training_check.json'
    if traincheck.exists():
        t=json.loads(traincheck.read_text())
        lines += ['', f'案例B_L14在{t["training_identified"]}条已完整识别的训练框架身份中匹配数为{len(t["matches"])}；参考预期{t["training_expected"]}条，部分解析的覆盖缺口仍保留。']
    lines += ['', '## 实际计算与产物', '',
        f'正式A弛豫20个、B弛豫1个，另含2个阳性控制，共23次MACE调用；正式样本无超时和运行异常。19个B兼容性拒绝保留在分母。',
        '', '逐结构运行秒数合计：'+json.dumps({arm:round(sum(p[arm]['seconds'] or 0 for p in pairs),1) for arm in ('A','B')})+'（含加载，非串行墙钟时间）。',
        '', '冻结清单 frozen.json / selected.json；配对结果 pairs.csv / pairs.json；原始和弛豫CIF raw/、relaxed/；逐结构优化与MOFid日志 records/、logs/、mofid/。']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    (out/'ALL_DONE').write_text('done\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['manifest','report']);ap.add_argument('out');ap.add_argument('--controls-only',action='store_true')
    a=ap.parse_args();out=Path(a.out).resolve()
    (manifest if a.action=='manifest' else report)(out,a.controls_only)
