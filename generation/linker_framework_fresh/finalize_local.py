"""Append post-selection fragment strata and continuous coordination diagnostics."""
import csv,json
from pathlib import Path
import numpy as np
from ase.io import read

p=Path(__file__).resolve().parent/'results'
s=json.loads((p/'summary.json').read_text());pairs=json.loads((p/'pairs.json').read_text());run=json.loads((p/'run.json').read_text())
training=json.loads((p/'training_fragment_audit.json').read_text());labels={r['id']:r for r in training['rows']}
strata={}
for key in ['raw_canonical_in_train','normalized_in_train']:
    strata[key]={}
    for present in [True,False]:
        rs=[r for r in pairs if labels[r['id']][key]==present]
        strata[key][str(present)]=dict(n=len(rs),**{arm:sum(r[arm]['joint'] for r in rs) for arm in ['A','U7','U19']})
coord=[]
for r in pairs:
    for arm in ['U7','U19']:
        name=arm+'_'+r['id'];canonical=run['aliases'].get(name,name);path=p/'relaxed'/(canonical+'.cif')
        if not path.exists():coord.append(dict(name=name,status=r[arm]['status']));continue
        a=read(path);zs=[i for i,x in enumerate(a.symbols) if x=='Zn'];ox=[i for i,x in enumerate(a.symbols) if x=='O'];d=a.get_all_distances(mic=True)
        for cutoff in [2.3,2.5,2.7]:
            counts=[];angles=[]
            for z in zs:
                ns=[o for o in ox if d[z,o]<=cutoff];counts.append(len(ns))
                if len(ns)==4:
                    v=a.get_distances(z,ns,mic=True,vector=True);v/=np.linalg.norm(v,axis=1)[:,None]
                    angles.extend(float(np.degrees(np.arccos(np.clip(v[i]@v[j],-1,1)))) for i in range(4) for j in range(i+1,4))
            coord.append(dict(name=name,status=r[arm]['status'],cutoff=cutoff,zn_count=len(zs),cn=counts,all_cn4=bool(zs) and all(c==4 for c in counts),angle_rms=float(np.sqrt(np.mean((np.array(angles)-np.degrees(np.arccos(-1/3)))**2))) if angles else None))
(p/'coordination.json').write_text(json.dumps(coord,indent=2))
s.update(training_fragment_strata=strata,training_fragment_unparsed_strings=training['unparsed_unique_strings'],coordination={str(c):dict(all_zn_cn4=sum(r.get('cutoff')==c and r.get('all_cn4',False) for r in coord),structures_with_cif=sum(r.get('cutoff')==c for r in coord)) for c in [2.3,2.5,2.7]})
(p/'summary.json').write_text(json.dumps(s,indent=2))
with (p/'REPORT.md').open('a',encoding='utf-8') as f:
    f.write('\n\n## 补充审计\n\n本批A直接使用新模型预测CIF；前两批A来自历史UFF输出，跨批次主表不能单独用于归因序列种子。训练片段标签在选样冻结后计算，采用组成必要条件预筛再作精确规范化匹配，未参与选样；参考中不可解析字符串数如实保留。\n\n```json\n'+json.dumps(dict(training_fragment_strata=strata,unparsed_training_strings=training['unparsed_unique_strings'],coordination=s['coordination']),ensure_ascii=False,indent=2)+'\n```\n\nZn–O截断2.3/2.5/2.7 Å均保留，四面体角RMS见coordination.json；失败构建和无输出未补样。源文件、冻结哈希、逐任务签名与映射复核见AUDIT.json。\n')
print(json.dumps(dict(strata=strata,coordination=s['coordination']),indent=2))
