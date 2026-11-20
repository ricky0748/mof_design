# 生产端技术可行性对照

2026-10-23 · 按 `NEXT_STEPS.md` 第 4 项执行 · 只核查“能否跑、能否适配、产物能否接现有接口”，不重复写综述

---

## 0. 先核查的数据口径

- `generation/scored_full.csv` 的 `pred_S_CO2` 等字段是 **log10 选择性**：`pred_S_CO2 > 0` 表示预测 `K_CO2/K_SiH4 > 1`，不是原始选择性大于 0。后续报告统一写“logS_CO2”或“S_CO2 > 1”。
- Novelty 按互斥分层核实：`scored_full_novelty.csv` 中 **exact 7 / topo+ligand 3 / metal+ligand 4 / no_match 254**（合计 268）。`novelty_core.csv` 的原始 `n_topolinker>0 = 10`、`n_metallinker>0 = 12` 有重叠；此前报告中的 256 是 fallback 拓扑前的旧数，应以互斥分层的 254 为准。
- 58 个“路由至精算”只是标记，并不代表 58 个 GCMC 已完成；实际完成的是 12 个历史 GCMC 验证结构。它们不构成新的前瞻性测试。

---

## 1. 路线对照

| 路线 | 代码/资产状态 | 已确认 | 接口差异 | 预计工作范围 | 最小试验 |
|---|---|---|---|---|---|
| **现有规则 + 反馈搜索** | 本地已有 `enumerate_variants.py`、`build_candidates.py`、`score_candidates_full.py`、Widom/GCMC 脚本 | **可运行**；不需要新资产 | 配体变体 → 锚点 → PORMAKE CIF，接口已通 | **低**：实现 BO/进化选择器，复用现有代理与精判 | 2 轮 × 10–20 个候选，真实 Widom/GCMC 标签，比较初始批次 vs 反馈批次 |
| **RFcode / SmVAE** | `zhenpengyao/Supramolecular_VAE`；Python 3.7 + PyTorch + RDKit + SELFIES 0.2.4；环境较旧 | 代码在，但**未发现预训练权重**；需训练/适配 | RFcode（edge/node/topology）+ reconstructor；生成的是 SELFIES 边和拓扑 | **中高**：旧环境、训练 VAE + 性质模型、组装器适配 | 克隆/建环境，跑训练 notebook 的最小 epoch；确认重构器和数据格式 |
| **MOFDiff** | `microsoft/MOFDiff`；预训练 0.13GB + BW-DB 3.99GB + BB embedding 2.13GB；需要 mamba/MOFid/Zeo++/RASPA/eGULP | 代码和权重在；环境重 | 粗粒化构筑块组合 → 全原子组装；**不能生成新构筑块** | **高**：约 6GB 资产、重环境、CG→原子组装和性质模型适配 | 下载 pretrained（0.13GB），跑一次无条件采样 + assemble；确认能否接我们的评估 |
| **LEGO-MOF** | arXiv v1 声明代码 upon reasonable request；无公开 repo/权重 | **不可运行** | 配体级 VAE + 虚拟 He 锚点；接口理论接近 | **阻塞**：需联系作者；未经授权不联系 | 无（记录为阻塞项） |
| **EGMOF** | `Yeonghun1675/EGMOF`；desc2mof 79MB + mof2desc 29MB；prop2desc 3.0GB + rf 3.5GB；`generate(target_value, build_cif=True)` | 代码在；小资产可下；**原生 183 维描述符与 G+Chem/PACMOF 不同** | 183 维 RAC+Zeo++ 描述符 → desc2mof → SELFIES 构筑块 → PORMAKE；新构筑块需要 xtb | **中**：desc2mof 冒烟低；目标引导需计算 183 维描述符并训练 SiH4/CO2 的 prop2desc（中高） | 只下 desc2mof+mof2desc（108MB），用 V0164_nbo 的 183 维描述符做一次 desc2mof→CIF 冒烟；不动 11GB 全量 |

---

## 2. 各路线细节

### 2.1 现有规则 + 反馈搜索（推荐主试点）

**已确认**：

- 生成端 `enumerate_variants.py` 支持种子、取代基、连接数过滤；`build_candidates.py` 支持 pcu/fcu/nbo/tbo 组装和几何判据。
- 评价端 `score_candidates_full.py` 输出 8 个 log10 选择性；`applicability_domain.py` 给出 proxy/gcmc 路由；Widom/GCMC 脚本已跑通。
- 不需要新下载、新环境；候选、标签、模型都在本地。

**未确认/要补**：

- 目前只有“固定枚举后排序”，没有“用真实反馈决定下一批修改”的闭环。
- 需要一个候选空间（种子 × 取代基 × 拓扑，或种子 × 多取代 × 节点）和选择器（BO/进化/UCB）。
- 需要防止代理自评分被当成优化成功；必须用独立 Widom/GCMC 标签评估。

**接口**：统一候选记录沿用 `candidate_id, seed, smiles, node, topo, cif, engine_version, parent_id, condition, pred_*, label_*`。

### 2.2 RFcode / SmVAE

**已确认**：

- 代码在 `zhenpengyao/Supramolecular_VAE`；论文 Nat Mach Intell 2021。
- `environment.yml`：Python 3.7、PyTorch、RDKit、SELFIES 0.2.4、CUDA 10.1，环境较旧。
- 生成的是 RFcode 的 edge/node/topology；edge 用 SELFIES，理论上能生成新配体。

**未确认**：

- 仓库没有明显的预训练权重；需要训练 VAE + 性质模型。
- 与现有 `anchor_rules`/PORMAKE 的接口需要自己写（RFcode 自带 reconstructor）。
- 我们的 SiH4/CO2 标签能否直接用于其性质模型，需要核实数据格式。

**结论**：可作为备选，但不是低改动试点。

### 2.3 MOFDiff

**已确认**：

- 代码在 `microsoft/MOFDiff`；Zenodo 10467288 提供 pretrained 0.13GB、BW-DB 3.99GB、BB embedding 2.13GB。
- 生成粗粒化 MOF（构筑块身份 + 质心 + 晶胞），组装成全原子 CIF；**不能生成新构筑块**。
- 依赖 mamba 环境、MOFid、Zeo++、RASPA、eGULP；预处理 BW-DB 可能数天。

**结论**：适合“已知构筑块的新组合”，不适合本轮“让目标性能影响新配体提出”的主试点；资产和环境成本高。

### 2.4 LEGO-MOF

- 论文 v1 明确代码 upon reasonable request；无公开 repo/权重。
- 未经授权不联系作者；当前记为阻塞项，不作为随时可跑方案。

### 2.5 EGMOF

**已确认**：

- 代码在 `Yeonghun1675/EGMOF`；`generate(num_samples, target_value, build_cif=True, cif_dir=..., new_bb_dir=...)`。
- 最小资产：desc2mof 79MB、mof2desc 29MB（合计 108MB）；prop2desc 3.0GB、rf 3.5GB 是可选的 property→descriptor 路径。
- 原生描述符 183 维（176 RAC + 7 Zeo++），与我们 G+Chem/PACMOF 特征不同。
- `build_cif` 内部用 PORMAKE 组装；新构筑块用 xtb 优化（`make_bbs.py` 会自动尝试下载 xtb；也可指定已有 xtb）。
- 预置配置有 H2 uptake 和 CO2/CH4/N2 等，但没有 SiH4。

**未确认/要补**：

- `generate(target_value=...)` 需要 prop2desc；如果只做 desc2mof，需要直接用 183 维描述符调用底层接口（需读 `run_desc2mof`）。
- 我们的 SiH4/CO2 标签要接 EGMOF，需要：
  1. 用 EGMOF 的 descriptor 模块（RAC + Zeo++）为 CRAFTED 690 + 132 个组装结构计算 183 维；
  2. 训练一个 SiH4/CO2 的 prop2desc，或用一个目标描述符（例如 V0164_nbo 的）跳过 prop2desc；
  3. 生成后的 SELFIES/拓扑/节点接我们的锚点/组装或 EGMOF 自带 PORMAKE。
- xtb、pormake、PyTorch 环境需要在隔离环境里准备；当前服务器有 Zeo++ 和 PORMAKE，但没有 xtb。

**结论**：desc2mof 冒烟成本低（108MB），值得先做；完整目标引导（prop2desc 训练 + 183 维描述符）是中等偏高工作量，需单独立项/授权。

---

## 3. 推荐

### 主试点：现有规则 + 反馈搜索

理由：

- 完全复用已跑通的生成/评价/精判接口，无新下载/新环境；
- 直接回答下一阶段问题：**目标性能能否影响候选提出**，而不只是固定枚举后排序；
- 反馈搜索的基线明确：同一候选空间里的随机/无目标选择；可做真正的对照。

### 备选：EGMOF desc2mof 冒烟

- 只下 108MB 的 desc2mof + mof2desc；
- 用 V0164_nbo 的 183 维描述符（或其目标描述符）生成 20–50 个 CIF；
- 验收：样例能否生成、SELFIES 新构筑块能否转成配体、PORMAKE 组装成功率、能否接我们的 G+Chem 打分；
- 如果冒烟可行，再评估是否训练 SiH4/CO2 的 prop2desc（中高工作量，另行授权）。

### 暂不做

- 不下载 EGMOF 全量 11GB；不启动 prop2desc 大训练；
- 不下载 MOFDiff 的 6GB 资产/建重环境；
- 不联系 LEGO-MOF 作者、不提交实验、不采购；
- 不把 12 个历史 GCMC 结构当作新的前瞻性对照。

---

## 4. 最小反馈搜索试点方案（待执行）

### 4.1 结构化任务

- 气体与方向：SiH4 主体，去除 CO2；298 K，1 bar，CO2 1000 ppm，SiH4 平衡。
- 目标：`log10 S_CO2` 最大化；同时记录 `q_SiH4`（SiH4 损失/容量）和 `q_CO2`；达标定义需在运行前冻结，建议 `logS_CO2 ≥ 0.3`（S_CO2 ≥ 2）且 `q_SiH4 ≤ 1.5 mol/kg`（依据现有 GCMC 头部候选的 q_SiH4 0.73–1.66）。
- 节点/元素/锚点限制：沿用羧酸锚点；节点 Zn4O/Zr6/Cu 桨轮；拓扑 pcu/fcu/nbo/tbo；配体重原子 ≤ 40，刚性过滤。
- 候选数量：初始批次 20，反馈批次 20；每批选 10 个做真实 Widom/GCMC。

### 4.2 候选空间

- 种子（已知羧酸配体）× 单/双取代基 × 拓扑；或对现有 239 个变体做多取代扩展。
- 用现有 `enumerate_variants.py` 扩展 `--max-subs 2`（需改脚本），或先用单取代空间。
- 初始批次用拉丁超立方/随机；反馈批次用 BO/UCB 或进化（以代理预测 + 不确定度选择）。

### 4.3 评价与对照

- 真实标签：Widom（np+pol）先筛，头部做完整 GCMC；同一条件、同一力场、同一电荷方案。
- 对照：
  - 同一候选空间随机选 10 个；
  - 初始批次 vs 反馈批次；
  - 之后可选“代理辅助的已知库选择”作为第三对照。
- 指标：原始生成数 → 唯一配体数 → 化学/几何通过数 → 域外比例 → 精算数 → 达标数；每个达标结构的精算次数与总机时；重复种子的区间。

### 4.4 登记与目录

- 目录：`generation/pilot_feedback/`，不覆盖现有 268 个候选和 Nexerra 结果。
- 精算前在 worklog 登记：候选文件路径 + sha256、模型版本、预测值与置信度、达标标准；登记后不改。
- 原始输出、拒绝原因、漏斗 CSV、简短结果报告全部保留。

---

## 5. 证据与版本

- EGMOF：`Yeonghun1675/EGMOF`；README/`src/egmof/egmof.py`；checkpoints 大小见 README；Zenodo 19362907。
- MOFDiff：`microsoft/MOFDiff`；README；Zenodo 10467288（pretrained 0.13GB、BW-DB 3.99GB、BB embedding 2.13GB）。
- RFcode/SmVAE：`zhenpengyao/Supramolecular_VAE`；environment.yml（Python 3.7、SELFIES 0.2.4、CUDA 10.1）。
- LEGO-MOF：arXiv 2604.13520 v1（代码 upon request）。
- 本地接口：`generation/enumerate_variants.py`、`build_candidates.py`、`score_candidates_full.py`、`nexerra_to_variants.py`。

---

## 6. 证据边界

- “代码可跑”不等于“候选质量合格”；本文件只做可行性，不宣称任何生成路线已经优于规则式基线。
- 规则生成 CIF、模型生成 CIF、目标引导生成必须分别标注；数据库无匹配不等于全球首创。
- 预测 > 0 是 log10 选择性 > 0（原始选择性 > 1），不是原始选择性大于 0。
- 58 个域外路由不等于 58 个 GCMC 已完成；已有 12 个 GCMC 是历史验证，不是前瞻性对照。


## 2026-11-13 后续备选：DAO / DAO-P

用户决定先完成现有测试，再考虑接入DAO-P。优先核对噪声中间态能量预测、坐标/晶胞梯度引导及生成—预测协同；先验证无机小晶胞预训练向MOF的迁移与能量标尺。尚未安装或复现。详细登记：[DAO_CANDIDATE.md](DAO_CANDIDATE.md)。
