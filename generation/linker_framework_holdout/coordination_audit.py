"""Exploratory Zn4O local-geometry audit; no retrospective pass/fail tuning."""
import csv,json,re
from pathlib import Path
import numpy as np
from ase.io import read
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'coordination_evidence';OUT.mkdir(exist_ok=True)
def local(at,cutoff):
    zn=[i for i,s in enumerate(at.symbols) if s=='Zn'];ox=[i for i,s in enumerate(at.symbols) if s=='O']
    distances=[];counts=[];angles=[]
    for z in zn:
        neighbors=[o for o in ox if at.get_distance(z,o,mic=True)<=cutoff]
        counts.append(len(neighbors));distances.extend(at.get_distances(z,neighbors,mic=True).tolist())
        if len(neighbors)==4:
            vec=at.get_distances(z,neighbors,mic=True,vector=True);vec/=np.linalg.norm(vec,axis=1)[:,None]
            angles.extend(float(np.degrees(np.arccos(np.clip(vec[i]@vec[j],-1,1)))) for i in range(4) for j in range(i+1,4))
    ideal=np.degrees(np.arccos(-1/3))
    return dict(zn_count=len(zn),cn=counts,cn4=sum(c==4 for c in counts),
        bond_min=min(distances) if distances else None,bond_max=max(distances) if distances else None,
        angle_rms=float(np.sqrt(np.mean((np.array(angles)-ideal)**2))) if angles else None,
        angle_min=min(angles) if angles else None,angle_max=max(angles) if angles else None)

rows=[]
for cohort,base,prefix in [('discovery',ROOT.parent/'linker_framework_pilot_v2/results','U_L'),('holdout',ROOT/'results','U_H')]:
    names=sorted(p.stem for p in (base/'relaxed').glob(prefix+'*.cif'))
    names+=['control_C_BDC']
    for name in names:
        raw=read(base/'raw'/(name+'.cif'));relaxed=read(base/'relaxed'/(name+'.cif'))
        text=(base/'records'/(name+'.opt.log')).read_text()
        history=[(float(m[0]),float(m[1])) for m in re.findall(r'BFGS:\s+\d+\s+\S+\s+([-+\d.eE]+)\s+([-+\d.eE]+)',text)]
        rec=json.loads((base/'records'/(name+'.json')).read_text())
        for cutoff in [2.3,2.5,2.7]:
            r=dict(cohort=cohort,id=name,control=name.startswith('control'),cutoff=cutoff,converged=rec['converged'],natoms=len(relaxed))
            for stage,at in [('raw',raw),('relaxed',relaxed)]:
                for k,v in local(at,cutoff).items():r[stage+'_'+k]=v
            r.update(initial_energy=history[0][0],final_energy=history[-1][0],energy_change_per_atom=(history[-1][0]-history[0][0])/len(relaxed),final_optimizer_fmax=history[-1][1])
            rows.append(r)
with (OUT/'per_structure.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={}
for cutoff in [2.3,2.5,2.7]:
    formal=[r for r in rows if r['cutoff']==cutoff and not r['control']]
    summary[str(cutoff)]=dict(structures=len(formal),all_zn_cn4=sum(r['relaxed_cn4']==r['relaxed_zn_count'] for r in formal),
        zn_sites=sum(r['relaxed_zn_count'] for r in formal),cn4_sites=sum(r['relaxed_cn4'] for r in formal),
        coordination_outliers=[dict(id=r['id'],cn=r['relaxed_cn']) for r in formal if r['relaxed_cn4']!=r['relaxed_zn_count']])
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
formal=[r for r in rows if r['cutoff']==2.5 and not r['control']];controls=[r for r in rows if r['cutoff']==2.5 and r['control']]
fig,axes=plt.subplots(1,3,figsize=(14,4.2),layout='constrained')
for cohort,color in [('discovery','#617ab4'),('holdout','#148b83')]:
    rs=[r for r in formal if r['cohort']==cohort];xs=list(range(1,len(rs)+1))
    axes[0].scatter(xs,[r['relaxed_angle_rms'] for r in rs],label=cohort,c=color,s=25)
    axes[1].scatter(xs,[r['energy_change_per_atom'] for r in rs],label=cohort,c=color,s=25)
    axes[2].scatter(xs,[r['final_optimizer_fmax'] for r in rs],label=cohort,c=color,s=25)
axes[0].axhline(controls[0]['relaxed_angle_rms'],ls='--',color='#bc684d',label='BDC control')
axes[0].set(title='Zn local tetrahedral distortion',ylabel='O-Zn-O angle RMS vs ideal (degrees)')
axes[1].set(title='Relaxation energy change',ylabel='Final - initial energy (eV / atom)')
axes[2].axhline(.2,ls='--',color='#bc684d',label='Budget convergence target')
axes[2].set(title='Residual optimizer force',ylabel='FrechetCellFilter optimizer fmax')
for ax in axes:ax.set_xlabel('Linker index within cohort');ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=7)
fig.savefig(OUT/'coordination_dashboard.png',dpi=180)
lines=['# Zn4O配位几何探索性审计','', '对两批40个U结构与2个BDC控制的原始/弛豫CIF逐一复算。Zn–O邻居截断2.3、2.5、2.7 Å同时报告，未据结果设立新通过阈值。角度偏差仅在四配位Zn上计算。', '', '```json',json.dumps(summary,ensure_ascii=False,indent=2),'```','', '优化能量变化是在同一结构组成内的初末差，反映弛豫过程；它未计算分解参考或形成能，不直接作为热力学稳定性指标。优化器fmax来自变胞FrechetCellFilter，包含晶胞自由度。', '', '逐结构数据见per_structure.csv；原计算与既有联合终点不变。']
(OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(summary,indent=2))
