"""Append audited interpretation without changing frozen simulation code."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
out = ROOT / 'results'
audit = json.loads((out / 'AUDIT.json').read_text())
assert audit['verified'] and audit['audited_arms'] == 40
assert audit['unique_U_frameworks'] == 20 and not audit['training_matches']
text = '''
## 独立核查与解释更正（2026-11-13）

重新读取40个U/M臂的落盘CIF，独立重算最短距离、连通分量、原子数与体积变化；逐条对照官方MOFid连接体和拓扑。结果与主表一致，见 AUDIT.json。

上一轮把19次直线预筛拒绝解释为固定pcu模板不适配，这一判断过强。U组保留相同pcu/N16方案并取消该预筛，20/20通过联合终点，且全部在150步内收敛、拓扑均为pcu。主要改进来自解除过严的手工门槛。v2同时修正了L03、L07、L16的非羧酸负氧归一化，因此U与B1的差异包含这项修正；其余17个样本中，16个从预筛拒绝变为通过，L14保持通过。

M组17/20通过，未超过U组20/20。M_L04未收敛且拓扑ERROR；M_L08虽收敛且识别cds，但有2个连通分量；M_L17未收敛、目标连接体与拓扑均未完整恢复。M同时改变节点、金属和拓扑，结果按整个构建策略解释。

U组20个结果具有20种不同框架身份。对187047条训练参考逐条扫描，在171978条完整身份中没有匹配；15069条部分解析参考构成覆盖缺口。原始序列比较标记的8个训练外连接体，在U组8/8通过联合终点、M组6/8通过；这一分组沿用原canonical SMILES精确集合差口径。

本轮新增39次唯一正式弛豫和3次校准弛豫；M_L14与U_L14初始结构相同，复用一次计算。BDC与间苯二甲酸校准通过；库模板回建校准的几何、收敛、cds拓扑均通过，其目标连接体未预设，target_recovered和joint应读作不适用。

后续优先在独立连接体批次、冻结构象种子和相同预算下复核U方案，并保留原生结构配对基线。本轮是同一历史20样本上的诊断性实验。
'''
report = out / 'REPORT.md'
base = report.read_text(encoding='utf-8').split('\n## 独立核查与解释更正')[0]
report.write_text(base + '\n' + text, encoding='utf-8')
(ROOT / 'README.md').write_text('''# 连接体—框架组合试验 v2

已完成：同一20连接体、4臂比较、39次唯一新正式弛豫、3次校准、官方MOFid及独立落盘核查。

- [完整报告](results/REPORT.md)
- [逐样本结果](results/pairs.csv)
- [独立核查](results/AUDIT.json)
- [预登记](PROTOCOL.md)

联合终点为几何有效、目标连接体恢复、完整拓扑身份同时成立。A原生0/20、B1旧预筛1/20、U取消预筛20/20、M几何匹配17/20。results包含完整原始/弛豫CIF、逐任务记录和MOFid输出；results_bundle.tar.gz保留服务器原始归档。追加解释由finalize_report.py生成。
''', encoding='utf-8')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
s = json.loads((out / 'summary.json').read_text())
arms = ['A', 'B1', 'U', 'M']
fig, ax = plt.subplots(figsize=(8, 4.5), layout='constrained')
bars = ax.bar(['Native', 'Old gate', 'No gate', 'Geometry match'], [s[a]['joint'] for a in arms], color=['#8293a8', '#8293a8', '#168b87', '#5e6bc5'])
ax.bar_label(bars, labels=[f'{s[a]["joint"]}/20' for a in arms], padding=5)
ax.set(ylim=(0,23), ylabel='Joint endpoint passes', title='Same 20 linkers: paired framework assembly study')
ax.spines[['top','right']].set_visible(False)
fig.savefig(out / 'comparison.png', dpi=180)
print('Audited report and plot saved')
