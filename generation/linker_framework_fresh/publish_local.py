"""Render audited new-batch results after downloading the server archive."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Patch

root=Path(__file__).resolve().parent;out=root/'results';s=json.loads((out/'summary.json').read_text());rows=json.loads((out/'pairs.json').read_text());n=s['n'];arms=['A','U7','U19']
# Only normalize the display copy; archived historical metrics stay untouched.
if all('strict_joint' in s['arms'][arm] for arm in arms):
    for arm in arms:s['arms'][arm]['joint']=s['arms'][arm]['strict_joint']
    for row in rows:
        for arm in arms:row[arm]['joint']=row[arm]['strict_joint']
    s['both_seeds_pass']=s['both_seeds_strict_pass'];s['either_seed_pass']=s['either_seed_strict_pass']
fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained',gridspec_kw={'width_ratios':[1.25,1]})
x=np.arange(3)
for delta,key,label,color in [(-.2,'geometry','Geometry','#8b9bb2'),(0,'joint','Joint endpoint','#168b83'),(.2,'converged','Converged','#6379b4')]:
    bars=axes[0].bar(x+delta,[s['arms'][a][key] for a in arms],.19,label=label,color=color);axes[0].bar_label(bars,padding=3,fontsize=9)
axes[0].set(xticks=x,xticklabels=['Native A','Assembly seed 7','Assembly seed 19'],ylim=(0,n+4),ylabel=f'Passes / {n}',title='Independent sequence batch: seed 719');axes[0].legend(fontsize=9)
matrix=np.array([[2 if r[a]['joint'] and r[a]['converged'] else 1 if r[a]['joint'] else 0 for a in arms] for r in rows])
axes[1].imshow(matrix,cmap=ListedColormap(['#d5dae2','#e3af59','#168b83']),norm=BoundaryNorm([-.5,.5,1.5,2.5],3),aspect='auto')
axes[1].set(xticks=range(3),xticklabels=arms,yticks=range(n),yticklabels=[r['id'] for r in rows],title='Per-linker paired outcomes')
axes[1].legend(handles=[Patch(color=c,label=l) for c,l in [('#d5dae2','Joint endpoint failed'),('#e3af59','Joint pass; unconverged'),('#168b83','Joint pass; converged')]],loc='upper center',bbox_to_anchor=(.5,-.06),fontsize=8,ncol=1)
for ax in axes:ax.spines[['top','right']].set_visible(False)
fig.savefig(out/'comparison.png',dpi=180)
note=f'''\n\n## 2026-11-13：全新生成批次719完成\n\n固定生成200序列，化学筛选并排除已测试40种归一化连接体后得到{s['n']}种，全部冻结，无补采样。A原生、U7/U19双构象固定pcu/N16三臂联合终点分别{s['arms']['A']['joint']}/{n}、{s['arms']['U7']['joint']}/{n}、{s['arms']['U19']['joint']}/{n}；两种子均通过{s['both_seeds_pass']}/{n}、至少一种通过{s['either_seed_pass']}/{n}。唯一正式弛豫{s['unique_formal_jobs']}次。参考完整身份{s['reference_identified']}条，U身份命中{len(s['training_matches'])}种；部分解析缺口保留。\n\n证据：generation/linker_framework_fresh/results/REPORT.md、AUDIT.json及comparison.png。该批检验固定条件下的跨随机批次和双构象稳健性；条件响应、配位应变和吸附性能另评。DAO-P继续保留备选。\n'''
workspace=root.parent.parent
for name in ['worklog.md','PROJECT_MAP.md']:
    with (workspace/name).open('a',encoding='utf-8') as f:f.write(note)
p=workspace/'generation/build_workbench.py';text=p.read_text(encoding='utf-8');marker="for v in views:\n    v['desc']=v['desc'].replace('2026-11-12','2026-11-13')"
update=f'''fresh_evidence=['generation/linker_framework_fresh/PROTOCOL.md','generation/linker_framework_fresh/results/REPORT.md','generation/linker_framework_fresh/results/AUDIT.json']
nodes['p2test'].update(title='新批次与双构象验证完成',desc='200新序列→{n}种未测试连接体；序列种子719',findings=['A联合终点{s['arms']['A']['joint']}/{n}；U7 {s['arms']['U7']['joint']}/{n}；U19 {s['arms']['U19']['joint']}/{n}。','两构象均成功{s['both_seeds_pass']}/{n}，至少一种成功{s['either_seed_pass']}/{n}。'],evidence=fresh_evidence,next=['分析种子敏感案例，补条件响应与性能验证。'])
nodes['independent'].update(status='partial',findings=['新随机批次固定200序列，冻结{n}种连接体。','双构象均通过{s['both_seeds_pass']}/{n}，至少一种通过{s['either_seed_pass']}/{n}。'],evidence=fresh_evidence)
'''
assert marker in text;p.write_text(text.replace(marker,update+marker),encoding='utf-8');print(note)
