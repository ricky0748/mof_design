import json,csv,re
from pathlib import Path
import numpy as np
from ase.io import read
from common import ligand_key
from relax_one import metrics

def coordination(a,cutoff):
    zn=[i for i,s in enumerate(a.symbols) if s=='Zn'];ox=[i for i,s in enumerate(a.symbols) if s=='O'];counts=[];angles=[];ds=[]
    for z in zn:
        ns=[o for o in ox if a.get_distance(z,o,mic=True)<=cutoff];counts.append(len(ns));ds.extend(a.get_distances(z,ns,mic=True).tolist())
        if len(ns)==4:
            v=a.get_distances(z,ns,mic=True,vector=True);v/=np.linalg.norm(v,axis=1)[:,None]
            angles.extend(np.degrees(np.arccos(np.clip(v[i]@v[j],-1,1))) for i in range(4) for j in range(i+1,4))
    return dict(cn=counts,angle_rms=float(np.sqrt(np.mean((np.array(angles)-np.degrees(np.arccos(-1/3)))**2))) if angles else None,bond_min=min(ds),bond_max=max(ds))

p=Path(__file__).resolve().parent
m={r['id']:r for r in map(json.loads,(p/'mofid/results.jsonl').read_text().splitlines())}
rows=[]
for t in json.loads((p/'selected.json').read_text()):
    name=t['name'];r=json.loads((p/'records'/(name+'.json')).read_text());row=dict(name=name,reason=t['reason'],status=r['status'],converged=r.get('converged',False))
    if r['status']=='completed':
        before=read(p/'raw'/(name+'.cif'));after=read(p/'relaxed'/(name+'.cif'))
        row.update(steps=r['steps'],geometry=r['geometry_valid'],before=metrics(before),after=metrics(after),volume_ratio=r['volume_ratio'])
        row['coordination']={str(c):dict(before=coordination(before,c),after=coordination(after,c)) for c in [2.3,2.5,2.7]}
        log=(p/'records'/(name+'.opt.log')).read_text();hist=re.findall(r'BFGS:\s+\d+\s+\S+\s+([-+\d.eE]+)\s+([-+\d.eE]+)',log)
        row.update(final_fmax=float(hist[-1][1]),energy_change_per_atom=(float(hist[-1][0])-float(hist[0][0]))/len(after))
    mr=m.get(name,{})
    row.update(mofid_status=mr.get('status','not_run'),topology=mr.get('result',{}).get('topology'),target_recovered=ligand_key(t['smiles']) in [ligand_key(s) for s in mr.get('linkers',[])])
    rows.append(row)
(p/'summary.json').write_text(json.dumps(rows,indent=2))
lines=['# 配位几何收敛复核结果','', '4个定向诊断样本与1个BDC控制；在旧弛豫结果上最多新增300步，fmax0.05。', '', '| 结构 | 新增步数 | 收敛 | 角RMS前→后（2.5 Å） | MOFid拓扑 | 保留连接体 |','|---|---:|---|---|---|---|']
for r in rows:
    c=r.get('coordination',{}).get('2.5',{})
    angle=f'{c["before"]["angle_rms"]:.2f} → {c["after"]["angle_rms"]:.2f}' if c else 'NA'
    lines.append(f'| {r["name"]} | {r.get("steps","NA")} | {r["converged"]} | {angle} | {r["topology"]} | {r["target_recovered"]} |')
lines+=['', '完整三个截断配位数、距离、体积、能量变化见summary.json。本次是结果驱动的诊断性复核，未改变原150步预算下的统计。能量变化未以分解产物为参考，热力学稳定性仍待单独评价。']
(p/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8');(p/'ALL_DONE').write_text('done\n');print(json.dumps(rows,indent=2))
