"""Update project evidence after the complete holdout results are downloaded."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
s=json.loads((root/'results/summary.json').read_text())
assert s['audit_pass'] and s['n']==20
fig,ax=plt.subplots(figsize=(7,4),layout='constrained')
bars=ax.bar(['Native A','Assembly U'],[s['A']['joint'],s['U']['joint']],color=['#8192a8','#168b87'])
ax.bar_label(bars,labels=[f'{s[a]["joint"]}/20' for a in ['A','U']],padding=4)
ax.set(ylim=(0,23),ylabel='Joint endpoint passes',title='20 held-out linkers | conformer seed 19')
ax.spines[['top','right']].set_visible(False)
fig.savefig(root/'results/comparison.png',dpi=180)
note=f'''\n\n## 2026-11-13：留出20连接体确认\n\n从同一千样本池中排除既有连接体及归一化同身份，固定哈希排序选20种，构象种子19。原生A联合终点{s['A']['joint']}/20、无预筛pcu/N16组装U {s['U']['joint']}/20；几何A {s['A']['geometry']}/20、U {s['U']['geometry']}/20；收敛A {s['A']['converged']}/20、U {s['U']['converged']}/20。旧20°门槛会拒绝{s['old_gate_cross_table']['20']['rejected']}个，其中{s['old_gate_cross_table']['20']['rejected_but_joint_pass']}个实际通过联合终点。\n\n本轮20种原序列片段均在训练集合中出现；验证范围是同生成批次的留出连接体。U获得{s['unique_U_frameworks']}种完整框架身份；训练参考已处理{s['reference_processed']}条、完整{s['reference_identified']}条，命中完整身份数{len(s['training_matches'])}。证据：generation/linker_framework_holdout/results/REPORT.md。下一阶段优先用全新生成批次与多构象种子复核，并补配位几何和稳定性评价。\n'''
workspace=root.parent.parent
for name in ['worklog.md','PROJECT_MAP.md']:
    with (workspace/name).open('a',encoding='utf-8') as f:f.write(note)
p=workspace/'generation/build_workbench.py';text=p.read_text(encoding='utf-8')
marker="for v in views:\n    v['desc']=v['desc'].replace('2026-11-12','2026-11-13')"
update=f'''holdout_evidence=['generation/linker_framework_holdout/PROTOCOL.md','generation/linker_framework_holdout/results/REPORT.md']
nodes['diagnose']['findings'] += ['留出20连接体：原生联合终点{s['A']['joint']}/20、无预筛组装{s['U']['joint']}/20；旧20°门槛拒绝{s['old_gate_cross_table']['20']['rejected']}个。']
nodes['diagnose']['evidence'] += holdout_evidence
nodes['p2test'].update(status='partial',title='留出验证完成 · 补全新生成批次',desc='新连接体20种、构象种子19；同千样本来源',findings=['A联合终点{s['A']['joint']}/20；U联合终点{s['U']['joint']}/20。','20个片段均为训练序列内；本轮验证同批次留出连接体。'],evidence=holdout_evidence,next=['全新生成批次、多构象种子与配位几何/稳定性检查。'])
nodes['independent'].update(status='partial',findings=['留出20连接体配对验证：A {s['A']['joint']}/20，U {s['U']['joint']}/20。','后续补全新生成批次、多构象种子与稳定性。'],evidence=holdout_evidence)
'''
assert marker in text
p.write_text(text.replace(marker,update+marker),encoding='utf-8')
print(note)
