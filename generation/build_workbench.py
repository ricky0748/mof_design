"""Build the offline project workbench from an explicit, reviewable research graph."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
nodes = {}


def node(id, title, desc, status='done', *, why='', inputs=(), outputs=(), checks=(), findings=(), evidence=(), next=(), jump=None, priority=None):
    nodes[id] = dict(id=id, title=title, desc=desc, status=status, why=why, inputs=inputs,
                     outputs=outputs, checks=checks, findings=findings, evidence=evidence,
                     next=next, jump=jump, priority=priority)
    return id


node('assets','数据与训练资产','公开 CIF、构筑块、训练表示、预训练权重',why='为生成、标签建模和新颖性核查提供各自的参考范围。',inputs=['CSD / CoRE / hMOF / MOSAEC / CRAFTED','三引擎官方公开资产'],outputs=['数据库镜像与轻量索引','推理权重和独立环境','MOFFlow-2 序列 / 结构 LMDB'],checks=['标明数据来源、版本、记录数和训练/验证范围'],findings=['结构匹配参考库共 365,010 CIF。','MOFFlow-2 训练序列与训练结构各 187,047 条。'],evidence=['worklog.md','generation/mofid_prepare.py'])
node('produce','多路线生成候选','三种生成引擎；规则设计保留基线','partial',why='区分模型能提出什么，以及新结构从哪一步产生。',inputs=['预训练权重、构筑块库、采样条件'],outputs=['序列 / 粗粒化表示 / 描述符','每条路线独立保留的原始样本'],checks=['记录全部原始样本、种子、条件和失败原因'],findings=['三引擎各 100 个样本已完成统一评估。','1000 样本扩展已执行，跨引擎汇总待齐。'],evidence=['generation/structure_generation_quality.md','worklog.md'],jump='generation')
node('cif','组装并形成结构批次','统一出口：CIF + 样本来源 + 尝试记录',why='将不同引擎输出接到共同验证流程，同时保留失败分母。',inputs=['引擎解码结果、节点、构筑块或预测坐标'],outputs=['原始 CIF','样本 ID、引擎、条件、父样本与组装状态'],checks=['原始生成数 → 解码/组装成功数分别统计','同名文件覆盖与结构重复分别核查'],findings=['MOFFlow-2：1000 → 754 个 CIF。','MOFDiff：1000 → 720 个 CIF。','EGMOF：生成结果存在同名覆盖，最终 751 个文件。'],evidence=['generation/convert_mofflow2_predictions.py','generation/egmof_scale.py','worklog.md'])
node('quality','验收化学与结构质量','原始检查 → 弛豫 → 有效 / 缺陷 / 未解决',why='得到可信的结构子集，同时定位生成和工具各自的失效。',inputs=['原始序列与 CIF'],outputs=['化学检查表','原始 / 弛豫结构对','分原因的接受与拒绝记录'],checks=['工具失败、超时与结构缺陷单列','化学通过与几何通过计算交集'],findings=['MOFFlow-2 千样本：427 个弛豫有效结构。','其中同时化学与结构有效的原始样本为 166/1000。'],evidence=['generation/mofdiff_plausibility/combine_mace.py','generation/scale1000_mofflow2/combined.csv'],jump='quality')
node('identity','核查身份与新颖性','去重、数据库比对、训练集比对、MOFid','partial',why='分别回答“重复了吗”“在参考中出现过吗”“框架身份是什么”。',inputs=['原始 / 弛豫 CIF','数据库和训练集参考'],outputs=['重复组','结构 / 连接体匹配','MOFid 完整身份与部分解析记录'],checks=['标注参考覆盖和解析成功率','训练外片段、拓扑身份、数据库无匹配分别报告'],findings=['MOFid 已提取 754 原始 + 427 弛豫有效结构。','完整训练参考的匹配仍在处理。'],evidence=['generation/mofid_validation.md'],jump='identity')
node('metrics','形成公平的生成质量比较','有效、唯一、新颖、多样、可控、成本','partial',why='用相同分母与预算决定下一阶段投入哪条路线。',inputs=['各批次全漏斗和身份结果'],outputs=['三引擎对照表','新颖性分层与失败谱','成本和不确定度'],checks=['统一原始样本分母、种子与预算','同时报告全样本和有效子集','条件可控性需要专门对照'],findings=['100 样本统一比较完成。','千样本统一结果和条件响应证据待补齐。'],evidence=['generation/structure_generation_quality.md','PROJECT_MAP.md'])
node('diagnose','找出主要失效机制','区分化学、装配、键感知、拓扑与工具问题','planned',why='把评估结果转化为可干预的生成器问题。',inputs=['逐样本失败日志','原始 / 弛豫身份成对结果'],outputs=['失败分类','代表样本','一个可检验的改进假设'],checks=['给出复现输入与对照','统计机制覆盖多少失败样本'],findings=['MOFid：427 个弛豫有效结构中 107 个获得完整身份。','识别失败的具体原因仍需逐样本诊断。'],evidence=['generation/mofid_validation.md'],next=['优先解释拓扑识别失败和弛豫前后的身份变化。'],jump='research')
node('improve','实现并验证生成改进','约束、解码、组装或采样的受控改动','planned',why='形成能通过独立批次验证的研究增益。',inputs=['明确的机制假设','冻结的基线与对照协议'],outputs=['方法版本','消融实验','独立评估批次'],checks=['同等预算下改善结构质量','报告有效率、新颖率、多样性与成本取舍'],evidence=['worklog.md','NEXT_STEPS.md'],next=['先选一个具体改进点，再登记对照。'])
node('independent','独立批次与条件响应','不同条件 / 无目标 / 改进前后','planned',why='检验增益能否在新的生成批次中复现。',inputs=['固定样本数、随机种子、条件、评价口径'],outputs=['条件响应曲线','跨种子结果','稳定性与成本区间'],checks=['真实输出结构响应条件变化','训练/反馈样本与独立评估分开'],evidence=['generation/structure_generation_quality.md'])
node('task','需求解析与任务配置','自然语言 → 条件、约束、数量、预算','planned',inputs=['用户需求'],outputs=['结构化任务','可复现批次配置'],checks=['解析元素/节点限制、生成数量、评价目标','条件实际传入引擎并可追溯'],evidence=['NEXT_STEPS.md'])
node('delivery','候选包与可追溯结果','多个 CIF + 来源 + 验证状态 + 证据','planned',why='让一次需求形成可审查、可复用的候选产物。',inputs=['质量与身份结果','任务配置与生成来源'],outputs=['候选 CIF 包','指标和失败原因','批次报告'],checks=['用户能追到每个结论对应的输入与计算'],evidence=['NEXT_STEPS.md'])
node('legacy','性能评价支线','特征 → 代理 / OOD → Widom / GCMC → 对照','paused',why='保留已验证的性能评价资产，当前计算重点转向结构生成。',inputs=['经过检查的候选 CIF'],outputs=['孔道/化学特征','选择性、容量、损失与成本'],checks=['弛豫后重新计算电荷和特征','性能结论使用对应结构版本'],evidence=['widom_sih4/README.md','generation/pilot_selection/fair_compare_report.md'],jump='performance')

# Generation routes: distinguish the actual intermediate representations.
node('mfd-sample','MOFDiff · 粗粒化采样','潜空间 / 构筑块级扩散 → 粗粒化 MOF',inputs=['BW-DB 预训练模型','种子与样本数'],outputs=['粗粒化位置、晶胞、构筑块表示'],checks=['保存采样参数与原始输出'],evidence=['worklog.md'])
node('mfd-match','构筑块检索与解码','嵌入近邻匹配 → 全原子构筑块',inputs=['粗粒化生成表示','构筑块嵌入缓存'],outputs=['具有具体构筑块的粗粒化框架'],checks=['记录固定构筑块库的覆盖与限制'],evidence=['worklog.md'])
node('mfd-assemble','装配优化与 CIF','连接约束检查 → 全原子拼装','partial',inputs=['解码后的构筑块与晶胞'],outputs=['1000 样本中的 720 个 CIF'],findings=['千样本原始几何干净 249/720；720/720 去重唯一。'],checks=['装配失败回到生成分母','弛豫结果另行统计'],evidence=['worklog.md'])
node('mff-seq','MOFFlow-2 · 序列生成','性质条件 → 金属与有机 SBU 序列',inputs=['训练序列模型','目标值、温度、种子'],outputs=['1000 条原始序列'],findings=['本轮 target=5.0，temperature=1.0。'],checks=['使用模型原生目标定义','保存全部序列与不可解析片段'],evidence=['generation/scale1000_mofflow2/bb_novelty_1000.csv','worklog.md'])
node('mff-predict','构筑块解析与三维预测','序列解析 → 几何生成 → 晶胞与坐标',inputs=['金属 / 有机构筑块序列'],outputs=['预测坐标、原子种类、晶胞','原始序列到成功结构的映射'],checks=['保持 processed_data 的索引对应','解析失败和几何预测失败分开'],evidence=['generation/convert_mofflow2_predictions.py'])
node('mff-export','MOFFlow-2 · CIF','预测张量转 CIF → 754/1000',inputs=['预测坐标、lattices、num_atoms'],outputs=['754 个原始 CIF','原始序列索引'],checks=['每个 CIF 可回溯到原始序列','后续可算化学与结构通过交集'],evidence=['generation/convert_mofflow2_predictions.py','generation/scale1000_mofflow2/chemfilter_1000_end2end.csv'])
node('eg-desc','EGMOF · 描述符生成','性质条件 → prop2desc → 描述符',inputs=['模型原生目标值','预训练条件模型'],outputs=['目标结构描述符'],checks=['原生 CO₂ 目标与项目任务目标分别记录'],evidence=['generation/egmof_scale.py'])
node('eg-decode','描述符到框架组合','desc2mof → 节点 / 边 / 拓扑',inputs=['描述符','固定构筑块与拓扑库'],outputs=['框架组合与模型筛选值'],checks=['统计组合重复','构筑块新颖性按固定库口径解释'],evidence=['generation/egmof_scale.py','worklog.md'])
node('eg-assemble','PORMAKE → CIF','组合构建，显式统计同名覆盖','partial',inputs=['节点、连接体与拓扑组合'],outputs=['751 个唯一文件'],findings=['963 行结果；951 行带 CIF 名；200 个同名被覆盖。'],checks=['文件数、结果行数、结构唯一数各自保留'],evidence=['worklog.md'])
node('rule-enum','规则基线 · 单取代枚举','已知配体种子 → 受限变体','baseline',inputs=['配体种子','取代基、价键、连接数限制'],outputs=['239 个配体变体'],checks=['保留种子对照与父配体','规范 SMILES 去重'],evidence=['generation/enumerate_variants.py','generation/README.md'])
node('anchor','锚点与构象','识别结合位点、方向、连接数','baseline',inputs=['配体 SMILES'],outputs=['连接点与带 X 构筑块','几何方向判据'],checks=['锚点类型、价键、构象和连接方向'],evidence=['anchor_rules/anchor_rules.py','anchor_rules/README.md'])
node('rule-cif','固定节点 / 拓扑组装','613 次尝试 → 268 个合格 CIF','baseline',inputs=['构筑块、节点、拓扑'],outputs=['CIF + 每次尝试的候选元数据'],findings=['17 known controls；251 个取代变体。'],checks=['方向、碰撞、键长及三齿定位误差'],evidence=['generation/build_candidates.py','generation/README.md'])
node('nex','Nexerra · 配体试点','分子生成 → 锚点 / 刚性筛选','pilot',inputs=['生成模型与配体约束'],outputs=['SMILES 到现有组装接口'],findings=['多批次可用产出低；部分路线组装失败。'],checks=['先改造化学与连接约束，再评价产出率'],evidence=['generation/nexerra_to_variants.py','worklog.md'])
node('cg','patchy 粗粒化自组装','锚点 → HOOMD → 连通与环统计','pilot',inputs=['配体与节点族'],outputs=['自组装轨迹','占位、桥连、连通、环分布'],checks=['位点单占位','周期绕行环与局部环分开'],evidence=['cg_assembly/README.md','cg_assembly/analyze_cg.py'])

# Quality gates and routing.
node('chem','关口 A · 化学检查','RDKit / 自由基 / 电荷 / 结合基团',inputs=['原始序列与构筑块'],outputs=['硬有效、连接体适用、guest 标记'],checks=['per-sequence 与 per-SBU 分母分开','≥2 结合基团；guest 单列'],findings=['MOFFlow-2 千序列：linker-suitable 45.6%。'],evidence=['generation/mofdiff_plausibility/filter_generated_sbus.py','generation/mofdiff_plausibility/chem_filter_seqs.py'])
node('precheck','关口 B · 原始几何','短接触、片段、组成与金属配位',inputs=['原始 CIF'],outputs=['dmin、短接触数、片段数、原子数和体积'],checks=['记录原始质量，保留供弛豫前后比较'],evidence=['generation/mofdiff_plausibility/precheck_dir.py'])
node('uff','UFF 参数化与弛豫','lammps-interface → LAMMPS',inputs=['原始 CIF'],outputs=['参数化状态','弛豫 CIF / 运行日志'],checks=['先判断工具是否成功，再判断结构质量'],findings=['MOFFlow-2：212/754 可参数化，202 个弛豫有效。'],evidence=['generation/mofdiff_plausibility/uff_relax_standalone.py','generation/mofdiff_plausibility/uff_summary.py'])
node('mace','工具失败 → MACE fallback','替代几何弛豫；保留势与参数差异',inputs=['UFF 工具失败的 CIF'],outputs=['MACE 结构','超时和异常记录'],checks=['MACE 与 UFF 的能量口径分开','超时保留为未解决'],findings=['MOFFlow-2：补回225个有效结构；62个超时样本待解决。'],evidence=['generation/mofdiff_plausibility/combine_mace.py','worklog.md'])
node('postcheck','关口 C · 弛豫后结构','原子数、体积、距离与连通性',inputs=['UFF 或 MACE 的弛豫结果'],outputs=['有效 / 结构缺陷 / 未解决'],checks=['原子数与输入一致','dmin ≥0.9 Å；单片段','体积比 0.75–1.25'],evidence=['generation/mofdiff_plausibility/combine_mace.py'])
node('valid','化学与结构的交集','按原始样本 ID 合并通过条件',inputs=['化学过滤表','弛豫后有效表','序列到CIF映射'],outputs=['端到端可用样本','各阶段通过率'],findings=['MOFFlow-2：166/1000 同时化学与结构有效。'],checks=['失败样本留在原始分母中'],evidence=['generation/scale1000_mofflow2/chemfilter_1000_end2end.csv'])
node('defect','结构缺陷 → 原因归档','碰撞、断片、体积异常、化学问题',inputs=['成功执行但未通过的检查'],outputs=['可复现失败样本与分类'],checks=['与工具运行失败分开','连接到生成器可改进环节'],evidence=['generation/mofdiff_plausibility/check_mofdiff_plausibility.py','worklog.md'])
node('unresolved','超时 / 工具错误 → 待核查','保留原结构与日志，按原因重试','partial',inputs=['超时、参数化异常、无输出'],outputs=['未解决清单','受限重试任务'],checks=['未解决数进入报告','重试参数与版本有记录'],evidence=['worklog.md'])

# Identity: three questions, three reference kinds.
node('dedup','问题 1 · 批次内是否重复','StructureMatcher 识别重复组',inputs=['同一批次全部 CIF'],outputs=['唯一结构数与重复组'],checks=['ltol 0.3 / stol 0.5 / angle 10','使用相同去重口径'],findings=['MOFFlow-2：676/754 唯一；MOFDiff：720/720 唯一。'],evidence=['generation/mofdiff_plausibility/dedup_dir2.py'])
node('dbmatch','问题 2 · 参考库中是否已有','同化学式预筛 → 晶体结构匹配',inputs=['生成 CIF','365,010 个参考结构索引'],outputs=['结构匹配与同式候选','已检索数据库范围'],checks=['精确搜索与有界宽松搜索分开','保留每库的覆盖与解析失败'],findings=['MOFFlow-2 千样本：精确结构匹配为0。'],evidence=['generation/mofdiff_plausibility/novelty_lookup.py','generation/mofdiff_plausibility/novelty_loose.py'])
node('seqnovel','问题 3a · 训练外分子片段','RDKit canonical SMILES 集合差',inputs=['生成 SBU 序列','187,047 条训练序列'],outputs=['在序列训练集合中未出现的分子字符串'],checks=['不同质子化与互变异构尚未统一','化学可行性另做过滤'],findings=['504 个唯一可解析有机片段中156个未精确匹配。'],evidence=['generation/mofdiff_plausibility/mofflow2_bb_novelty.py'])
node('review','类似物距离与化学审查','最近邻指纹相似性 + 连接体规则','partial',inputs=['训练外片段'],outputs=['与训练构筑块的最近邻','可行连接体与缺陷清单'],findings=['早期18个新片段中，14个最近邻Tanimoto≥0.7。'],checks=['千样本156个片段的审查待补全'],evidence=['generation/mofdiff_plausibility/review_novel_sbus.py'])
node('mofid','问题 3b · 从 CIF 提取身份','节点、连接体、拓扑和互穿标记',inputs=['原始和弛豫 CIF'],outputs=['chemistry_key','framework_key','partial / failed / timeout'],checks=['文件名和版本元数据不参与身份比较','ERROR / UNKNOWN 等单列'],findings=['754原始：44完整身份；427弛豫有效：107完整身份。','HKUST-1重命名与超胞控制通过。'],evidence=['generation/mofid_validate.py','generation/mofid_validation.md'])
node('trainref','同版本构建训练参考','LMDB重建CIF → MOFid','partial',inputs=['187,047条训练结构','同版本MOFid'],outputs=['训练身份与连接体索引','处理/成功/失败覆盖率'],checks=['抽查结构键与序列对应','记录未解决训练结构'],findings=['20条序列对应抽查通过。','100条流程抽样：95完整身份、5部分解析。'],evidence=['generation/mofid_prepare.py','generation/run_mofid_reference.sh'])
node('idcompare','身份与连接体的精确匹配','完整身份匹配 / 化学片段匹配分别输出','partial',inputs=['生成MOFid结果','已处理的训练参考'],outputs=['逐结构匹配记录','训练覆盖率与未知标签'],checks=['参考覆盖不足时保留待定范围','部分解析与完整身份使用不同分母'],evidence=['generation/mofid_compare.py'])
node('identityreport','分层报告新颖性','批次唯一 / 数据库无匹配 / 训练外片段 / 框架身份','partial',inputs=['三类比较与失败覆盖'],outputs=['带范围说明的新颖性证据'],checks=['每个结论可回溯到参考与比较方法'],evidence=['generation/mofid_validation.md','generation/structure_generation_quality.md'])

# Historical performance pipeline.
node('labels','历史标签与特征摸底','CRAFTED Widom、组装结构标签、R²分析','paused',inputs=['CRAFTED / 组装结构'],outputs=['Henry标签','几何与化学特征的信号分析'],findings=['CRAFTED690 + 组装132标签用于代理开发。'],evidence=['widom_sih4/结果报告.md','r2_probe/R2摸底报告.md'])
node('zeo','Zeo++ 孔道特征','孔径、可达体积、密度等','paused',inputs=['候选 CIF'],outputs=['几何特征 G'],checks=['在对应结构版本上重算'],evidence=['widom_sih4/zeo_features.py'])
node('charge','PACMOF 与化学特征','部分电荷、元素比例、金属类别','paused',inputs=['候选 CIF'],outputs=['带电荷CIF','Chem特征'],checks=['弛豫后的CIF重新充电'],evidence=['widom_sih4/pacmof_batch.py','widom_sih4/chem_features_pacmof.py'])
node('surrogate','LightGBM 代理评分','G + Chem → 选择性预测','paused',inputs=['训练标签','候选特征'],outputs=['预测分数与候选排序'],checks=['预测登记与真实评价分开'],evidence=['generation/score_candidates_full.py'])
node('ood','适用域 / OOD 分流','域内筛选；域外精算与补标签','paused',inputs=['候选几何/化学特征','训练特征分布'],outputs=['适用域标记','扩训/精算任务'],findings=['CRAFTED代理对MOFDiff40个可评估结构ρ≈0.078。'],checks=['在生成候选家族上检验排序','不同候选家族分别评价'],evidence=['widom_sih4/applicability_domain.py','generation/mofdiff_aug_eval.py'])
node('widom','Widom → Henry 选择性','np / pol 输入、超胞、误差解析','paused',inputs=['合适力场与电荷CIF'],outputs=['Henry常数、误差、log选择性'],checks=['吸附能与异常大Henry核查'],evidence=['widom_sih4/make_inputs.py','widom_sih4/parse_widom.py'])
node('gcmc','混合 GCMC → 容量与选择性','温度、压力、混合比例下的吸附','paused',inputs=['候选结构、混合物与条件'],outputs=['选择性','CO₂容量','SiH₄摄取'],checks=['对照冻结标准','记录收敛与超时'],evidence=['generation/make_gcmc_inputs.py','generation/parse_gcmc.py'])
node('fair','同预算对照与阈值分析','设计池 vs 已知库；性能与容量取舍','paused',inputs=['冻结候选池与选择策略','同一精算预算'],outputs=['命中率、成本、Pareto与阈值敏感性'],checks=['已看结果的样本用于历史验证','报告阈值改变后的取舍'],evidence=['generation/pilot_selection/fair_compare_report.md','generation/pilot_selection/exhaustive/REPORT.md'])
node('feedback','历史反馈选择','根据真值决定下一轮候选选择','baseline',inputs=['已测标签与候选池'],outputs=['后续候选','预测登记和真实结果'],checks=['区分固定池选择与生成器改进'],evidence=['generation/pilot_selection/feedback_select.py','generation/pilot_selection/feedback_registration.md'])
node('synthesis','合成可及性桌面研究','配体难度、文献路线与框架先例','paused',inputs=['候选连接体与框架'],outputs=['有出处的可行性判断'],checks=['实验验证目前无执行条件'],evidence=['generation/pilot_selection/synthesis_assessment.md','NEXT_STEPS.md'])

# Work items depend on deliverables rather than unrelated UI modules.
node('p0ref','完成训练参考与匹配','先得到可解释的参考覆盖','partial',priority='P0',inputs=['全量训练结构MOFid'],outputs=['覆盖率、匹配表、未知清单'],checks=['187047预期数与处理/成功数一致可追溯','生成完整身份与连接体匹配可复核'],evidence=['generation/run_mofid_reference.sh','generation/mofid_validation.md'],next=['核对全量任务日志，补全匹配报告。'],jump='identity')
node('p0diag','诊断拓扑与身份变化','原始 / 弛豫成对抽查','planned',priority='P0',inputs=['MOFid逐结构日志','原始与弛豫CIF'],outputs=['失败谱和代表案例'],checks=['定位键感知、氢/电荷、断片与拓扑差异','给出可复现案例及覆盖数'],evidence=['generation/mofid_validation.md'],jump='quality')
node('p1bench','收齐千样本公平比较','同分母、同口径、失败原因可见','partial',priority='P1',inputs=['三引擎千样本完整漏斗'],outputs=['统一质量表与成本表'],checks=['同时报告原始/唯一/有效/化学交集','超时与工具失败单列'],evidence=['worklog.md','generation/structure_generation_quality.md'],jump='generation')
node('p1control','登记条件响应对照','冻结目标、预算、种子与评价','planned',priority='P1',inputs=['可复现基线','统一评价协议'],outputs=['有目标/无目标或不同条件的对照批次'],checks=['结构质量、目标响应、唯一/新颖/多样同时评价'],evidence=['generation/structure_generation_quality.md'])
node('p2method','选择一个方法改进点','从失败机制提出可检验假设','planned',priority='P2',inputs=['失败诊断','跨引擎比较'],outputs=['干预点与消融协议'],checks=['明确预期改善哪个漏斗环节'],evidence=['worklog.md'])
node('p2test','独立验证研究增益','新种子、新批次、同预算','planned',priority='P2',inputs=['改进版本','冻结基线与消融'],outputs=['可复现的增益与成本取舍'],checks=['用独立评估回答是否改善生成'],evidence=['NEXT_STEPS.md'])
node('p3product','封装自然语言入口','任务配置、批次追踪、多CIF结果','planned',priority='P3',inputs=['稳定的生产/评价接口'],outputs=['需求到候选包的产品流程'],checks=['条件真正改变输出；每个结论可追溯'],evidence=['NEXT_STEPS.md'])
node('blockedbw','补齐 BW-DB 参考','下载受阻；影响MOFDiff记忆化核查','blocked',priority='依赖',inputs=['完整可校验的BW-DB'],outputs=['MOFDiff训练集参考范围'],checks=['下载内容完整校验后再索引'],evidence=['worklog.md','generation/bwdb_watch.py'])


def edge(a,b,label='',kind='flow',side=None):
    return dict(a=a,b=b,label=label,kind=kind,side=side)


def view(id,name,kicker,title,desc,positions,edges,groups=(),questions=()):
    return dict(id=id,name=name,kicker=kicker,title=title,desc=desc,
                positions=[dict(id=n,x=x,y=y) for n,x,y in positions],edges=edges,groups=groups,questions=questions)


views=[
view('overview','全局研究脉络','01 / PROJECT LOGIC','我们怎样从“能生成”推进到“可信、可控地生成”？','沿实线读取已搭建的处理链；虚线表示下一阶段的研究依赖。每个节点都能展开输入、产物、验收和文件依据。',
 [('assets',40,80),('produce',410,80),('cif',780,80),('quality',780,310),('identity',410,310),('metrics',40,310),('diagnose',40,560),('improve',410,560),('independent',780,560),('legacy',780,820),('task',40,820),('delivery',410,820)],
 [edge('assets','produce','训练资产'),edge('produce','cif','解码 / 组装'),edge('cif','quality','原始批次'),edge('quality','identity','结构与来源'),edge('identity','metrics','质量与身份表'),edge('metrics','diagnose','失败谱','plan'),edge('diagnose','improve','改进假设','plan'),edge('improve','independent','新版本','plan'),edge('independent','produce','新一轮生成','feedback','right'),edge('quality','legacy','保留性能出口','paused','right'),edge('task','delivery','需求与返回接口','plan')],
 groups=[dict(x=16,y=40,w=1080,h=470,title='A · 已有生产与验证链'),dict(x=16,y=520,w=1080,h=225,title='B · 下一阶段研究闭环'),dict(x=16,y=780,w=1080,h=225,title='C · 产品出口与历史性能支线')],questions=['现在最缺：失败机制和条件响应的系统证据。','已有底座：三引擎、质量筛查、身份核查、性能精算。']),
view('generation','生成路线拆解','02 / PRODUCERS','不同路线究竟在哪一步提出了新结构？','按行读取。各路线保留自己的原始分母与失败记录，最后汇入共同的 CIF 验收；固定构筑块重组与新片段生成分别评价。',
 [('mfd-sample',40,80),('mfd-match',410,80),('mfd-assemble',780,80),('mff-seq',40,300),('mff-predict',410,300),('mff-export',780,300),('eg-desc',40,520),('eg-decode',410,520),('eg-assemble',780,520),('rule-enum',40,740),('anchor',410,740),('rule-cif',780,740),('nex',40,980),('cg',410,980),('quality',780,980)],
 [edge('mfd-sample','mfd-match','构筑块嵌入'),edge('mfd-match','mfd-assemble','全原子构筑块'),edge('mff-seq','mff-predict','序列与索引'),edge('mff-predict','mff-export','坐标 / 晶胞'),edge('eg-desc','eg-decode','描述符'),edge('eg-decode','eg-assemble','组合 / 拓扑'),edge('rule-enum','anchor','配体SMILES'),edge('anchor','rule-cif','带连接点构筑块'),edge('nex','anchor','生成配体','pilot','left'),edge('rule-cif','quality','共同验收','baseline')],
 groups=[dict(x=16,y=40,w=1080,h=188,title='模型路线 1 · MOFDiff'),dict(x=16,y=260,w=1080,h=188,title='模型路线 2 · MOFFlow-2'),dict(x=16,y=480,w=1080,h=188,title='模型路线 3 · EGMOF'),dict(x=16,y=700,w=1080,h=188,title='保留基线 · 规则与锚点'),dict(x=16,y=940,w=1080,h=210,title='探索资产与共同出口')],questions=['MOFDiff：构筑块级空间生成。','MOFFlow-2：序列构筑块 + 三维预测。','EGMOF：性质条件下的固定库组合生成。']),
view('quality','质量关口与分流','03 / ACCEPTANCE GATES','一个候选在哪一步通过、失败，或仍待解决？','化学检查与几何检查有不同输入；最终按样本 ID 取交集。工具失败走替代计算或待核查队列，成功执行后的结构缺陷进入失败归因。',
 [('cif',40,80),('chem',40,330),('precheck',410,80),('uff',780,80),('mace',780,330),('postcheck',410,330),('valid',40,600),('identity',40,850),('defect',410,600),('unresolved',780,600),('diagnose',410,850)],
 [edge('cif','chem','原始序列'),edge('cif','precheck','原始 CIF'),edge('precheck','uff','结构 + 原始指标'),edge('uff','postcheck','执行成功'),edge('uff','mace','工具失败'),edge('mace','postcheck','弛豫成功'),edge('mace','unresolved','超时 / 异常'),edge('postcheck','valid','结构通过'),edge('chem','valid','化学通过'),edge('postcheck','defect','结构未通过'),edge('valid','identity','接受子集'),edge('defect','diagnose','可复现缺陷','plan'),edge('unresolved','diagnose','工具原因','plan')],
 questions=['化学有效、几何有效、拓扑身份各自对应独立检查。','同一个样本在所有阶段使用相同来源 ID。']),
view('identity','身份与新颖性证据','04 / IDENTITY & NOVELTY','“新”具体指哪一层？参考范围覆盖到哪里？','三条证据链分开读取：批次去重、公开结构库比对、训练集核查。MOFid 从最终 CIF 重建身份，用来复查序列提出的构筑块是否落实到了框架。',
 [('cif',40,80),('dedup',410,80),('dbmatch',780,80),('seqnovel',40,330),('review',410,330),('mofid',40,600),('trainref',410,600),('idcompare',780,600),('identityreport',780,850),('blockedbw',410,850)],
 [edge('cif','dedup','同批次'),edge('dedup','dbmatch','参考库查询'),edge('seqnovel','review','训练外片段'),edge('mofid','idcompare','生成身份','flow','top'),edge('trainref','idcompare','训练身份'),edge('idcompare','identityreport','覆盖 + 匹配'),edge('dbmatch','identityreport','公开库证据','flow','right'),edge('review','identityreport','片段证据','plan','right')],
 groups=[dict(x=16,y=40,w=1080,h=190,title='证据 A · 晶体结构的唯一性与数据库匹配'),dict(x=16,y=290,w=710,h=190,title='证据 B · 序列提出的分子片段'),dict(x=16,y=560,w=1080,h=190,title='证据 C · 从 CIF 实测框架身份')],questions=['156/504：序列 canonical SMILES 差集。','107/427：弛豫有效结构的完整 MOFid 身份识别数。','两个数字回答不同的问题，分别保留分母和方法。']),
view('performance','性能评价与历史反馈','05 / EXISTING EVALUATION','已有性能管线怎样产生标签、分流候选并验证结果？','这条管线已经跑通，11月11日起暂停扩展任务。恢复时从对应结构版本重算电荷与特征，并沿用登记、对照和真实评价规则。',
 [('labels',40,80),('zeo',410,80),('charge',780,80),('surrogate',410,330),('ood',780,330),('widom',780,580),('gcmc',410,580),('fair',40,580),('feedback',40,330),('synthesis',40,850),('delivery',410,850)],
 [edge('labels','surrogate','训练标签','paused'),edge('zeo','surrogate','G特征','paused'),edge('charge','ood','带电荷结构 / Chem','paused'),edge('surrogate','ood','排序与域检查','paused'),edge('ood','widom','域内筛选 / 域外精算','paused'),edge('widom','gcmc','精算候选','paused'),edge('gcmc','fair','真值与成本','paused'),edge('fair','feedback','更新选择','baseline'),edge('feedback','surrogate','补标签 / 更新','feedback'),edge('fair','synthesis','桌面可行性','paused'),edge('synthesis','delivery','证据材料','plan')],questions=['代理在训练分布内有效，生成家族需独立验证。','规则反馈选择已有执行；生成器改进的研究闭环仍待验证。']),
view('research','工作队列与依赖','06 / DECISIONS & NEXT WORK','下一步先做什么，完成后允许作出哪个判断？','从 P0 向后读取。点击任务看具体输入、产物和验收条件；选中后用上游 / 下游追踪它依赖什么、会解锁什么。状态来自 2026-11-12 文件快照。',
 [('p0ref',40,100),('p0diag',40,370),('p1bench',410,100),('p1control',780,100),('p2method',410,370),('p2test',780,370),('p3product',780,650),('blockedbw',40,650),('metrics',410,650)],
 [edge('p0ref','p1bench','身份覆盖','plan'),edge('p0ref','p0diag','身份差异','plan'),edge('p0diag','p2method','机制假设','plan'),edge('p1bench','p2method','主要瓶颈','plan'),edge('p1bench','p1control','冻结基线','plan'),edge('p1control','p2test','条件对照','plan'),edge('p2method','p2test','改进版本','plan'),edge('p2test','p3product','稳定接口与结果','plan'),edge('blockedbw','metrics','MOFDiff参考覆盖','plan'),edge('metrics','p3product','可追溯评价','plan')],
 questions=['P0 解决身份可信度与失败解释。','P1 固定基线和条件对照。','P2 建立方法增益；P3 封装产品入口。'])
]

data=dict(updated='2026-11-12', title='生成式 MOF · 研究工作台', nodes=nodes, views=views,
          statuses=dict(done='已实现',partial='部分完成',planned='待开展',paused='当前暂停',baseline='保留基线',pilot='探索试点',blocked='依赖受阻'))
for id in ('mfd-assemble','mff-export','eg-assemble','rule-cif'):
    nodes[id]['jump']='quality'
for v in views:
    for e in v['edges']:
        if v['id']=='overview' and e['kind']=='feedback': e['side']='cycle'
        if v['id']=='generation' and e['a']=='nex': e['side']=None
        if e['label']=='MOFDiff参考覆盖': e['label']='训练集覆盖'
    if v['id']=='overview':
        v['edges'].extend([edge('task','produce','任务配置','plan','outer-left'),edge('independent','delivery','验证结果','plan')])
    if v['id']=='generation':
        for g in v['groups']:
            if g['h']==188: g['h']=200
    if v['id']=='research':
        # Raw/relaxed identity diagnostics can proceed with existing generated results.
        # Completing the training reference is not a prerequisite for that work.
        v['edges']=[e for e in v['edges'] if not(e['a']=='p0ref' and e['b']=='p0diag')]
        v['questions'][0]='两个 P0 可并行：训练匹配与生成结构诊断。'
data['updated']='2026-11-13'
nodes['produce']['findings']=['三引擎各1000原始样本的结构评估全部完成。','按原始生成计结构有效：MOFDiff42.5%、MOFFlow-2 42.7%、EGMOF65.9%。']
nodes['mfd-assemble'].update(status='done',findings=['720个CIF中425个弛豫有效（59.0%）；原始1000样本计42.5%。','18个MACE超时样本保留为未解决。'])
nodes['eg-assemble'].update(status='done',findings=['751个落盘CIF中659个弛豫有效（87.7%）；原始1000请求计65.9%。','生成结果中存在同名覆盖；最终5个MACE超时样本未解决。'])
nodes['metrics']['findings']=['千样本统一结构评估完成：425/720、427/754、659/751有效。','条件响应、多种子稳定性及完整身份口径仍需补充。']
nodes['identity']['findings']=['生成结构1181次和训练参考187047次MOFid处理均已完成。','弛豫生成样本8个匹配训练框架身份，对应2种唯一身份。']
nodes['trainref'].update(desc='187047条全部处理；完整身份覆盖91.94%',findings=['171978条获得完整身份，15069条部分解析。','全量处理于2026-11-13 04:02完成；部分解析仍是身份覆盖缺口。'])
nodes['idcompare'].update(desc='生成结构与训练参考已完成首轮比较',findings=['弛豫有效427个：107个完整身份中8个匹配，99个未在已解析参考中匹配。','原始754个：44个完整身份均未匹配；其余710个未完整识别。','8个样本对应2种唯一身份；7个rna、1个pcu。'])
nodes['identityreport']['findings']=['公开结构库精确匹配0与训练参考身份匹配8分别报告。','训练参考15069条部分解析、生成结构完整身份覆盖不足，未匹配部分仍需保留范围。']
nodes['p0ref'].update(title='核查训练匹配与解析缺口',desc='全量处理完成：8个样本匹配，15069条参考待解析',findings=['训练结构187047条全部处理；完整身份171978条。','8个弛豫样本匹配2种训练身份。'],next=['检查8个命中样本及对应训练记录。','分类15069条部分解析记录，优先补关键参考覆盖。'])
nodes['p1bench'].update(title='千样本基线已齐 · 补强对照',desc='结构评估完成；多种子与条件对照待补',findings=['三引擎结构基线全部完成。'],next=['在统一基线上登记条件响应和独立种子实验。'])
pilot_evidence=['generation/linker_framework_pilot_v2/PROTOCOL.md','generation/linker_framework_pilot_v2/results/REPORT.md','generation/linker_framework_pilot_v2/results/AUDIT.json']
nodes['diagnose'].update(status='partial',findings=['v2独立核查通过：原生联合终点0/20、旧预筛1/20、取消预筛20/20、几何匹配17/20。','v1把19次手工预筛拒绝解释为模板不适配，已由取消预筛实验更正。'],evidence=pilot_evidence,next=['在独立连接体批次复核取消预筛方案。'])
nodes['p2method'].update(title='组合与消融完成 · 取消过严预筛',desc='同20连接体：U 20/20；几何匹配M 17/20',status='partial',inputs=['冻结20连接体（8原序列训练外、12训练内）','固定pcu/N16与121个有效模板池'],outputs=['4臂配对结果、39次唯一新正式弛豫和3次校准','完整CIF、官方MOFid和独立核查'],findings=['U全部恢复目标连接体、预期pcu拓扑并收敛。','训练外8个连接体U 8/8、M 6/8通过。','U的20种完整框架身份在171978条完整训练参考中无匹配；15069条部分解析。'],checks=['保留同20个分母与全部失败','修正3个样本的负氧归一化','同结构复用1次；M同时改变金属和拓扑'],evidence=pilot_evidence,next=['冻结独立批次、种子与预算，复核U相对原生结构的收益。'])
nodes['improve'].update(status='partial',findings=['取消直线预筛后U 20/20；几何匹配M 17/20，额外匹配收益未出现。','原生0/20；同历史样本诊断已完成，下一步独立验证。'],evidence=pilot_evidence)
nodes['p2test'].update(next=['用全新连接体批次配对比较原生与固定pcu/N16无预筛组装。'],evidence=pilot_evidence)
holdout_evidence=['generation/linker_framework_holdout/PROTOCOL.md','generation/linker_framework_holdout/results/REPORT.md']
nodes['diagnose']['findings'] += ['留出20连接体：原生联合终点0/20、无预筛组装20/20；旧20°门槛拒绝19个。']
nodes['diagnose']['evidence'] += holdout_evidence
nodes['p2test'].update(status='partial',title='留出验证完成 · 补全新生成批次',desc='新连接体20种、构象种子19；同千样本来源',findings=['A联合终点0/20；U联合终点20/20。','20个片段均为训练序列内；本轮验证同批次留出连接体。'],evidence=holdout_evidence,next=['全新生成批次、多构象种子与配位几何/稳定性检查。'])
nodes['independent'].update(status='partial',findings=['留出20连接体配对验证：A 0/20，U 20/20。','后续补全新生成批次、多构象种子与稳定性。'],evidence=holdout_evidence)
coordination_evidence=['generation/linker_framework_holdout/coordination_evidence/REPORT.md','generation/coordination_followup/results/REPORT.md','generation/coordination_followup/results/RESUME_AUDIT.json']
nodes['p2test']['findings'] += ['定向严格收敛复核：4风险样本+BDC控制5/5收敛，保留连接体和pcu身份。','L12仍有2.7 Å额外近邻；控制角偏差也随优化变化，暂不设置角度硬门槛。']
nodes['p2test']['evidence'] += coordination_evidence
nodes['diagnose']['findings'] += ['40个结构160个Zn在2.3/2.5 Å截断均四配位；2.7 Å近邻敏感性和角偏差已逐结构报告。']
nodes['diagnose']['evidence'] += coordination_evidence
fresh_evidence=['generation/linker_framework_fresh/PROTOCOL.md','generation/linker_framework_fresh/results/REPORT.md','generation/linker_framework_fresh/results/AUDIT.json']
nodes['p2test'].update(title='新批次与双构象验证完成',desc='200新序列→18种未测试连接体；序列种子719',findings=['A联合终点0/18；U7 16/18；U19 18/18。','两构象均成功16/18，至少一种成功18/18。'],evidence=fresh_evidence,next=['分析种子敏感案例，补条件响应与性能验证。'])
nodes['independent'].update(status='partial',findings=['新随机批次固定200序列，冻结18种连接体。','双构象均通过16/18，至少一种通过18/18。'],evidence=fresh_evidence)
steric_evidence=['generation/steric_diagnosis/REPORT.md','generation/steric_precondition/results/REPORT.md','generation/steric_precondition/DECISION.md']
nodes['diagnose']['findings'] += ['F11/F14种子7跨连接体碰撞；统一预处理试验0/2恢复、成功控制3/4保持，版本未采纳。']
nodes['diagnose']['evidence'] += steric_evidence
nodes['p2test']['findings'] += ['六案例预处理负结果已归档；后续严格核对连接体类型集合和预期拓扑。']
nodes['p2test']['evidence'] += steric_evidence
nodes['p2test']['next']=['继续双构象组装，登记目标条件响应和吸附性能对照。']
phase_evidence=['generation/budget_confirmation/PHASE_CLOSEOUT.md','generation/budget_confirmation/results/AUDIT.json','generation/budget_confirmation/results/INDEPENDENT_REVIEW.json','generation/budget_confirmation/deliverables/manifest.json']
nodes['p2test'].update(status='done',title='同预算结构确认已结项',desc='30连接体：单26/30、双28/30；默认单构象',findings=['单构象单位有效框架63.20 GPU任务秒，双构象101.65秒（+61%）。','92次正式物理任务/120逻辑分支；28条早收敛合法复用。','26个默认候选均收敛，输出哈希核验通过。'],evidence=phase_evidence,next=['本阶段结束，不追加个例修复。','下一阶段预登记目标条件响应与吸附性能。'])
nodes['p2method'].update(status='done',title='组合生产基线已选定',desc='单构象默认；双构象保留质量—成本取舍',findings=['固定目标下30个新连接体，严格终点原生0、单构象26、双构象28。','按计算前成本规则推荐单构象，结论限定本批与当前实现。'],evidence=phase_evidence,next=['沿冻结接口开展下一阶段。'])
nodes['independent'].update(status='done',title='结构生成确认阶段完成',desc='新批次、同预算、实际成本与身份审计已齐',findings=['4个训练片段未匹配连接体，两组合方案均4/4通过。','28种有效身份在171978条完整参考中未匹配，15069条部分解析。'],evidence=phase_evidence)
nodes['improve'].update(status='done',findings=['结构生成确认阶段结项，默认单构象pcu/Zn4O方案。','统一几何预处理未采纳；失败边界与电荷兼容性已归档。'],evidence=phase_evidence)
nodes['diagnose']['findings'] += ['本轮B25双构象几何失败、B29类型保持失败；未事后剔除或追加修复。']
nodes['produce']['findings'] += ['组合路线另以30个化学合格连接体为分母，单26/30、双28/30；已完成同预算确认。']
refine_evidence=['generation/convergence_sensitivity/REPORT.md','generation/convergence_sensitivity/results/收敛精修对照.png','generation/convergence_sensitivity/results/per_structure.csv','generation/convergence_sensitivity/results/AUDIT.json']
nodes['p2test']['findings'] += ['2026-11-16严格精修：26/26收敛且保留完整身份；体积变化中位−7.33%。']
nodes['p2test']['evidence'] = nodes['p2test']['evidence'] + refine_evidence
nodes['p2test']['next']=['同预算试验保持冻结，后续性能对照统一采用已验证的精修条件。','下一阶段登记目标条件响应与吸附性能。']
nodes['diagnose']['findings'] += ['34条精修/诊断任务已完成；失败分支追加预算无新增救回。']
nodes['diagnose']['evidence'] += refine_evidence
nodes['p2method']['findings'] += ['26个候选以广义力0.05精修后全部保留；建议作为后续性能输入。']
nodes['p2method']['evidence'] = nodes['p2method']['evidence'] + refine_evidence
data['updated']='2026-11-16'
conditional_evidence=['generation/conditional_response/README.md','generation/conditional_response/REPORT.md','generation/conditional_response/PROTOCOL.md','generation/conditional_response/PERFORMANCE_PROTOCOL.md','generation/conditional_response/results/response_summary.json','generation/conditional_response/results/structure_summary.json','generation/conditional_response/results/STRUCTURE_AUDIT.json']
nodes['p1control'].update(status='partial',title='条件响应主线已启动',desc='2400条配对采样完成；结构/性能对照进行中',findings=['目标2/5×种子1601/1602，各600条，全部保留。','当前路线合格序列：目标2为4/600、1/600；目标5为118/600、112/600。','35条组成员、29种唯一连接体进入统一结构处理；不补低目标样本。'],evidence=conditional_evidence,next=['完成统一结构验收和双种子Henry/GCMC。','原条件是CO₂工作容量，项目选择性作为迁移效果单列。'])
nodes['independent'].update(status='partial',title='条件响应与性能对照进行中',desc='新配对种子；统一精修和性能口径',findings=['既有结构生成及精修确认已完成。','同种子跨目标600/600序列改变，合格身份交集均0。','最终结构和性能效果按实际完成结果另报。'],evidence=phase_evidence+conditional_evidence)
nodes['mff-seq']['findings'] += ['2026-11-16已完成target2/5、两个新配对种子的2400条采样。']
nodes['p1control']['desc']='24种最终结构完成；96项性能任务正在运行'
nodes['p1control']['findings'] += ['29种抽样身份中24种有效：目标2为4种，目标5为20种。','24种电荷与Zeo++均通过，双种子Henry/GCMC共96项，性能结论等待计算。']
nodes['independent']['findings'] += ['结构审计已完成；24种有效候选进入96项性能对照。']
data['updated']='2026-11-17'
completed_evidence=conditional_evidence+['generation/conditional_response/results/performance/summary.json','generation/conditional_response/results/performance/AUDIT.json','generation/conditional_response/results/performance/per_candidate.csv','generation/conditional_response/results/主线对照.png']
nodes['p1control'].update(status='done',title='条件响应与性能实算已完成',desc='96/96完成；整体选择性未提高，存在更优个例',findings=['2400条配对采样，29种抽样身份，24种最终候选。','目标2/5混合选择性中位0.867/0.848，最佳0.968/1.641。','目标5有5/20种选择性>1；目标2为0/4。','来源/分母/结构/性能审计通过，低目标样本量较小。'],evidence=completed_evidence,next=['用已有标签分析选择性、容量与SiH₄损失。','登记项目目标驱动的下一轮对照。'])
nodes['independent'].update(status='done',title='配对条件响应与吸附对照完成',desc='两个生成种子；24候选各双模拟种子',findings=['条件明显改变候选与当前组合路线兼容率。','高目标组整体混合选择性中位数未提高，存在少量更优候选。','96项完成且解析，审计通过；MC独立延长收敛复核尚未做。'],evidence=completed_evidence)
nodes['p1control']['findings'] += ['按历史S≥2及容量/SiH₄损失门槛回看：本批0/24通过；作为新增参照，原预登记终点不变。']
nodes['p1control']['evidence'] = nodes['p1control']['evidence']+['PROJECT_OVERVIEW.md']
nodes['metrics'].update(status='partial',title='从结构产率走向项目命中密度',desc='结构与条件比较已完成，性能反馈待验证',findings=['三引擎千样本结构比较与条件/双种子吸附对照均完成。','本批原生条件提高组合路线候选产率，整体项目选择性未提高。','下一步按选择性、CO₂容量、SiH₄损失和成本评价反馈增益。'],evidence=['PROJECT_OVERVIEW.md','generation/conditional_response/REPORT.md'])
nodes['p1bench'].update(status='done',title='基线与首轮条件对照已归档',desc='千样本、固定路线与96项吸附证据齐备',findings=['三引擎结构基线、组合路线与统一精修均有数据。','首轮条件/性能迁移对照完成，保留各自分母与范围。'],evidence=['PROJECT_OVERVIEW.md','generation/conditional_response/REPORT.md'],next=['制定项目性能反馈对照，保留历史基线。'])
nodes['metrics'].update(title='模块验收与应用评价分层',desc='AI设计模块为交付目标；分离案例独立评价',findings=['模块需要统一输入输出、可复现生成、验证、失败处理和候选交付。','SiH₄/CO₂是已有应用案例，其性能门槛用于案例评价。','生成/验证底座已有试验，统一模块封装仍待实现。'],evidence=['PROJECT_OVERVIEW.md','NEXT_STEPS.md'])
nodes['task'].update(priority='P0',title='定义统一设计任务',desc='约束、引擎、数量、种子、预算与支持范围',evidence=['PROJECT_OVERVIEW.md','NEXT_STEPS.md'])
nodes['p3product'].update(priority='P1',title='封装AI设计MOF模块',desc='统一调用、任务编排、多CIF与验证结果',next=['先封装已验证路线，按支持范围验收。','自然语言交互与应用评价按需扩展。'],evidence=['PROJECT_OVERVIEW.md','NEXT_STEPS.md'])
nodes['delivery'].update(priority='P1',title='统一候选交付接口',desc='多个CIF、来源、验证状态、失败与批次清单',evidence=['PROJECT_OVERVIEW.md','NEXT_STEPS.md'])
nodes['p1control']['next']=['结果作为分离应用案例保留。','当前交付优先统一模块入口、编排和候选包。']
nodes['p1bench']['next']=['复用现有证据封装模块，避免重复大型试验。']
module_evidence=['mof_design/README.md','mof_design/ACCEPTANCE.md','module_delivery/v0.1.0/acceptance/egmof/AUDIT.json','module_delivery/v0.1.0/acceptance/linker/AUDIT.json']
nodes['task'].update(status='done',title='结构化设计任务入口已实现',desc='引擎/场景/目标/数量/预算与显式约束',inputs=['JSON或Python任务配置'],outputs=['任务快照、唯一ID、进度与状态'],checks=['拒绝不支持的场景、约束和无效预算','约束应用层级明确为生成后过滤'],evidence=module_evidence)
nodes['p3product'].update(status='done',title='AI设计MOF模块v0.1已交付',desc='EGMOF默认＋连接体探索；Python/CLI',findings=['20项本地测试通过，支持状态/取消/超时及独立任务目录。','两条真实小批各交付2份经过精修和MOFid的CIF。','场景配置独立于后端；无新训练、网页或自然语言解析。'],checks=['统一输入输出与能力声明','请求、资产、提案和候选包可追溯'],evidence=module_evidence,next=['按需求补场景适配和使用体验。'])
nodes['delivery'].update(status='done',title='候选包统一交付已实现',desc='相对路径CIF、索引、验证记录和ZIP',findings=['EGMOF三次提案交付两份，完整身份识别失败的一份保留。','连接体探索两次提案交付两份；两模式包审计通过。'],evidence=module_evidence)
for v in views:
    v['questions']=[q.replace('现在最缺：失败机制和条件响应的系统证据。','当前重点：候选已有目标响应，如何提高项目分离命中密度？') for q in v.get('questions',[])]
    v['questions']=[q.replace('当前重点：候选已有目标响应，如何提高项目分离命中密度？','当前交付：把已有生成与验证能力封装成可调用的AI设计MOF模块。').replace('P2 建立方法增益；P3 封装产品入口。','优先模块输入输出、编排和交付；应用性能研究独立管理。') for q in v['questions']]
    v['desc']=v['desc'].replace('2026-11-12','2026-11-13')
(ROOT/'project-workbench.data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
template=(ROOT/'project-workbench.template.html').read_text(encoding='utf-8')
(ROOT/'project-workbench.html').write_text(template.replace('2026-11-12',data['updated']).replace('2026.11.12',data['updated'].replace('-','.')).replace('/*__PROJECT_DATA__*/',json.dumps(data,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
print(f'{len(nodes)} nodes; {len(views)} views; '+str(ROOT/'project-workbench.html'))
