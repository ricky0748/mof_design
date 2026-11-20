"""Local presentation of the frozen server outputs; no new scientific calculations."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],'axes.unicode_minus':False})
rows=json.loads((OUT/'per_structure.json').read_text());hist=json.loads((OUT/'histories.json').read_text());summary=json.loads((OUT/'summary.json').read_text())['primary_26'];primary=[r for r in rows if r['primary'] and r['status']=='completed']
fig,axs=plt.subplots(2,2,figsize=(13,9));fig.suptitle(f"26 个已交付结构的严格精修：{summary['converged']} 个收敛，{summary['strict']} 个通过结构验收",fontsize=17)
for r in primary:
    h=hist[r['name']];n=r['final_natoms'];x=[p['step'] for p in h]
    axs[0,0].plot(x,[(p['energy']-h[0]['energy'])/n for p in h],alpha=.55,lw=1)
    axs[0,1].plot(x,[p['filter_fmax'] for p in h],alpha=.55,lw=1)
axs[0,0].set(title='继续优化后，势能还下降了多少？',xlabel='本轮追加优化步数',ylabel='相对起点的能量变化（eV/原子）')
axs[0,1].set(title='最大广义力是否降到停止阈值？',xlabel='本轮追加优化步数',ylabel='变胞优化器最大广义力',yscale='log');axs[0,1].axhline(.05,color='black',ls='--',label='本轮阈值 0.05');axs[0,1].axhline(.2,color='gray',ls=':',label='原阈值 0.2');axs[0,1].legend()
x=np.arange(len(primary));axs[1,0].bar(x,[r['volume_change_percent'] for r in primary],color='#278682');axs[1,0].set_xticks(x,[r['name'].split('_')[1] for r in primary],rotation=90);axs[1,0].set(title='精修前后，晶胞体积改变多少？',ylabel='相对精修起点的体积变化（%）');axs[1,0].axhline(0,color='gray',lw=.7)
for r in primary:
    a=r['angle_rms_before_2.5'];b=r['angle_rms_after_2.5']
    if a is not None and b is not None:axs[1,1].scatter(a,b,color='#278682',s=25)
limits=axs[1,1].get_xlim()+axs[1,1].get_ylim();low=min(limits);high=max(limits);axs[1,1].plot([low,high],[low,high],ls='--',color='gray',lw=1);axs[1,1].set(xlim=(low,high),ylim=(low,high),title='Zn 配位角偏差是否改变？（邻居截断 2.5 Å）',xlabel='精修前：四配位 Zn 的角度 RMS 偏差（°）',ylabel='精修后：角度 RMS 偏差（°）')
for ax in axs.flat:ax.grid(alpha=.15,axis='y');ax.spines[['top','right']].set_visible(False)
fig.text(.5,.012,'每条曲线/每根柱/每个点对应一个既有交付结构；角度图仅统计四配位 Zn，缺失不补值。',ha='center',fontsize=10)
fig.tight_layout(rect=[0,.035,1,.95]);fig.savefig(OUT/'收敛精修对照.png',dpi=170);plt.close(fig)
