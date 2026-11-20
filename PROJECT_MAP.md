# 生成式 MOF 项目工作地图

更新：2026-11-17。定位：**能力地图 + 研究流程 + 工作状态**。用于把控已有功能、当前问题和下一次决策。先读 [项目总览](PROJECT_OVERVIEW.md)，再按本图定位模块与证据。

当前状态：主线96/96 Henry/GCMC全部完成，汇总和审计通过。目标2/5的混合选择性中位0.867/0.848，最佳0.968/1.641；候选产率有明显响应，整体选择性未提高。详细结果见[generation/conditional_response/REPORT.md](generation/conditional_response/REPORT.md)。

当前主线：**可调用的AI设计MOF模块**。v0.1已补齐统一任务入口、两后端编排与候选交付。2400条采样和96项吸附作为SiH₄/CO₂应用案例归档；原26个B系列与本轮24个C系列候选分批报告。

最新交付：模块v0.1已完成统一Python/CLI、EGMOF/连接体探索后端、场景注册、任务管理与候选交付；真实小批各2份CIF。使用与范围见[mof_design/README.md](mof_design/README.md)。

下一步：使用已交付模块，按实际需求补场景适配、交互和运行调度。历史S_CO2≥2等门槛用于对应分离案例；本批未达到该案例门槛的结果独立保留。

最新完成：**结构生成同预算确认阶段已结项**。30个冻结的新连接体，原生300步0/30、单构象300步26/30、双构象各150步28/30严格通过；单位有效框架GPU任务墙钟63.20秒与101.65秒。按预登记成本规则，默认单构象，双构象为较高成本质量选项。[结项报告](generation/budget_confirmation/PHASE_CLOSEOUT.md) · [26个候选清单](generation/budget_confirmation/deliverables/manifest.json)。

三引擎千样本评估、MOFid训练参考已处理并记录解析缺口。v1的20°方向预筛解释已由消融更正；统一几何预处理0/2恢复、成功控制3/4保持，版本未采纳。已完成的结构试验保持冻结，后续改动按新对照登记。

推荐在项目根目录双击 **`打开项目工作台.cmd`**，会启动或复用本机服务并在浏览器打开。服务运行后可进入 **[本机工作台](http://127.0.0.1:8765/generation/project-workbench.html)**；实际端口也记录在 `generation/workbench-server.json`。

[HTML 文件](generation/project-workbench.html) 保留为离线入口。聊天或编辑器中的 HTML 文件链接可能进入源码视图；一键启动入口会明确打开浏览器。

工作台共有六个视图、60 个可追溯节点；点击节点展开输入、产物、验收条件、现有发现、证据文件和下一动作。本机入口中的证据文件直接显示为只读网页。

| 视图 | 用它回答什么 |
|---|---|
| 全局研究脉络 | 怎样从生成候选，经过可信度验证，走向方法改进与产品出口？ |
| 生成路线拆解 | 三种模型各自在哪一步提出结构？固定库、序列、粗粒化表示怎样解码成 CIF？ |
| 质量关口与分流 | 化学与几何怎么验收？UFF 失败、MACE 超时、结构缺陷分别去哪里？ |
| 身份与新颖性证据 | 批次重复、公开数据库匹配、训练外片段、MOFid 身份各自比较什么？ |
| 性能评价与历史反馈 | 特征、代理、适用域、Widom、GCMC、公平对照和历史反馈怎样衔接？ |
| 工作队列与依赖 | P0–P3 分别交付什么，哪些任务可并行，哪些依赖前面的证据？ |

操作：切换视图 → 点击节点 → 读取验收和文件依据；“追踪上游 / 下游”突出当前视图的依赖路径。“适合宽度”调整地图显示比例，画布可滚动。“导出当前图”生成独立 SVG。工作备注保存在当前浏览器。

旧版 12 模块 [概览图](generation/project-map.html) 保留作为历史版本。

## 1. 目标和当前工作

最终目标：需求描述 → 结构化条件与约束 → 提出多个 MOF 候选 → 输出带来源和验证结果的 CIF。

当前工作：在已有结构生产与验收基础上封装可调用模块，明确支持范围和结果交付。化学/结构有效性、身份、新颖性与成本逐层报告；分离性能和命中密度用于具体应用验证。

主线：

```text
训练数据 / 模型权重
        ↓
MOFDiff / MOFFlow-2 / EGMOF
        ↓
解码、组装、CIF 与来源元数据
        ↓
化学过滤 + 原始几何检查 + UFF/MACE 弛豫
        ↓
StructureMatcher 去重 + 构筑块比对 + MOFid 身份验证
        ↓
统一指标、失败归因、成本和对照
        ↓
定位问题 → 改进生成 → 独立批次验证
```

性能链：合格 CIF → Zeo++ / PACMOF → 代理与适用域 → Widom / GCMC → 同预算比较与反馈选择。11月16日新条件试验已完成96项吸附对照；下一轮性能反馈效果待登记验证。

总览箭头表达逻辑依赖；各阶段当前由独立脚本与服务器任务执行。交互图展示模块级概览，以下清单记录子功能。

## 2. 功能清单

状态含义：**已实现**＝有代码和执行记录；**部分完成**＝仍有明确覆盖或实验缺口；**研究试点**＝可运行的探索路线；**规划**＝尚待实现；**暂停**＝保留既有能力、本轮不扩展。

| 模块 | 已有功能与产物 | 当前状态 / 下一缺口 | 主要依据 |
|---|---|---|---|
| 公开数据 | CSD、CoRE、hMOF、MOSAEC、CRAFTED 镜像，化学式/体积索引 | 已实现；BW-DB 下载受阻 | `worklog.md`；`generation/mofdiff_plausibility/fast_db_index.py` |
| 训练资产 | 三引擎公开权重及推理环境；MOFFlow-2 序列与结构 LMDB | 已具备；训练集覆盖按引擎核验 | `worklog.md`；`generation/mofid_prepare.py` |
| MOFDiff | 粗粒化扩散采样、构筑块匹配、全原子组装、CIF | 千样本结构评估完成；425/720结构有效 | `worklog.md`；`generation/structure_generation_quality.md` |
| MOFFlow-2 | 条件序列生成、三维预测、CIF 转换 | 已跑通；1000 样本质量评估完成 | `generation/convert_mofflow2_predictions.py`；`generation/scale1000_mofflow2/` |
| EGMOF | 性质→描述符→构筑块/拓扑→PORMAKE→CIF | 千样本结构评估完成；659/751结构有效 | `generation/egmof_scale.py`；`worklog.md` |
| 规则变体设计 | 种子单取代、价键与连接数约束、候选池 | 已实现，保留基线 | `generation/enumerate_variants.py`；`generation/README.md` |
| 化学锚点 | 结合位点识别、构象与连接方向、构筑块导出 | 已实现 | `anchor_rules/anchor_rules.py`；`anchor_rules/README.md` |
| 拓扑组装 | 节点/配体/拓扑匹配、PORMAKE、碰撞与方向检查 | 已实现 | `generation/build_candidates.py`；`anchor_rules/assembly_test.py` |
| Nexerra 配体路线 | 分子生成接入、SMILES→变体、刚性与锚点过滤 | 研究试点；可用产出低，待路线重设计 | `generation/nexerra_to_variants.py`；`generation/producer_feasibility.md`；`worklog.md` |
| 粗粒化自组装 | 配体→patchy 模型、HOOMD 运行、占位/连通/环统计 | 研究试点，当前主线外保留 | `cg_assembly/README.md`；`cg_assembly/cg_build.py`；`cg_assembly/analyze_cg.py` |
| 化学有效性 | RDKit、自由基、电荷、结合基团、guest、SAscore | 已实现；序列级与片段级分别统计 | `generation/mofdiff_plausibility/filter_generated_sbus.py`；`chem_filter_seqs.py` |
| 原始结构检查 | 原子短接触、连通片段、金属配位、组成 | 已实现；几何判据属近似检查 | `generation/mofdiff_plausibility/precheck_dir.py` |
| 弛豫与故障分类 | UFF / LAMMPS、MACE fallback、体积与原子数检查、超时记录 | 已实现；工具失败和未解决样本单列 | `generation/mofdiff_plausibility/uff_relax_standalone.py`；`combine_mace.py` |
| 结构去重 | StructureMatcher、化学式/体积预筛、重复组 | 已实现 | `generation/mofdiff_plausibility/dedup_dir2.py` |
| 数据库结构比对 | 36.5 万参考 CIF，精确预筛与部分有界宽松搜索 | 已实现指定口径；库与搜索覆盖单列 | `generation/mofdiff_plausibility/novelty_lookup.py`；`novelty_loose.py` |
| 序列构筑块新颖性 | canonical SMILES 训练集集合差、最近邻相似性、化学审查 | 已实现；千样本新片段审查待补全 | `generation/mofdiff_plausibility/mofflow2_bb_novelty.py`；`review_novel_sbus.py` |
| MOFid 实测验证 | 从 CIF 提取节点/连接体/拓扑，控制实验，原始/弛豫身份比较 | 生成与187047训练参考处理完成；15069条部分解析待核查 | `generation/mofid_validation.md`；`generation/mofid_validation/` |
| 历史 MOFid 字段索引 | 规则候选与 CoRE 已有 MOFid 字段构成的组合键比对 | 已实现历史口径；与本轮从 CIF 实测分开 | `generation/novelty_core.py`；`generation/README.md` |
| 统一生成评估 | 可组装率、几何/化学有效率、唯一率、金属/体积覆盖 | 千样本结构汇总、两个新种子的条件/性能对照已完成 | `generation/structure_quality/`；`generation/conditional_response/REPORT.md` |
| 孔道描述符 | Zeo++ 孔径、可达体积、密度等 | 已实现，性能支线资产 | `widom_sih4/zeo_features.py` |
| 电荷与化学特征 | PACMOF 充电、元素/金属组成、电荷统计 | 已实现，弛豫后结构需要重新计算 | `widom_sih4/pacmof_batch.py`；`chem_features_pacmof.py` |
| 代理模型与 OOD | LightGBM、适用域、组装结构扩训、学习曲线、生成域检验 | 已实现；MOFDiff 域排序失效已确认 | `widom_sih4/applicability_domain.py`；`ood_augment_eval.py`；`generation/mofdiff_aug_eval.py` |
| Widom 标签 | 输入生成、np/pol、Henry 常数、误差与选择性解析 | 最新24候选各两个种子均完成 | `generation/conditional_response/results/performance/`；`widom_sih4/parse_widom.py` |
| 混合 GCMC | 多组分输入、超胞、条件设置、吸附量与选择性解析 | 最新24候选各两个种子均完成 | `generation/conditional_response/results/performance/`；`generation/parse_gcmc.py` |
| 公平性能对照 | 冻结阈值、同预算设计池/已知库、重复划分、全池普查 | 已有结果；依历史任务与阈值解释 | `generation/pilot_selection/fair_compare_report.md`；`generation/pilot_selection/exhaustive/` |
| 反馈选择 | 根据真实评价更新后续候选选择，保留预测登记 | 规则路线已试验；生成器闭环改进待验证 | `generation/pilot_selection/`；`generation/validate_predictions.py`；`worklog.md` |
| 可合成性桌面评估 | 配体难度指标、类似物与合成先例整理 | 部分桌面工作；实验当前无执行条件 | `generation/pilot_selection/synthesis_assessment.md`；`NEXT_STEPS.md` |
| 自然语言任务入口 | 需求解析、统一条件/约束、批次追踪与多 CIF 返回 | 规划 | `NEXT_STEPS.md` 第7节 |
| 条件可控性验证 | 同引擎不同条件、配对种子、固定预算，统一结构与性能评价 | 首轮2400序列和96吸附任务完成，性能迁移结论已归档 | `generation/conditional_response/REPORT.md` |
| 生成方法改进 | 失败归因、组装/姿态改进、性能反馈与独立验证 | 组合与精修已有数据；项目性能反馈待下一轮验证 | `PROJECT_OVERVIEW.md`；`worklog.md` |

## 3. 当前工作队列与验收条件

| 优先级 | 工作 | 完成时需要看到什么 |
|---|---|---|
| P0 | 明确模块边界与输入输出 | 受支持配置、候选CIF、ID、来源、验证状态、失败与预算语义 |
| P1 | 封装已验证的生成/组装/验收路线 | 统一调用、任务编排和显式引擎支持范围 |
| P1 | 小批端到端模块验收 | 从配置到多CIF交付、进度/异常/日志及可复现记录 |
| P2 | 补强数值稳健性与参考覆盖 | 重点候选的延长/重复模拟、力场或工况敏感性、MOFid部分解析清单 |
| P2 | 评估更复杂引导与DAO-P适用性 | 明确瓶颈、MOF适用性、独立增益、质量/多样性/成本 |
| 按需扩展 | 自然语言入口和更多引擎/应用 | 在统一模块接口上扩展，逐项验证支持范围与案例效果 |

## 4. 使用与维护

- 每次新批次或结论变化，先追加 `worklog.md`，再更新本表的状态和证据。
- 地图维护模块级能力；实时任务数量留在日志，减少地图因运行进度频繁过期。
- 既有、进行中、规划三个层级分别记录；“能运行”“通过验证”“有研究增益”使用各自验收条件。
- 讨论下一步时，先选工作队列的一项，明确输入、产物和验收条件，再启动计算。

新版数据与内容：`generation/build_workbench.py`、`generation/project-workbench.data.json`。页面模板：`generation/project-workbench.template.html`。执行 `python generation/build_workbench.py` 生成可离线打开的 `generation/project-workbench.html`。

新版浏览器与交互检查：`generation/check_workbench.mjs`；结果 `generation/project-workbench.check.json`。检查六个视图的节点文本与连线、上游/下游追踪、搜索、备注、缩放，以及实际导出 SVG 的 XML 完整性。`project-workbench.*.png` 为浏览器截图。

入口服务：`generation/serve_workbench.py`，仅绑定 `127.0.0.1`，提供工作台和显式引用的证据文件。执行 `python generation/serve_workbench.py --ensure --open` 可启动并打开；重复执行会复用现有进程。入口与证据检查记录：`generation/workbench-entry-check.json`。浏览器检查也覆盖 600/900 像素窄窗口。

工作台与功能清单已更新为2026-11-17快照；下方为各历史批次的记录，当前思路以PROJECT_OVERVIEW.md和上方工作队列为准。


## 2026-11-13：组合小试v2与解释更正

同一20连接体四臂联合终点：原生A 0/20、旧直线预筛B1 1/20、无预筛pcu/N16的U 20/20、几何匹配M 17/20。完成39次唯一新正式弛豫、3次校准和官方MOFid；40个U/M臂落盘独立复核一致。U全部收敛且拓扑pcu，20种完整框架身份在171978条完整训练参考中未匹配；15069条参考部分解析。原序列训练外8连接体U全部通过，M通过6个。

v1把19次手工预筛拒绝解释为模板不适配，判断过强；U实验直接显示预筛误拒。另修正L03/L07/L16非羧酸负氧归一化，原生连接体恢复总数保持5。M策略改变金属/拓扑，当前未超过简单U方案。后续独立批次验证优先。证据：generation/linker_framework_pilot_v2/results/REPORT.md 与 AUDIT.json；完整CIF和日志已归档。


## 直线门槛来源补充核查

原有anchor_rules用两端方向互角≥160°标记linear；v1新增的每端相对X–X轴≤20°硬拒绝与它不等价。旧20样本两端互角167.9–179.8°，按原规则全部linear。17个v1/v2构筑块哈希相同，其中16个旧门槛拒绝者在U全部通过；其余3个归一化修正单列。详见generation/linker_framework_pilot_v2/results/GATE_CHECK.md。此前把这些样本概括为弯曲连接体以及“与现有锚点判据一致”的描述均已修正。


## 2026-11-13：留出20连接体确认

从同一千样本池中排除既有连接体及归一化同身份，固定哈希排序选20种，构象种子19。原生A联合终点0/20、无预筛pcu/N16组装U 20/20；几何A 2/20、U 20/20；收敛A 1/20、U 19/20。旧20°门槛会拒绝19个，其中19个实际通过联合终点。

本轮20种原序列片段均在训练集合中出现；验证范围是同生成批次的留出连接体。U获得20种完整框架身份；训练参考已处理187047条、完整171978条，命中完整身份数1。证据：generation/linker_framework_holdout/results/REPORT.md。下一阶段优先用全新生成批次与多构象种子复核，并补配位几何和稳定性评价。


## 2026-11-13：Review修复落地

新版本显式skin=0；加入任务输入/模型/脚本/参数签名、输出CIF校验和、启动前全量恢复校验与冻结文件校验。13项测试通过，含运行器拒绝旧记录和安全复用两项集成测试；40个归档CIF复算最终几何判定变化0。历史results及服务器实验目录保持冻结，新增计算必须使用新目录。版本说明：generation/linker_framework_holdout/REVISION.md。


## 2026-11-13：配位几何与严格收敛复核完成

40个U结构、160个Zn位点在2.3/2.5 Å截断均四配位；2.7 Å下L12和H05各有一额外O近邻。角RMS范围1.99–12.80°，原BDC控制约2.3°。对L12/H05/H12/H01及BDC控制从既有CIF继续最多300步、fmax0.05：5/5收敛且几何、连接体与pcu身份保持。4个诊断样本角RMS均减小，L12 12.80→8.91、H05 9.05→6.60、H12 4.95→4.24、H01 9.54→4.89°。控制2.33→5.03°；L12的2.7 Å额外近邻仍在，暂保留连续诊断量，不设角度淘汰阈值。能量变化用于优化检查，热力学稳定性仍待参考体系计算。真实5任务签名复用复核通过，优化日志与输出CIF保持不变。证据：generation/coordination_followup/results/REPORT.md与RESUME_AUDIT.json。


## 2026-11-13：全新生成批次719完成

固定生成200序列，化学筛选并排除已测试40种归一化连接体后得到18种，全部冻结，无补采样。A原生、U7/U19双构象固定pcu/N16三臂联合终点分别0/18、16/18、18/18；两种子均通过16/18、至少一种通过18/18。唯一正式弛豫54次。参考完整身份171978条，U身份命中2种；部分解析缺口保留。

证据：generation/linker_framework_fresh/results/REPORT.md、AUDIT.json及comparison.png。该批检验固定条件下的跨随机批次和双构象稳健性；条件响应、配位应变和吸附性能另评。DAO-P继续保留备选。


## 2026-11-13：构象敏感诊断与预处理负结果

F11/F14种子7存在跨连接体的严重碰撞，伴随能量异常下降、残余力增长；成功F04也有初始短接触，因此未新增初始距离硬拒绝。固定6案例对照：50步成键约束几何预处理+100步MACE，两失败者恢复0/2、成功控制保持3/4；预处理虽清除了初始短接触并保持构造键长，后续仍出现断片/额外自由基片段。该版本不进入主流程，保留双构象组装方案，不继续按这6例调参。

新增严格连接体类型集合/预期拓扑验收，9项测试通过，原新批次34个已接受U输出保持通过。独立核查6个历史同输入、签名、预处理键长变化及最终指标通过。证据：generation/steric_diagnosis/REPORT.md、generation/steric_precondition/results/REPORT.md、DECISION.md。


## 2026-11-13：结构生成同预算确认阶段结项

用户授权持续做到本阶段结束。固定600序列（seed1301），排除既有58种归一化连接体，31种合格新身份中哈希冻结30种。严格终点：原生300步0/30、单构象7最多300步26/30、双构象7/19各150步28/30；配对26均通过、2仅双通过、2均未通过。单位有效框架GPU任务墙钟63.20秒与101.65秒，双构象约+60.8%，按预登记20%成本取舍默认推荐单构象，双构象保留较高成本选项。

完成92次正式物理任务+2控制，120个正式逻辑分支，28条早收敛合法复用；14项测试及完整签名/预算/成本审计通过。4个训练片段未匹配连接体两方案均4/4通过。28种有效框架MOFid身份在171978条完整训练参考中均未匹配，15069条参考部分解析缺口保留。已交付26个默认策略CIF，均收敛且哈希核对通过。

边界：固定目标5.0、二羧酸、pcu/Zn4O；本批20–32重原子/C,N,O,S。B25两构象几何失败，B29两构象连接体类型未保持；B29额外净负电基团的配位/补偿未建模，未事后剔除。实际预测20条/批而非计划8、末尾CR导致启动器在审计后非零退出、两坏结构复读差异均单列，统计和MACE预算不变。

结项：generation/budget_confirmation/PHASE_CLOSEOUT.md；候选包deliverables/manifest.json；比较图results/comparison.png。本结构确认阶段到此结束，不继续逐例修复。下一阶段另行登记目标条件响应与吸附性能，DAO-P维持备选。
