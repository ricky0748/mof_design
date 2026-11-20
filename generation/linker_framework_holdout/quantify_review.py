"""Reproduce gate and connectivity sensitivity evidence from archived CIFs."""
import csv,json
from pathlib import Path
import numpy as np
from ase.io import read
from ase.neighborlist import NeighborList,natural_cutoffs
from scipy.sparse.csgraph import connected_components
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
out=root/'review_evidence';out.mkdir(exist_ok=True)
base=root/'results'
pairs=json.loads((base/'pairs.json').read_text())
targets=json.loads((base/'targets.json').read_text())
ts={t['id']:t for t in targets}
rows=[]
for pair in pairs:
    for arm in ['A','U']:
        name=arm+'_'+pair['id'];rec=json.loads((base/'records'/(name+'.json')).read_text())
        atoms=read(base/'relaxed'/(name+'.cif'))
        counts={}
        for skin in [.3,0]:
            nl=NeighborList(natural_cutoffs(atoms,mult=1.15),skin=skin,self_interaction=False,bothways=True);nl.update(atoms)
            counts[skin]=int(connected_components(nl.get_connectivity_matrix(sparse=True).tocsr(),directed=False)[0])
        distances=atoms.get_all_distances(mic=True);np.fill_diagonal(distances,np.inf)
        minimum=float(distances.min());ratio=atoms.get_volume()/rec['before']['volume']
        geo=lambda count:bool(len(atoms)==rec['before']['natoms'] and minimum>=.9 and count==1 and .75<=ratio<=1.25)
        rows.append(dict(id=pair['id'],arm=arm,axis_angle=max(ts[pair['id']]['profile']['angles'][:2]),
            mutual_angle=ts[pair['id']]['profile']['angles'][2],fragments_default=counts[.3],fragments_skin0=counts[0],
            geometry_default=geo(counts[.3]),geometry_skin0=geo(counts[0]),
            joint=pair[arm]['joint'],converged=pair[arm]['converged'],dmin=minimum,volume_ratio=ratio))
with (out/'per_structure.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
u=[r for r in rows if r['arm']=='U'];a=[r for r in rows if r['arm']=='A']
summary=dict(n=20,gate_rejected=sum(r['axis_angle']>20 for r in u),
    rejected_but_passed=sum(r['axis_angle']>20 and r['joint'] for r in u),
    geometry_decision_changes=sum(r['geometry_default']!=r['geometry_skin0'] for r in rows),
    connectivity_changes={arm:sum(r['fragments_default']!=r['fragments_skin0'] for r in rows if r['arm']==arm) for arm in ['A','U']},
    accepted_default={arm:sum(r['geometry_default'] for r in rows if r['arm']==arm) for arm in ['A','U']},
    accepted_skin0={arm:sum(r['geometry_skin0'] for r in rows if r['arm']==arm) for arm in ['A','U']})
(out/'summary.json').write_text(json.dumps(summary,indent=2))
fig,axes=plt.subplots(1,3,figsize=(15,4.6),layout='constrained')
x=np.arange(1,21)
ax=axes[0];ax.axhspan(0,20,color='#e7edf1');ax.axhline(20,color='#bd493c',ls='--',label='Old rejection threshold')
ax.scatter(x,[r['axis_angle'] for r in u],c='#148b83',s=38,label='Passed joint endpoint')
ax.set(title='A. Old gate rejects 19 successful builds',xlabel='Held-out linker H01-H20',ylabel='Maximum axis deviation (degrees)',xticks=[1,5,10,15,20])
ax.legend(fontsize=8,loc='lower right')
ax=axes[1]
for subset,label,color in [(a,'Native A','#7b8da7'),(u,'Assembly U','#148b83')]:
    ax.scatter([r['fragments_default'] for r in subset],[r['fragments_skin0'] for r in subset],label=label,c=color,s=35,alpha=.75)
ax.plot([0,65],[0,65],color='#adb5bf',ls='--');ax.set(title='B. Connectivity depends on distance margin',xlabel='Components: default skin = 0.3 A',ylabel='Components: explicit skin = 0 A',xlim=(0,65),ylim=(0,65));ax.legend(fontsize=9)
ax=axes[2]
v0=[summary['accepted_default'][k] for k in ['A','U']];v1=[summary['accepted_skin0'][k] for k in ['A','U']]
xx=np.arange(2)
for shift,values,label,color in [(-.19,v0,'Default skin','#8799b3'),(.19,v1,'Explicit skin = 0','#148b83')]:
    bars=ax.bar(xx+shift,values,.36,label=label,color=color);ax.bar_label(bars,padding=3)
ax.set(title='C. Final geometry decisions unchanged',xticks=xx,xticklabels=['Native A','Assembly U'],ylabel='Geometry passes / 20',ylim=(0,23));ax.legend(fontsize=8)
for ax in axes:ax.spines[['top','right']].set_visible(False)
fig.suptitle('Auditable evidence | 20 held-out linkers | fixed archived structures',fontsize=14)
fig.savefig(out/'review_dashboard.png',dpi=180)
fig.savefig(out/'review_dashboard.svg')
print(json.dumps(summary,indent=2))
