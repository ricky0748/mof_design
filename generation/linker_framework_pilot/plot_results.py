"""Static scientific figure for the frozen paired pilot."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path(__file__).resolve().parent/'results'
summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
pairs=json.loads((out/'pairs.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,(a,b)=plt.subplots(1,2,figsize=(12,4.2),gridspec_kw={'width_ratios':[1,1.25]},layout='constrained')
keys=['geometry_valid','target_recovered','topology_identified','joint_success']
x=np.arange(4)
for shift,arm,color,label in [(-.18,'A','#386f96','Native framework (A)'),(.18,'B','#c48635','pcu / Zn4O template (B)')]:
    vals=[summary[arm][k] for k in keys]
    bars=a.bar(x+shift,vals,.34,color=color,label=label)
    a.bar_label(bars,labels=[f'{v}/20' for v in vals],padding=4,fontsize=9)
a.set_xticks(x,['Geometry\nvalid','Target linker\nrecovered','Topology\nidentified','Joint\nendpoint'])
a.set_ylim(0,21);a.set_ylabel('Paired units (fixed denominator = 20)');a.legend(frameon=False,fontsize=8)
a.set_title('A  |  Matched treatment, all attempts counted',loc='left',fontsize=11,fontweight='bold')
angles=[max(p['direction_degrees']) for p in pairs]
colors=['#bd8032' if p['novel'] else '#397998' for p in pairs]
b.axhspan(0,20,color='#e7f1eb',zorder=0)
b.axhline(20,color='#54856b',linestyle='--',linewidth=1,label='Frozen compatibility threshold')
b.scatter(np.arange(1,21),angles,c=colors,s=40,zorder=3)
b.annotate('L14: compatible',xy=(14,angles[13]),xytext=(11,5),arrowprops={'arrowstyle':'->','color':'#617b70'},fontsize=9)
b.set_xticks([1,4,8,12,16,20]);b.set_xlabel('Frozen ligand ID');b.set_ylabel('Maximum connection-direction deviation (degrees)')
b.set_xlim(.2,20.8);b.set_ylim(0,39)
b.set_title('B  |  Template compatibility is the main loss',loc='left',fontsize=11,fontweight='bold')
b.text(.03,.95,'8 sequence-training-external linkers (orange)\n12 training-seen linkers (blue)',transform=b.transAxes,va='top',fontsize=8,color='#647887')
fig.suptitle('Linker-to-framework pilot | 20 fixed ligands | 2026-11-13',fontsize=13,fontweight='bold')
fig.savefig(out/'pilot_results.png',dpi=180,facecolor='white')
fig.savefig(out/'pilot_results.svg',facecolor='white')
print(out/'pilot_results.png')
