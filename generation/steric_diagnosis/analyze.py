"""Reproduce seed-sensitive collision evidence without running a calculator."""
import json,re
from pathlib import Path
import numpy as np
from ase.io import read
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import connected_components
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent;base=root.parent/'linker_framework_fresh/results';rows=[];cases=[]
for f in sorted((base/'records').glob('U*_*.json')):
    r=json.loads(f.read_text());hist=re.findall(r'BFGS:\s+\d+\s+\S+\s+([-+\d.eE]+)\s+([-+\d.eE]+)',(base/'records'/(f.stem+'.opt.log')).read_text())
    rows.append(dict(name=f.stem,before=r['before']['dmin'],after=r['after']['dmin'],geometry=r['geometry_valid'],initial_force=float(hist[0][1]),last_force=float(hist[-1][1]),initial_energy=float(hist[0][0]),last_energy=float(hist[-1][0])))
for name in ['U7_F11','U19_F11','U7_F14','U19_F14']:
    a=read(base/'raw'/(name+'.cif'),store_tags=True);tags=a.info;labels=tags['_atom_site_label'];index={v:i for i,v in enumerate(labels)};g=lil_matrix((len(a),len(a)),dtype=int)
    for x,y in zip(tags['_geom_bond_atom_site_label_1'],tags['_geom_bond_atom_site_label_2']):
        i,j=index[x],index[y]
        if a[i].symbol!='Zn' and a[j].symbol!='Zn':g[i,j]=g[j,i]=1
    _,group=connected_components(g.tocsr(),directed=False);d=a.get_all_distances(mic=True);details=[]
    for i,j in np.argwhere(np.triu(d<.9,k=1)):
        details.append(dict(a=labels[i],b=labels[j],distance=float(d[i,j]),same_organic_group=bool(group[i]==group[j]),symbols=a[i].symbol+'-'+a[j].symbol))
    cases.append(dict(name=name,contacts=sorted(details,key=lambda r:r['distance'])))
(root/'initial_analysis.json').write_text(json.dumps(dict(all_36=rows,clashes=cases),indent=2))
fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained')
for passed,color,label in [(True,'#168b83','Geometry passed'),(False,'#c65747','Geometry failed')]:
    rs=[r for r in rows if r['geometry']==passed];ax.scatter([r['before'] for r in rs],[r['initial_force'] for r in rs],c=color,label=label,s=40)
for r in rows:
    if r['name'] in ['U7_F11','U7_F14','U19_F04']:
        ax.annotate(r['name'],(r['before'],r['initial_force']),xytext=(8,5),textcoords='offset points',fontsize=9)
ax.set(yscale='log',xlabel='Initial minimum interatomic distance (A)',ylabel='Initial optimizer fmax (log scale)',title='36 initial structures: close contact alone does not separate failures')
ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=9);fig.savefig(root/'initial_contacts.png',dpi=180)
(root/'REPORT.md').write_text('''# 构象敏感案例的初始碰撞诊断

对新批次36个组装输入与对应优化日志复算。F11种子7存在3对<0.9 Å接触，F14有10对；这些接触位于去除Zn后不同的有机成键连通组之间，支持连接体间堆积碰撞的解释。种子19的同连接体没有<0.9 Å接触。

F14种子7初始最短C–C距离0.376 Å，优化器fmax从76157升至361417，能量从3810降至−54414 eV；F11亦出现能量异常降低且力增大的轨迹。记录支持优化失稳的判断，未将异常低能量解释为稳定性收益。

U19_F04起始最短距离0.490 Å仍成功，说明单凭初始距离设硬拒绝会误拒；没有据此新增距离或力阈值。完整数值与接触原子标签见initial_analysis.json，图见initial_contacts.png。
''',encoding='utf-8')
