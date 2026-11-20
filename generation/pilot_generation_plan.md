# 生成端小规模试点计划（MOFDiff / MOFFlow-2 / EGMOF）

2026-10-30 · 纯计算 · 在验证收尾后执行

## 1. 目的

现有工作回答的是“候选是否可靠”（代理 + Widom/GCMC + 适用域 + novelty）。
下一阶段要回答：**AI 能否按需求提出更好的新结构**，而不只是在固定枚举里做筛选。

试点不追求大规模，而是用小预算回答三个可判定的问题：

1. 三个生成引擎能否在本机跑通并产出可组装的 CIF（最小可运行条件）。
2. 在相同预算下，生成候选的合法率、护栏通过率、命中密度是否优于规则式基线。
3. 目标条件（SiH₄/CO₂ 选择性）能否影响生成，而不是只影响事后排序。

## 2. 引擎与资产核查（2026-10-30）

| 引擎 | 论文/代码 | 许可 | 权重与数据 | 运行环境 | 备注 |
|---|---|---|---|---|---|
| EGMOF | arXiv 2511.03122v3；github.com/Yeonghun1675/EGMOF；Zenodo 19362907 | MIT | `prop2desc` ~3.0 GB + config；`desc2mof` 79 MB；`mof2desc` 29 MB；全部约 11 GB（含 RF 3.5 GB，非必需） | `uv sync`；CPU 或 CUDA；生成时 xtb + PORMAKE | 直接支持 `target_value`、`build_cif=True`；183 维描述符，与本项目 G+Chem 不同 |
| MOFFlow-2 | NeurIPS 2025；arXiv 2505.17914；github.com/nayoung10/MOFFlow-2 | MIT | 检查点 Zenodo 17163237 / HF `nayoung10/mofflow2-ckpt`；数据 HF `nayoung10/mofflow2-data` | mamba `env.yml`；依赖 `pip install git+https://github.com/microsoft/MOFDiff.git`；GPU | 两阶段：SMILES 自回归生成构筑块 + flow matching 组装；支持条件序列生成 |
| MOFDiff | arXiv 2310.10732；github.com/microsoft/MOFDiff | MIT | Zenodo 预训练权重；BW-DB 预处理数据 | mamba；GPU | 需要 BW-DB 域；作为基线与 MOFFlow-2 共用依赖 |

服务器现状：8× RTX 3090（24 GB）、`/share` 剩余 1.8 TB、可访问 Zenodo；系统 python 无 torch，需隔离环境（`uv`/mamba），**不得 pip 安装到系统用户包**（历史事故）。

## 3. 小批量试点设计（每个引擎）

### 3.1 采样

- 固定随机种子；每引擎 **100 个原始样本**（smoke test 先用 10 个）。
- EGMOF：`target_value` 先映射到“高 CO₂/SiH₄ 选择性”的代理目标（用现有代理对目标值做标定，或先跑无条件/中性目标作为对照）。
- MOFFlow-2 / MOFDiff：条件序列 + 结构预测；记录条件向量与采样参数。
- 原始输出、失败原因、版本/检查点哈希全部保留。

### 3.2 统一漏斗（沿用现有接口）

原始样本 → 合法构筑块/序列 → PORMAKE 组装 CIF → 几何检查（D_fs ≥ 3.3 Å、AV ≥ 0.02）→ PACMOF 电荷 → G+Chem 特征 → 代理 + 适用域 → Widom/GCMC。

### 3.3 精算预算

- 每引擎取漏斗通过者中代理 UCB 前 15 个，做与普查相同的二元 GCMC（298 K、1 bar、CO₂ 1000 ppm、PACMOF/UFF/Ewald、30k/5k）。
- 对照：同预算的规则式候选 15 个（随机 15 + UCB 15）。
- 判定沿用冻结标准（logS_CO2 ≥ 0.3、q_SiH4 ≤ 1.5、q_CO2 ≥ 0.001），并报告选择性–容量取舍，不只报命中数。

### 3.4 评估指标

- 原始数 → 唯一合法数 → 可组装数 → 几何通过数 → 域内数 → 精算数 → 达标数（完整漏斗 CSV）。
- 新颖性：CSD / CoRE 2024 / CoRE 2019 结构级比对（沿用 `structure_novelty.py`），记录数据库覆盖数。
- 与规则式基线比较：同预算命中密度、组装的失败模式、化学多样性（金属/拓扑/配体）。

## 4. 执行顺序与门槛

1. **EGMOF 先行**：目标条件接口最直接、可 CPU、直接产出 CIF；先做 10 样本 smoke test，确认环境与组装链。
2. **MOFFlow-2 次之**：需要 GPU 与 MOFDiff 依赖；先做无条件 10 样本，再做条件 100 样本。
3. **MOFDiff 作为基线**：与 MOFFlow-2 共用 BW-DB 与部分依赖；只跑到能形成同预算对照的最小规模。

每个引擎的继续/停止门槛：smoke test 能产出 ≥1 个可组装 CIF；100 样本中可组装率 ≥10% 才进入精算；否则记录失败模式并停止扩容。

## 5. 已知风险

- **目标域不匹配**：EGMOF 的 Prop2Desc 与 MOFDiff/MOFFlow-2 的预训练目标主要是气体吸附量（BW-DB），不是 SiH₄/CO₂ 痕量选择性；`target_value` 只能作为代理目标，需明确标注，不能声称“按选择性生成”。
- **描述符/构筑块域**：生成模型的构筑块库与 CRAFTED/CoRE 不同；代理适用域必须重新检查，命中率不能直接外推。
- **资源**：GPU 为共享资源；下载总量可能 >10 GB；环境隔离优先。
- **结论口径**：生成 CIF ≠ 新材料；数据库无匹配 ≠ 首创；预测 ≠ 模拟 ≠ 实验。

## 6. 交付物

- 每引擎独立目录：命令、版本、种子、原始输出、漏斗 CSV、失败原因。
- 一份同预算对照报告：生成 vs 规则式，含命中率、容量–选择性取舍、novelty 覆盖数。
- 是否扩到 1000 样本的决策建议（基于 smoke + 100 样本的合法率与命中密度）。
