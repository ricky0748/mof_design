import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],'axes.unicode_minus':False})
response=json.loads((P/'response_summary.json').read_text());names=list(response['groups']);colors=['#5785ac' if n.endswith('t2') else '#238b73' for n in names];labels=['1601\n目标2','1601\n目标5','1602\n目标2','1602\n目标5']
has_perf=(P/'performance/per_candidate.json').exists();has_structure=(P/'structure_summary.json').exists();fig,axs=plt.subplots(2 if has_perf else 1,2 if has_structure else 1,figsize=(12,9 if has_perf else 5),squeeze=False);ax=axs[0,0]
vals=[response['groups'][n]['eligible_sequences'] for n in names];bars=ax.bar(np.arange(4),np.array(vals)/600*100,color=colors)
for b,v in zip(bars,vals):ax.annotate(f'{v}/600',xy=(b.get_x()+b.get_width()/2,b.get_height()),xytext=(0,5),textcoords='offset points',ha='center')
ax.set_xticks(range(4),labels);ax.set(ylabel='符合当前连接体规则的序列（%）',title='改变条件，当前路线的兼容率是否改变？',ylim=(0,24))
if has_structure:
    structure=json.loads((P/'structure_summary.json').read_text());ax=axs[0,1];vals=[structure[n]['accepted'] for n in names];totals=[structure[n]['selected'] for n in names];bars=ax.bar(range(4),vals,color=colors)
    for b,v,t in zip(bars,vals,totals):ax.annotate(f'{v}/{t}',xy=(b.get_x()+b.get_width()/2,b.get_height()),xytext=(0,5),textcoords='offset points',ha='center')
    ax.set_xticks(range(4),labels);ax.set(ylabel='收敛且通过严格结构验收的候选数',title='冻结抽样后，最终得到多少可用结构？',ylim=(0,max(totals)+3))
if has_perf:
    per=json.loads((P/'performance/per_candidate.json').read_text())
    for ax,kind,title in [(axs[1,0],'widom','低压 Henry 选择性'),(axs[1,1],'gcmc','1 bar / CO2 1000 ppm 混合选择性')]:
        counts=[];positive=[]
        for i,n in enumerate(names):
            rs=[r for r in per if any(m['group']==n for m in r['memberships']) and r.get(kind+'_S_CO2') is not None];counts.append(len(rs));vs=[r[kind+'_S_CO2'] for r in rs if r[kind+'_S_CO2']>0];positive+=vs
            for j,r in enumerate(rs):
                v=r[kind+'_S_CO2']
                if v<=0:continue
                x=i+(j-(len(rs)-1)/2)*.035;ax.scatter(x,v,c=colors[i],marker='x' if r.get(kind+'_uncertain') else 'o',s=35)
        ax.set_xticks(range(4),[s+f'\nn={n}' for s,n in zip(labels,counts)]);ax.set(title=title,ylabel='S_CO2（越高越偏好吸附 CO2）',yscale='log' if positive else 'linear');ax.axhline(1,color='gray',ls='--',lw=.7)
    fig.text(.5,.015,'每点为一个候选的两个模拟种子均值；× 表示误差较大或零采样警示。零选择性不画在对数轴，详见逐候选表。',ha='center',fontsize=10)
for ax in axs.flat:ax.grid(alpha=.15,axis='y');ax.spines[['top','right']].set_visible(False)
fig.suptitle('目标条件响应与分离性能对照：同一模型、配对种子、统一结构处理',fontsize=16);fig.tight_layout(rect=[0,.04 if has_perf else 0,1,.94]);fig.savefig(P/'主线对照.png',dpi=170);plt.close(fig)
