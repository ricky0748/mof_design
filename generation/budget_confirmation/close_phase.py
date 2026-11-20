"""Local delivery after the frozen server run and its audit have completed."""
import json,shutil,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Patch

root=Path(__file__).resolve().parent;p=root/'results';s=json.loads((p/'summary.json').read_text());audit=json.loads((p/'AUDIT.json').read_text());assert audit['passed']
rows=json.loads((p/'pairs.json').read_text());n=s['n'];strategies=['A300','S300','D'];recommend={'S':'S300'}.get(s['final_recommendation'],s['final_recommendation'])
fig,axes=plt.subplots(1,3,figsize=(16,6.5),layout='constrained',gridspec_kw={'width_ratios':[1,1,1.2]})
for i,key in enumerate(strategies):
    r=s['strategies'][key];color=['#8b9bb2','#637bb5','#168b83'][i]
    axes[0].bar(i,r['rate'],color=color,width=.6);lo,hi=r['wilson95'];axes[0].vlines(i,lo,hi,color='#354458');axes[0].text(i,r['rate']+.04,f'{r["success"]}/{n}',ha='center')
    cost=r['seconds_per_valid'];ci=s['paired_bootstrap']['cost_per_valid95'][key]['interval']
    if cost is not None:
        axes[1].scatter(i,cost,c=color,s=60)
        if ci:axes[1].vlines(i,ci[0],ci[1],color=color,lw=2)
        axes[1].annotate(f'{cost:.1f}',(i,cost),xytext=(8,4),textcoords='offset points',fontsize=9)
    else:axes[1].text(i,.1,'No valid\noutput',ha='center',transform=axes[1].get_xaxis_transform(),fontsize=9)
axes[0].set(xticks=range(3),xticklabels=['Native 300','Single 300','Dual 2x150'],ylim=(0,1.18),ylabel='Strict pass rate; Wilson 95% interval',title='Equal maximum step budget')
axes[1].set(xticks=range(3),xticklabels=['Native 300','Single 300','Dual 2x150'],ylabel='GPU-task wall seconds per valid candidate',title='Actual cost; paired bootstrap 95% interval')
axes[1].set_yscale('log')
def cell(r,a):
    q=r[a]['strict_joint'];conv=r[a].get('converged_candidate',r[a].get('converged',False));return 2 if q and conv else 1 if q else 0
mat=np.array([[cell(r,a) for a in ['A300','S300','D7','D19','D']] for r in rows])
axes[2].imshow(mat,cmap=ListedColormap(['#d5dae2','#e3af59','#168b83']),norm=BoundaryNorm([-.5,.5,1.5,2.5],3),aspect='auto')
axes[2].set(xticks=range(5),xticklabels=['A300','S300','D7','D19','D any'],yticks=range(n),yticklabels=[r['id'] for r in rows],title=f'Frozen {n}-linker paired outcomes');axes[2].tick_params(axis='y',labelsize=7)
axes[2].legend(handles=[Patch(color=c,label=l) for c,l in [('#d5dae2','Strict endpoint failed'),('#e3af59','Pass, not converged'),('#168b83','Pass and converged')]],loc='upper center',bbox_to_anchor=(.5,-.06),fontsize=8)
for ax in axes:ax.spines[['top','right']].set_visible(False)
fig.savefig(p/'comparison.png',dpi=180);fig.savefig(p/'comparison.svg')

# Produce one deterministic representative per passing candidate. In D prefer a
# converged passing branch, then fixed seed7 order; success/cost statistics do not change.
deliver=root/'deliverables';cifs=deliver/'cifs';cifs.mkdir(parents=True,exist_ok=True)
aliases=json.loads((p/'mofid_aliases.json').read_text());m={r['id']:r for r in map(json.loads,(p/'mofid/results.jsonl').read_text().splitlines())};manifest=[]
matched_samples={name for hit in s['identity']['matches'] for name in hit['samples']}
for row in rows:
    if recommend=='D':
        choices=[a for a in ['D7','D19'] if row[a]['strict_joint']];choices.sort(key=lambda a:not row[a]['converged'])
        branch=choices[0] if choices else None
    else:branch=recommend if recommend in strategies and row[recommend]['strict_joint'] else None
    if branch is None:continue
    name=branch+'_'+row['id'];record=json.loads((p/'records'/(name+'.json')).read_text());source=p/'relaxed'/Path(record['out']).name
    dest=cifs/(row['id']+'.cif');shutil.copyfile(source,dest);digest=hashlib.sha256(dest.read_bytes()).hexdigest();assert digest==record['output_sha256']
    manifest.append(dict(id=row['id'],branch=branch,smiles=row['smiles'],converged=row[branch]['converged'],sha256=digest,cif=str(dest.relative_to(deliver)),source_output=Path(record['out']).name,framework_key=m[aliases.get(name,name)]['framework_key'],training_framework_match=name in matched_samples,training_fragment=row['training']))
(deliver/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
expected=s['strategies'][recommend]['success'] if recommend in strategies else 0;assert len(manifest)==expected

reason_names=dict(higher_yield_within_20pct_cost='双构象通过数更高，且每有效框架成本增幅不超过预登记20%',same_yield_at_least_20pct_cheaper='通过数相同，双构象成本至少降低20%',simpler_same_yield='通过数相同，采用更简单的单构象',dual_lower_yield='双构象通过数较低',dual_gain_costs_more_than_20pct='双构象有质量收益，但成本增幅超过预登记20%，默认单构象并保留取舍',only_dual_succeeds='仅双构象产生通过候选',neither_strategy_succeeds='两种组合策略都未产生通过候选')
name_map=dict(A300='原生300步',S300='单构象种子7、300步',D='双构象种子7/19、各150步',unconfirmed='固定模板路线未确认')
selection_reason='原生通过数不低于推荐组合策略，且计入原生坐标预测后每有效框架成本仍不高' if recommend=='A300' else reason_names[s['decision']['reason']]
lines=['# 结构生成确认阶段：结项报告','',f'状态：本阶段已结束。推荐默认方案：**{name_map[recommend]}**。', '',selection_reason+'。该建议按计算前登记规则形成，范围限于本批与当前实现。','', '## 同预算结果','', '| 策略 | 严格成功 | 任务墙钟秒/有效框架 |','|---|---:|---:|']
for key in strategies:
    v=s['strategies'][key];cost=f'{v["seconds_per_valid"]:.2f}' if v['seconds_per_valid'] is not None else '无有效输出'
    lines.append(f'| {name_map[key]} | {v["success"]}/{n} | {cost} |')
lines+=['',f'600条固定采样 → {json.loads((p/"selection_frozen.json").read_text())["eligible"]}种合格且未测试身份 → 哈希冻结{n}种。排除旧58种身份，选样不读取结构结果或训练标签。', '', '## 预算与成本解释','',f'正式物理任务{s["physical_formal_jobs"]}次；D7早收敛复用{len(s["derived_D7_records"])}条。D的逻辑成本仍计入该分支完整耗时，物理执行成本单列，避免缓存使D显得更便宜。所有控制、失败、超时与未收敛记录保留。', '', '任务墙钟包含模型/进程加载和退出，反映当前单进程单任务实现，不是GPU核函数时间。原生坐标预测成本另列；模型长期驻留或改批处理会改变成本，需要另行验证。名义步数同上限不代表实际成本相等。', '', '## 严格验收与不确定性','', '最终CIF显式原子数保持、距离、连通性、体积；MOFid完整身份、目标连接体类型集合一致；S/D预期pcu。收敛另列，类型集合不提供计量数/分解稳定性证明。比例区间与配对成本bootstrap见summary.json，点估计选择不替代广泛泛化证据。', '', '## 适用范围与失败边界','',json.dumps(s['scope'],ensure_ascii=False,indent=2),'',f'S/D配对得失：{json.dumps(s["paired_S_D"],ensure_ascii=False)}；双构象均通过{s["both_dual_branches_pass"]}/{n}。失败案例见pairs.csv，保留原分母，本阶段不再调种子、阈值或修复算法。', '', '本批固定MOFFlow-2目标5.0、二羧酸连接体及pcu/Zn4O模板。目标条件响应、其它节点/拓扑、热力学稳定性和吸附分离性能仍属于下一阶段。', '', '## 身份与训练覆盖','',json.dumps(s['identity'],ensure_ascii=False,indent=2),'',json.dumps(s['strata'],ensure_ascii=False,indent=2),'', '训练片段集合差与框架身份无匹配分开解释；训练参考部分解析是覆盖缺口。批内唯一数为MOFid身份口径。']
if (p/'RUNTIME_DEVIATIONS.json').exists():
    deviation=json.loads((p/'RUNTIME_DEVIATIONS.json').read_text());lines+=['','## 实现偏差记录','',f'原生预测实际使用官方入口的{deviation["actual_predict_batch_size"]}条/批，而非计划8条/批；配置项层级未被预测入口读取，worker=4生效。该偏差在CIF转换和MACE前记录，没有按结构结果重启或换样，保留了真实有效配置与成本。工作代码已修正未来批大小键路径，原冻结代码保留在results。MACE预算和验收规则未变。']
lines+=['', '## 可复用交付与阶段出口','',f'deliverables/cifs包含推荐策略的{len(manifest)}个验收通过CIF，manifest.json记录选用分支、收敛、输出哈希和训练标签。D代表选择先取收敛的通过分支，再按种子7优先；这项交付排序不改变成功数或成本。', '', '可复用批次接口：selected/targets/build JSON → 签名保护的run.py → manifest → 官方MOFid → 严格身份检查与报告。尚未封装自然语言产品入口。', '', '后续入口：在已冻结生产策略上登记目标条件响应与吸附性能对照；复用已有孔道、电荷、Widom/GCMC管线。DAO-P继续备选。本阶段到此结项，不再逐例修复。', '', '审计见results/AUDIT.json；完整数据见results/pairs.csv、summary.json及results_bundle.tar.gz。']
(root/'PHASE_CLOSEOUT.md').write_text('\n'.join(lines),encoding='utf-8')
(deliver/'README.md').write_text(f'本阶段推荐：{name_map[recommend]}。共{len(manifest)}个几何与身份验收通过候选；吸附性能和实验合成尚未验证。见../PHASE_CLOSEOUT.md及manifest.json。\n',encoding='utf-8')
(root/'PHASE_COMPLETE.json').write_text(json.dumps(dict(phase_complete=True,recommendation=recommend,n=n,delivered_candidates=len(manifest),audit_passed=True),indent=2))
print(json.dumps(dict(recommendation=recommend,n=n,delivered=len(manifest)),indent=2))
