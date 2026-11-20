# AI 生成式 MOF 设计：研发工作日志

记录约定：每条记录写日期、做了什么、产出物、结论/发现、遗留问题。新记录追加在最后。

---

## 2026-10-16 ① 读启动文档，确认项目意图

- **做了什么**：读了《AI 生成式 MOF 设计：项目启动文档.md》。
- **要点**：
  - 本项目是筛选管线的第 0 步，任务是扩大候选来源，不替代后面的评估层。
  - 路线是约束式逆向设计：节点和拓扑固定，用种子邻域采样和 scaffold 约束生成配体。
  - 成功标准：评估预算相同时，生成候选中高分结构的占比高于直接从已知库筛选。
- **遗留**：5 个待决问题（体系选择、对照组设计、代理模型特征、技术路线、客户口径）。

## 2026-10-16 ② 文献精读（paper/ 下 17 个 PDF，实读 16 篇）

- **产出**：`AI生成式MOF设计_文献阅读笔记.md`
- **主要发现**：
  - 成功标准有现成口径：MOFDiff 用"每命中一个达标结构所需的 GCMC 次数"衡量，随机从 BW-DB 抽要 58.1 次，MOFDiff 降到 14.6 次。对照实验可以直接采用这个指标。
  - 代理模型分布外失效是最大风险：GHP-MOFassemble 的 CGCNN 测试集 R² 0.93，但生成结构上精确率只有 6/102 ≈ 5.9%，接近基数。EGMOF 发现命中率与"描述符 → 性质"的 R² 正相关。
  - 力场弛豫对有效率影响很大：MOFDiff 带 UFF 弛豫时有效率 30.1%，不弛豫只有 10.13%。
  - 锚点处理有两种可借鉴的做法：LEGO-MOF 在真实配位原子断键处放虚拟 He；GHP 按化学规则识别羧酸 C、唑 N。
  - MOFSimBench：MACE-MP-0a 在 MOF 上势能面偏软；OMat24 训练的模型更好。
- **启动文档需要更正的地方**：
  - GHP 的"56% 未过价键检查"指的是训练集配体，不是生成配体。
  - `jacs.6c09208.pdf` 下错了，不是 Nexerra。
  - tobascco（Boyd & Woo）和 ToBaCCo（Colón & Snurr）是两套代码，需要区分。
  - MOFFUSION 就是待补 DOI 的 Park, Lee, Kim, Nat Commun 2025 那篇。
- **遗留**：重新下载 Nexerra；补读 Inizan 等和 MOFA；核对 Comlek 是哪个版本。

## 2026-10-16 ③ "描述符 → 选择性"R² 摸底

- **目的**：在决定代理模型输入特征（待决问题 3）之前，先看现有特征能解释多少选择性方差。
- **数据变更**：gcmc_mof 文件夹里没有 SiH4 的批量筛选数据（那个项目是几十个材料的 GCMC 准确度验证），C2H2 数据不在本地。改用"MOF-公开数据库"里的 CRAFTED-2.0.0：690 个 CoRE-2014 MOF，6 种电荷方案 × 2 种力场，CO2/N2，298 K，自带 RAC 和几何描述符。
- **流程**：
  1. 在本机抽取等温线（`extract_crafted.py`），并从 DDEC CIF 提取化学/电荷特征（`cif_chem_features.py`）。
  2. 在云端做双位点 Langmuir 拟合和 IAST（`build_targets.py`）。
  3. LightGBM 5 折 × 5 次交叉验证（`r2_probe.py`），再做稳健性检查（`robustness.py`）。
- **产出**：`r2_probe/R2摸底报告.md`，以及配套的脚本和结果 CSV。
- **结果**（主标签 DDEC/UFF，n = 654）：
  - 纯几何特征：选择性 R² 0.42–0.52，ρ ≈ 0.7。
  - 加化学/电荷特征后：R² 0.64–0.70，ρ ≈ 0.84，EF10 约 5.6–6.4。
  - 28 个简单的元素/电荷统计特征 ≈ 176 个 RAC。
  - 用 DSL 外推的 Henry 选择性 R² 只有 0.31；改用经验低压比后升到 0.70。原因是低压区 GCMC 噪声很大，拟合外推把它放大了。
  - 换电荷方案后，标签之间的 ρ 只有 0.70–0.79，和模型误差同一量级。
- **结论**：
  - 几何特征缺的主要是静电部分，简单的电荷统计就能补回来。
  - 痕量组分的 Henry 常数要用 Widom 插入直接算，不要从等温线外推。
  - 限制代理模型的主要是标签的方法学不确定度，不是特征。
- **局限**：
  - CO2/N2 不是痕量杂质分离。
  - 金属以 Zn 为主。
  - 交叉验证属于分布内表现，生成结构上要单独验证。
- **遗留**：
  - 拿到 SiH4 或 C2H2 的批量数据后，用同一套脚本重跑。
  - 口袋级特征（开放金属位、芳环间距、孔口官能团）还没做。

## 2026-10-16 ④ SiH4 + 常规杂质 Widom 输入准备（CRAFTED 690 MOF）

- **目的**：给 R² 摸底提供痕量体系的标签。上一轮发现低压选择性靠等温线外推噪声太大，这次改用 Widom 直接算 Henry 常数。
- **确认的范围**：杂质先做常规气体（H2、N2、O2、Ar、CH4、CO、CO2）；MOF 用 CRAFTED 690；只准备输入，计算由我自己提交。
- **设定**：
  - 框架沿用 CRAFTED 的 UFF + DDEC 电荷和各自的 UnitCells，与 CO2/N2 摸底同口径。
  - 分子拆成两组：np 组（SiH4、H2、Ar、CH4，不开 Ewald）和 pol 组（N2、O2、CO、CO2，开 Ewald）。
  - 298 K，5000 cycles。
  - SiH4 用单位点 LJ（ε/k = 207.6 K，σ = 4.084 Å，Svehla 1962）。这是最弱的一环，绝对选择性不能直接用于工艺判断。
- **验证**：在云端编译 RASPA 2.0.4，用 ABUWOJ 测试：
  - 8 分子合跑与拆成两组跑，结果一致。
  - Widom K_N2 与 CRAFTED 等温线外推值一致（8.1e-6 vs 8.0e-6）；K_CO2 在误差内一致；CO2 吸附能 −40.1 vs −40.2 kJ/mol。
  - 耗时：np 组 60 s，pol 组 392 s（2000 cycles）。
- **产出**：`widom_sih4/`，包括 README、力场与分子定义、`make_inputs.py`、`launch.sh`（并行、超时、断点续跑）、`parse_widom.py`、`analyze_henry.py`、可选的 `make_blocks.sh`（未测试），以及 `runs/`（1380 个 run 目录，已打包为 `runs.tar.gz`，3.5 MB）。
- **机时**：总计约 270 核时，64 核约 4 小时；最慢单任务约 0.8 小时。
- **遗留**：
  - 计算完成后跑 `parse_widom.py` 和 `analyze_henry.py`。
  - SiH4 力场需要校验（第二维里系数，或换多位点模型对照）。
  - 不可及孔袋的屏蔽（Zeo++ block 文件）尚未启用。

## 2026-10-19 ⑤ 补读 Predictive Synthesis of MOFs and COFs（arXiv 2610.12739）

- **状态核对**：Widom 结果还没回来，本地 `widom_sih4/runs/` 下没有输出。
- **产出**：笔记追加在《AI生成式MOF设计_文献阅读笔记.md》末尾。
- **要点**：这是一篇观点文章，没有新数据。它把合成看成"轨迹"；把预测任务分成三级；把合成先验分成三类（范围型、性质型、构型约束型）；把失败分成三类。
- **对项目的启示**：
  - 生成配体要附带"范围型先验"检索，查不到合成先例的单独标记。
  - 拓扑不要用 one-hot 编码 RCSR 符号。
  - 前瞻性评估：对照实验的候选名单和模型版本，要在精算之前登记到 worklog 并固定。
- **评估**：价值有限。没有新方法和新数据，优先级定为"低"，远不如 MOFDiff。
- **决定（已确认）**：确立项目规范"预测先登记"，内容如下：
  - 任何用于对照或交给实验的候选，在跑精算或做实验之前，先在 worklog 里登记以下信息：候选名单（或其文件路径与哈希）、代理模型或生成模型的版本、预测值与置信度、判定标准。
  - 登记之后不得再修改。
  - 事后对模型、提示词或候选空间做的任何调整，都要另起一条新记录，不能覆盖原记录。

## 2026-10-19 ⑥ 锚点规则第一版

- **确认的范围**：组装代码为 ToBaCCo 系（更正：当时并没有现成的组装代码，这是我的误判；后来在 ⑦ 中选定 PORMAKE）；锚点类型先覆盖羧酸、唑类（吡唑/咪唑/1,2,4-三唑/1,2,3-三唑/四唑）和吡啶，规则表结构化，便于后续扩展。
- **产出**：`anchor_rules/`，包括：
  - `anchor_rules.py`：规则表、识别、X 放置、导出。
  - `anchor_cli.py`：命令行。
  - `validate_core2024.py`：验证脚本。
  - README、`锚点规则验证报告.md`，以及 12 个示例配体的 ToBaCCo CIF。
- **设计要点**：
  - SMARTS 识别配位基团，按优先级认领原子。
  - 唑类规则不依赖芳香性，以兼容 MOFid 的写法。
  - 羧酸默认"羧基 C 归节点"，X 放在原羧基 C 的位置；N 给体沿孤对方向、距 N 2.0 Å 放 X。
  - 可以指定目标节点族：节点不接受的基团记为孔道基团。例如 MOF-303 的 PZDC 在 Al 棒节点下只有羧基配位，吡唑 NH 朝向孔道。
  - 导出格式：ToBaCCo CIF（X 加键表）、He xyz、[Lr] SMILES、JSON。
- **验证（CoRE MOF 2024，9,835 个结构，1,911 个唯一有机组分）**：
  - 覆盖率：按唯一配体 83.5%；按出现次数加权 87.4%；84.8% 的结构所有配体都能识别。
  - 未覆盖部分：主要是小配体/端基（472 次）、膦酸（233 次）、脂肪胺柱撑配体（146 次）、N-氧化物（98 次）、儿茶酚（73 次）。
  - 与 Nexerra 式纯几何规则对比（475 个纯羧酸配体）：化学等价一致率只有 41.9%（k = 2 时 48.1%，k = 4 时 23.0%）。错误是系统性的，例如间苯二甲酸被选成对苯二甲酸（123 次）、5-取代间苯二甲酸被选成 2-取代对苯二甲酸、1,4-萘二甲酸被选成 2,6-萘二甲酸。即几何规则会把弯曲配体推向直线型。这给启动文档"锚点必须自己写"的判断提供了定量依据。
- **遗留**：
  - ~~需要一个组内实际使用的 ToBaCCo 边构筑块 CIF~~（已作废：组装器改用 PORMAKE，见 ⑦）。
  - 第二版加入膦酸、儿茶酚、N-氧化物、脂肪胺柱撑配体。
  - 接上组装代码后测"生成配体 → 组装成功率"。

## 2026-10-19 ⑦ 接入 PORMAKE 作为组装器，测组装成功率

- **决定**：项目里还没有组装代码。第一阶段组装器用 PORMAKE（pip 安装 pormake 0.2.3，自带 2404 个拓扑和节点构筑块）。
- **锚点导出改动**：
  - 新增 `to_pormake_xyz`，默认 `x_convention="pormake"`：X 放在被切断键的中点，组装时两侧 X 重合。
  - 用 BDC + pcu + N16 建出 IRMOF-1（晶胞 12.96 Å），以此验证约定无误。
  - 常用节点构筑块：Zn4O = N16，Cu 桨轮 = N17，Zr6 = N419。PORMAKE 库里没有 sql。
- **测试**：`anchor_rules/assembly_test.py`，报告 `组装测试报告.md`。
  - 配体：CoRE 纯羧酸配体，二齿 149 个、三齿 80 个。化学锚点与 Nexerra 式几何锚点在同一批配体上配对比较。
  - 拓扑：pcu/fcu/nbo（二齿配体作边）和 tbo（三齿配体作节点）。
  - 判据：连接方向偏差 ≤ 20°、Locator RMSD ≤ 0.3、无碰撞、键长合理。
- **结果**：
  - PORMAKE 构建 100% "成功"，所以必须加几何判据。
  - 化学锚点成功率 20–30%。失败主因是配体弯曲或柔性导致与线性边拓扑不匹配；方向合格的配体放进 pcu，成功率 92%。
  - 几何锚点表观成功率更高（pcu 50%），但成功的里面约一半化学上是错的（把间位改成对位，硬适配线性边）。
  - 按"成功且化学正确"计：pcu 30.2 对 26.8，fcu 20.8 对 22.8，nbo 26.8 对 25.5，tbo 20.0 对 16.2（前者为化学锚点，单位 %）。
- **结论**：组装流程定为"锚点 → 形状（方向偏差）分类 → 拓扑分发 → PORMAKE → 几何判据"。几何判据不合格的结构不计入命中率分母中的有效候选。
- **下一步**：
  - 柔性配体做多构象，挑方向偏差最小的构象。
  - 补弯曲配体用的拓扑（kgm 等）。
  - 组装后做快速弛豫。
  - 唑类、吡啶配体对应的节点构筑块。

## 2026-10-19 ⑧ 接入 mof303 的 HOOMD patchy 自组装：锚点 → patchy 输入转换器

- **定位（已确认）**：不进筛选主路径。用于 GCMC 之后的头部候选，检查"能否自组装成目标拓扑"，只作定性旁证，不进打分。全原子的组装后弛豫改用 LAMMPS+UFF 或 MACE，不用 HOOMD。
- **产出**：`cg_assembly/`，在 `mof303/cg_patchy3.py` 基础上泛化。
  - 配体几何由锚点规则自动粗粒化：环体系对应 R bead，X 对应 C bead，键长和角度取自 3D 构象。
  - 节点模板：rod、paddlewheel、octahedral。
  - σ 用 PZDC 校准为 1.58 Å。
  - HOOMD 调用写法与 cg_patchy3 相同。
  - 当前只出输入，由用户在服务器 hoomd5 环境上跑（`bash run_all.sh`）。
- **复查 mof303 结果时的发现**：`patchy3_fix_v3.gsd` 末帧确实是每个金属配 4.00 个 C，但 144 个 E 位点里有 46 个空、36 个同时吸住 2–4 个 C。原因是 E–C 吸引截断 1.5σ 太长，一个位点能装多个 C。所以"配位饱和 = 4"实际上是多占，并不是 4 个位点各配 1 个。用我的分析脚本统计：链 6 条、C 全部配位、网络 1 个连通分量，与 `analyze_patchy3.py` 的结果一致。
  - 新增 single 位点模式：E–C 截断 0.8σ，C–C 体积排除 σ = 1.45，强制单占。legacy 模式只用于复现。
  - 这一点可能影响 MOF-303 专利计算章节里关于配位的表述。mof303 文件夹未做任何修改。
- **验证**：
  - 分析脚本在理想网格上的单元测试通过：sql 得到 4 元环 35 个加周期环 2 个；pcu 全是 4 元环；kgm 只有 3 元环和 6 元环。
  - 21 个输入自检通过：键长和角度与设定一致，C–C 初始间距满足单占模式要求。
  - 云端无法安装 hoomd（conda-forge、GitHub 都被拦截），HOOMD 本身没有试跑。`run_all.sh` 会先做冒烟测试。

### 预测登记（运行前写入，之后不得修改）

- **候选与参数**：`cg_assembly/cases/cases.csv`，sha256 `68253b4ae682dade9161600dfbb9360023bd5a15e9de9fe033292543c269e106`。6 个用例 × 3 个种子，200k 步，退火 kT 3.0 → 0.4。A-A 吸引 8、E-C 吸引 20（cg_patchy3 v3 参数）。
- **判定指标**：取末 10 帧平均、3 个种子平均。

| 编号 | 用例 | 预测 | 置信度 |
|---|---|---|---|
| P1 | C0（legacy 复现） | 每节点 C ≥ 3.9，最大连通 ≥ 0.9，E 位点占用率 ≤ 0.8 | 高。注意这只是复现检查，不算预测：多占现象我已经在 fix_v3 上看到了 |
| P2 | C0b（patchy3 几何 + 单占） | E 位点占用率 ≥ 0.9，最大连通 ≥ 0.5 | 约 50% |
| P3 | C2 BDC + 桨轮 | 4 元环比例 frac4 ≥ 0.4，且 3 元环比例 frac3 ≤ 0.15（对应 sql） | 约 55% |
| P4 | C3 mBDC + 桨轮 | frac3 比 C2 高至少 0.2（对应 kgm 或 MOP 笼） | 约 55% |
| P5 | C4 BDC + Zn4O | frac4 ≥ 0.4，且 frac3 ≤ 0.1（对应 pcu） | 约 45%，6 连接体系更容易动力学陷阱 |
| — | C5 BTC + 桨轮 | 探索性用例，不登记定量预测 | — |

- **判定规则**：P3 和 P4 都不成立，说明模型分不出线性配体和弯曲配体，这个模块就不接入工作流。

## 2026-10-20 ⑨ Widom 全量计算上服务器

- **做了什么**：把 `widom_sih4/runs.tar.gz`（691 个 MOF × np/pol，共 1,380 个任务）和 `launch.sh` / `parse_widom.py` / `analyze_henry.py` 上传到 g0048 的 `/share/rickyswork/ai_mof/widom_sih4`，解压核对 692 个条目（691 MOF + jobs.csv）。
- **冒烟测试**：ABUWOJ 改成 200 cycles 跑 np + pol。np 8.5 s、pol 57 s；两组都写出 `Simulation finished`，8 个分子的 Henry 系数齐全；K_N2 = 8.24e-6，与之前 ABUWOJ 验证值 8.1e-6 一致（cycle 数不同，属正常）。
- **启动**：2026-10-20 14:03:59 CST，`nohup bash launch.sh runs 64 14400`，64 并行，单任务超时 4 h。日志 `launch.out`，结果在 `runs/<MOF>/<group>/Output/System_0/*.data`，超时任务留 `TIMEOUT` 标记。
- **并行度**：服务器 255 核；启动时负载约 70（另有用户在用），取 64 并行留余量。按 270 核时估计约 4–5 h。
- **遗留**：跑完后先 `python3 parse_widom.py runs --out results`，把 `henry_wide.csv` 拉回本地，再跑 `analyze_henry.py`（需 lightgbm）。

## 2026-10-21 ⑩ Widom 计算完成，SiH4 痕量选择性 R² 摸底

- **完成情况**：2026-10-20 20:28:06 CST 结束，总耗时 6 h 24 min（约 410 核时），1,380/1,380 个任务全部完成，`TIMEOUT` 为 0。比 269 核时的估算高约 50%，与 `cost_estimate.txt` 里 Ewald 随体积超线性的提示一致。
- **解析**：`parse_widom.py` 得 690/690 个 MOF 的 np 和 pol 状态均为 ok。相对误差中位数：SiH4 3.7%，H2 1.1%，N2 2.1%，O2 1.5%，Ar 1.8%，CH4 2.5%，CO 2.1%，CO2 6.1%；误差 < 50% 的比例 96.4–99.9%。数据质量足够。
- **物理结果**（S_i = K_杂质 / K_SiH4，log10 中位数）：
  - H2 −2.57，N2 −1.55，O2 −1.53，Ar −1.47，CO −1.43，CH4 −0.93，CO2 −0.12（IQR −0.39 到 +0.47）。
  - 也就是说，绝大多数材料优先吸附 SiH4 而不是杂质；只有 CO2 与 SiH4 吸附强度相当，且约一半材料对 CO2 的 S 为正。对 SiH4 纯化而言，这本身就是一条有效的筛除判据。
  - 最难分杂质：CO2 在 541/683 个 MOF 中是瓶颈，CH4 99 个，H2 26 个，其余很少。
- **R² 摸底**（LightGBM，5 折 × 5 次；G → G+RAC+Chem）：
  - K_SiH4：R² 0.89 → 0.92；S_H2/N2/O2/Ar/CH4/CO：R² 0.89–0.91 → 0.92；S_CO2：0.85 → 0.88（ρ 0.65 → 0.80）；S_bottleneck：0.74 → 0.78（ρ 0.46 → 0.55）。
  - EF10：大多数 S_i 为 8.4–8.9，S_CO2 7.5，S_bottleneck 5.9。
  - 与上一轮 CO2/N2 摸底（R² 0.42–0.70）相比大幅提高，支持"限制因素主要是低压标签噪声，不是特征"的判断。
- **一致性检查**：Widom vs CRAFTED 等温线 DSL 外推：K_CO2 ρ = 0.978、中位偏差 −0.033；K_N2 ρ = 0.907、−0.006；选择性比 ρ = 0.911、−0.025。排序高度一致、无系统平移；但 Pearson r² 只有 0.23–0.34，说明外推标签的散布大，进一步印证痕量标签必须用 Widom。
- **解读上的保留**：
  - S_i 以 K_SiH4 为分母，而几何特征对 K_SiH4 的 R² 本身就有 0.89，所以 S_i 的高 R² 有一部分来自"整体吸附容量/孔隙度"，不一定全是选择性化学。CO2（四极矩）是化学特征真正起作用的那一档。
  - 仍在 CRAFTED/CoRE 分布内（Zn 为主），生成结构上的分布外表现必须单独验证。
  - SiH4 单位点力场未校验，绝对 S 值不能用于工艺判断；整体平移不影响排序和 R²。
- **代码修正**：`analyze_henry.py` 中所有 S_i 均为 NA 的行会让新版 pandas 的 `idxmin` 报错，已改为逐行判断。
- **产出**：`widom_sih4/results/` 下 `henry_long.csv`、`henry_wide.csv`、`henry_targets.csv`、`henry_r2_results.csv`、`consistency.txt`；服务器 `runs/` 保留完整输出（4.6 GB）。
- **下一步**：把结果写成正式报告；用生成结构验证代理模型的分布外富集能力；确认 SiH4 力场是否需要多位点对照。

## 2026-10-21 ⑪ 组装结构 OOD 试点：代理模型在适用域外失效

- **产出**：`widom_sih4/结果报告.md`（含第 11 节 OOD 试点）；`anchor_rules/export_ood_set.py` 导出 132 个「化学锚点 + 几何合格」PORMAKE 结构；`widom_sih4/zeo_features.py`；`ood_assembly_eval.py`。
- **工具链**：在服务器编译 Zeo++（`mharanczyk/zeoplusplus` 镜像）。用 ABUWOJ 反校准出 CRAFTED 的口径：`-ha -res`；`-sa/-vol` 1.4 Å 探针、20000 采样。重算 690 个 CRAFTED 结构，D_is/D_fs/D_isfs/ASA/体积/密度等与 CRAFTED 原 CSV 完全一致，AV 只有约 1.5% 版本差异。**以后新结构的 G 特征都应用这套重算口径。**
- **OOD 试点**：41 个组装结构（pcu 14、nbo 12、fcu 10、tbo 5），Widom np 组（SiH₄/H₂/Ar/CH₄，5000 cycles）41/41 完成，0 超时，K 相对误差中位数 0.5–1.6%。
- **结果**（CRAFTED 上训练 G 特征 LightGBM，直接预测组装结构）：

  | 目标 | R² | ρ | EF10 |
  |---|---|---|---|
  | K_SiH4 | 0.31 | 0.60 | 5.0 |
  | S_H2 | 0.29 | 0.37 | 0.0 |
  | S_Ar | 0.25 | 0.38 | 0.0 |
  | S_CH4 | 0.34 | 0.42 | 0.0 |

- **诊断**：组装结构严重偏离 CRAFTED 的几何分布。中位 D_is 12.2 Å（CRAFTED 5.53），D_fs 9.31（3.98），晶胞体积 10,200 Å³（2,290），密度 0.54（1.22），AV 体积分数 0.502（0.074）。41 个里只有 2 个在全部 14 个 G 特征上落在 CRAFTED 的 5–95% 区间。**这是外推失败，不是标签噪声。**
- **结论**：当前代理模型只在 CRAFTED 类似的孔径/密度范围内有效，不能直接给组装/生成候选当 reward。三条出路：① 用 D_is/密度/AV 分数约束生成与组装；② 用组装/生成结构的 Widom 标签扩充训练集；③ 用集成方差或 k-NN 距离做适用域过滤，分布外候选直接送 GCMC。
- **力场对照决定**：文献有 Sakiyama 等（2002）的刚性 SiH₄ 多位点势（MP2/aug-cc-pVTZ，复现黏度），但没有吸附参数化，也没有可对照的实验 Henry 数据。多位点只能做排序敏感性检验，优先级低于 OOD 与适用域问题。
- **遗留**：
  - 在正式生成候选上重复 OOD 试点；当前 41 个是 PORMAKE 组装结构，不是生成配体。
  - 只测了 np 组；CO₂ 需要电荷方案（EQeq/PACMOF/DDEC）才能进入 pol 组。
  - 组装结构未弛豫，孔径偏大；弛豫后可能靠近 CRAFTED 分布，需复测。
  - 是否把 41 个 OOD 标签并入训练集，等候选分布确定后再定。

### 补充（同日）：弛豫试验与适用域门槛

- **弛豫试验**：用服务器 miniconda 的 MACE-MP medium（GPU，float64，可变晶胞，BFGS 40 步）弛豫 4 个代表结构。体积变化 +0.02% 到 +0.6%，D_is 变化 <2%（O0073_pcu 36.10→35.87，O0040_nbo 11.98→11.74）。**大孔是组装几何固有的，弛豫不能把结构带回适用域。**
- **适用域门槛**：`applicability_domain.py` 已写好，用 CRAFTED 的 9 个几何量分位数定义域。41 个组装结构中，1–99% 域内 7 个，5–95% 域内 2 个。输出 `results/domain/bounds.json`、`domain_scores.csv` 和 proxy/gcmc 建议动作。
- **服务器环境记录**：MACE 在 `/home/ruiqi/miniconda3/bin/python`（torch 2.9.1+cu128，MACE 可用）；模型文件 `/share/rickyswork/ai_mof/mace_medium.model`（本地下载后上传，GitHub release 在服务器上超时）。系统 python 的 ASE 3.29 已无 UFF 计算器，不要再用 ASE UFF 做弛豫。
- **扩训实验（已完成）**：41 个试点做扩训、91 个做留出。CRAFTED-only 在留出集上平均 R² 0.016、ρ 0.405、EF10 1.11；加入 41 个组装标签（权重 5）后 R² 0.780、ρ 0.894、EF10 6.67。逐目标 ρ：K_SiH4 0.48→0.73，S_H2 0.40→0.96，S_Ar 0.36→0.95，S_CH4 0.38→0.94。**OOD 失败的主因是训练集没覆盖组装分布，不是特征或弛豫。**
- **学习曲线**：132 个组装结构池，N 个标签加入训练、剩余测试，5 次随机划分。N=10 时 ρ 0.77 ± 0.15；N=20 时 0.85 ± 0.13；N=41 时 0.86 ± 0.14；N=110 时 0.93 ± 0.07。建议每个候选家族先算 40–60 个 Widom 标签；N<20 方差大。
- **产出**：`results/ood_augment/`（metrics、preds）、`results/ood_learning_curve/`（runs、summary）、`ood_augment_eval.py`、`ood_learning_curve.py`、`applicability_domain.py`。
- **下一步**：给新结构分配电荷以覆盖 CO2/pol 组；在正式生成候选（Nexerra/BBA/种子邻域）上重复「抽 40–60 个算标签 → 扩训 → 打分」的闭环。

## 2026-10-21 ⑫ PACMOF 电荷与 pol 组 Widom

- **PACMOF 部署**：从 `snurr-group/pacmof` 源码（本地 clone 后上传，服务器 GitHub 连接不稳）。串行接口不依赖 dask；在服务器 python3 上按原参数训练 DDEC 随机森林模型（500 棵树，测试 R² 0.9955，模型 319 MB），写入 `pacmof/data/Model_RF_DDEC.pkl`。
- **校准**：用 ABUWOJ 跑 PACMOF，输出 CIF 的 `_atom_site_charge` 与 CRAFTED 的 `CIF_FILES/PACMOF/ABUWOJ.cif` 几乎一致（Zn1 1.02388 vs 1.02376，Zn2 0.97777 vs 0.97944），确认电荷口径可用。
- **OOD 电荷**：为 132 个组装结构（41 试点 + 91 留出）生成 PACMOF 电荷 CIF，输出在 `ood_assembly/pacmof_cif/<mof>_charged.cif`，132/132 成功。
- **pol 输入**：
  - CRAFTED：`widom_pacmof/runs/<mof>/pol/`。复用原 `runs/<mof>/pol` 的 simulation.input/ff/molecules，把 CIF 换成 `crafted_pacmof/<mof>.cif`（690 个，全部匹配）。
  - OOD：`ood_assembly/ood_pol_runs/<mof>/pol/`。UnitCells 沿用 np 运行，CIF 换成 PACMOF 电荷版，Ewald + `UseChargesFromCIFFile yes`，132 个。
- **冒烟测试**：ABUWOJ 和 O0073_pcu 各 200 cycles，两批都正常写出 Henry 系数和 `Simulation finished`。
- **启动**：
  - CRAFTED：2026-10-21 15:47:52 CST，`launch.sh widom_pacmof/runs 56 14400`，690 个 pol 任务，56 并行。
  - OOD：2026-10-21 15:51:01 CST，`launch.sh ood_pol_runs 16 14400`，132 个 pol 任务，16 并行。
  - 当前 72 个 `simulate` 同时运行，服务器负载约 231/255。预计 CRAFTED 6–8 h、OOD 2–3 h。
- **下一步**：两批完成后分别 `parse_widom.py`，与 np 标签合并，训练含 CO2/N2/O2/CO 的代理模型，并在 41/91 分割上重复扩训实验。

## 2026-10-21 ⑬ 生产层 MVP：种子邻域 → 组装 → CIF → 代理打分

- **做了什么**：新建 `generation/`，把「配体变体 → 锚点 → PORMAKE 组装 → 候选 CIF → 代理打分」跑通。
  - `enumerate_variants.py`：10 个羧酸种子，在芳香 C–H 上枚举单取代（F/Cl/Br/Me/OH/NH₂/OMe/CF₃/CN/NO₂），保留连接数和锚点类型，重原子 ≤60，去重 → **239 个变体**。
  - `build_candidates.py`：二齿 × pcu/fcu/nbo，三齿 × tbo，套用现有几何判据 → **613 次尝试，268 个合格 CIF**（pcu 118、nbo 93、fcu 47、tbo 10）。
  - `score_candidates.py`：CRAFTED 690 + 132 个组装标签（权重 5）训练 np 代理，在**扩训后的适用域**上给新批次打分。
- **结果**：
  - 适用域：**210 / 268 走代理，58 / 268 判为域外直接送 GCMC**。域外主要来自 BPDC（36 个）和 nbo（34 个）的大孔结构；BDC、DOBDC、NH₂-BDC、DM-BDC 的变体全部在域内。
  - np 预测：域内候选的 S_CH4 中位数 −0.46，最好 −0.36；**没有任何候选对 H₂/Ar/CH₄ 出现正选择性**，仍然是优先吸 SiH₄。排名靠前的是 2,6-NDC/BPDC 的 nbo/pcu 大孔结构，但对纯化方向不利。
  - 说明：规则式单取代枚举本身不足以造出 np 选择性材料；下一批要往孔口化学/口袋特征走（取代基组合、唑/吡啶锚点、更接近 CRAFTED 孔径），并等 CO₂ 的 pol 模型。
- **产出**：`generation/`（README、seeds.smi、variants.csv、build_candidates.py、out/cif 268 个、out/candidates.csv、scored.csv、score_candidates.py）；服务器 `generation/gen_zeo.csv`。
- **下一步**：
  - pol 两批完成后，用同一套流程给 268 个候选补 CO₂/N₂/O₂/CO 打分；
  - 抽 40–60 个新批次候选跑 Widom，验证「新批次 → 扩训 → 打分」闭环；
  - 把生成器换成 Nexerra/BBA 时，只需替换 `variants.csv` 的来源；
  - 下一批考虑多取代、唑/吡啶配体和更小的种子，避免全是 BPDC/NDC 大孔结构。

### 补充（同日）：Novelty 标注

- **问题**：用户一眼认出这批 CIF 里的 MOF-5、UiO-66、HKUST-1、IRMOF-8/10 等结构，怀疑不是“生成”的。
- **核查**：`annotate_novelty.py` 分层结果：268 个候选中 **17 个 known_control**（未取代种子搭出的教科书结构），**251 个 substituted_variant**（已知骨架 + 取代基）。配体层面，251 个取代变体的配体都不在 CoRE 的 1,738 个唯一配体里；唯一匹配的 BDC 属于 known_control。
- **结论**：这批是「已知骨架 × 新取代配体」，不是「全新骨架家族」。骨架眼熟是固定节点/拓扑 + 教科书种子的预期结果，也是可合成性的来源；但不能把它当作生成新颖度的证据。
- **动作**：`known_control` 单独统计，不计入生成命中率；框架级 novelty 需要 MOFid 对 CoRE/BW-DB 比对；下一批生成换掉 BDC/NDC/BPDC/BTC 这些教科书种子，或直接接 Nexerra/BBA。
- **产出**：`generation/annotate_novelty.py`、`generation/annotated.csv`。

## 2026-10-22 ⑭ PACMOF pol 完成与 CO₂ 扩训：CO₂ 是硬骨头

- **完成情况**：CRAFTED pol 690/690（2026-10-22 00:22:48 结束），OOD pol 132/132（2026-10-21 19:26:56 结束），两批 0 超时。
- **数据质量**（K 相对误差中位数）：CRAFTED N₂ 2.1%、O₂ 1.6%、CO 2.0%、CO₂ 5.4%；OOD N₂ 1.0%、O₂ 0.9%、CO 1.2%、CO₂ 6.2%；误差 <50% 的比例 97.5–100%。
- **合并与扩训**：`merge_np_pol.py` 把 np（电荷无关）和 PACMOF pol 合并；41 个试点扩训、91 个留出。
  - 4 个 pol 目标 + K_SiH4 平均：CRAFTED-only R² −0.454、ρ 0.197、EF10 0.89；+41 标签（w20）R² 0.618、ρ 0.831、EF10 6.44。
  - 逐目标（w20）：K_SiH4 ρ 0.734；S_N2 0.953；S_O2 0.953；S_CO 0.960；**S_CO2 只有 0.558**。
  - S_CO2 的 R² 在 −0.02 到 0.06 之间，EF10 3.33；远弱于其他 pol 气体。
- **CO₂ 学习曲线**（132 个组装结构池）：N=20 ρ 0.519，N=41 ρ 0.552，N=60 ρ 0.577，N=90 ρ 0.634，N=110 ρ 0.740；R² 从 0.15 到 0.36，EF10 从 2.4 到 5.0。**CO₂ 需要 100+ 标签，而且 G-only 特征在 110 个标签时仍未饱和。**
- **结论**：np 组（H₂/Ar/CH₄）和 N₂/O₂/CO 用 40–60 个标签即可修复；CO₂ 不行，瓶颈是几何特征看不见四极矩/静电。下一步必须给 OOD 结构和生成结构补化学/电荷特征（元素分数、PACMOF 电荷统计、金属 one-hot），再重训 CO₂ 模型；仅靠加标签不够。
- **产出**：`results/henry_wide_pacmof.csv`、`results/ood_pilot_henry_pacmof.csv`、`results/ood_holdout_henry_pacmof.csv`、`results/ood_augment_pacmof/`、`results/ood_learning_curve_co2/`。
- **下一步**：实现 PACMOF 版 Chem 特征（CRAFTED/OOD/生成结构同口径）→ 重训 CO₂ → 给 268 个生产候选补 CO₂ 打分。

## 2026-10-22 ⑮ G+Chem 修复 CO₂，生产闭环验证通过

- **Chem 特征**：`chem_features_pacmof.py` 为 CRAFTED（690）、OOD（132）、生产候选（268）统一计算 20 个 PACMOF 化学/电荷特征。与 DDEC 版对比：元素分数/原子数完全一致，电荷统计相关 0.838–0.989。
- **G vs G+Chem**（41→91 OOD）：S_CO2 ρ 0.558→**0.765**，R² −0.02→**0.463**，EF10 3.33→4.44；S_N2/O2/CO 也升到 0.96–0.97；K_SiH4 0.734→0.848。**Chem 特征是 CO₂ 的关键。**
- **生产打分**：用 CRAFTED + 132 个组装标签（w20）训练 G+Chem，给 268 个候选打分。**155/268 预测 log10 S_CO2 > 0（S_CO2 > 1）**；nbo 93/93 全为正，pcu 46/118，fcu 14/47，tbo 2/10。排名靠前的是 NH2-BDC/DOBDC/2,6-NDC 的 nbo 结构（胺/羟基 + Cu 桨轮开放金属位）。
- **真实 Widom 验证**：选 10 个高分 + 3 个低分对照 + 2 个 known control，跑 np+pol。13/15 pol 完成（两个 fcu 对照还在跑）：
  - K_SiH4 R² 0.930、ρ 0.789、MAE 0.072；
  - S_CH4 R² 0.944、ρ 0.900；
  - **S_CO2 R² 0.802、ρ 0.692、MAE 0.091**；
  - S_N2 R² 0.958、ρ 0.676。
  - 预测前 10 的 CO₂ 候选真实 S_CO2 全部为正（0.335–0.706）；底部对照 V0064_fcu 预测 −0.484、真实 −0.348。
- **结论**：生产闭环（生成→锚点→组装→CIF→G+Chem→代理→适用域→Widom 验证）已经跑通。CO₂ 可以用于排序，但不能用于绝对工艺判断。
- **产出**：`results/chem_crafted_pacmof.csv`、`results/chem_ood_pacmof.csv`、`results/chem_gen_pacmof.csv`、`results/ood_chem_eval/`、`generation/scored_full.csv`、`generation/validation.csv`；脚本 `chem_features_pacmof.py`、`ood_chem_eval.py`、`score_candidates_full.py`、`validate_predictions.py`。
- **下一步**：两个 fcu 对照已完成（预测与真实均为负）；把 top 候选交给完整 GCMC/实验；下一批换更少见的骨架或接 Nexerra/BBA，重复同一闭环。

## 2026-10-22 ⑯ 完整 SiH4/CO2 混合 GCMC：头部候选全部 CO2 优先

- **条件**：298 K，1 bar，CO₂ 1000 ppm，SiH₄ 平衡；PACMOF 电荷 + UFF + Ewald；30k cycles / 5k init；12 个候选（预测前 10 + 2 known control）。
- **完成**：12/12，0 超时。
- **结果**：所有候选 S_CO2 > 1，范围 2.35–5.15（log 0.371–0.712）。
  - 最好：V0164_nbo（2,6-NDC/nbo）S_CO2 5.15；V0039_nbo（NH₂-BDC/nbo）4.14；V0035_nbo 3.72；V0058_nbo（DM-BDC/nbo）2.79。
  - known control：V0011_nbo 3.00，V0000_nbo 2.67——nbo/Cu 桨轮家族本身就有 CO₂ 选择性。
- **一致性**：
  - GCMC vs Widom Henry：ρ 0.965，R² 0.792，MAE 0.031（log10）——Widom 筛选可靠。
  - GCMC vs 代理预测：ρ 0.692，R² 0.115，MAE 0.065——代理可 triage，不能替代 GCMC。
- **Widom 验证（15/15）**：S_CO2 R² 0.903、ρ 0.789、MAE 0.097；三个 fcu 底部对照预测与真实均为负。
- **结论**：生产闭环完整验证通过；头部候选是真实 CO₂ 优先吸附材料。下一步：把头部候选交给实验；下一批换更少见的骨架/Nexerra 并补多组分 GCMC。
- **产出**：`generation/gcmc_runs/`、`generation/gcmc_results.csv`、`generation/gcmc_vs_proxy.csv`；脚本 `make_gcmc_inputs.py`、`launch_gcmc.sh`、`parse_gcmc.py`、`compare_gcmc.py`。

## 2026-10-22 ⑰ CoRE 2024 框架级 novelty 核查

- **触发**：用户觉得生成的 CIF 眼熟。核查确认：17 个是未取代种子搭出的 known control（MOF-5、UiO-66、HKUST-1、IRMOF-8/10 等），251 个是 substituted variant。
- **方法**：`novelty_core.py` 解析 CoRE 2024 的 9,835 条 MOFid-v1 字符串，拆成「金属元素集合 + 配体 InChIKey 骨架 + 拓扑 + catenation」；生成结构用同样的键比对。8,627/9,835 条可用（1,208 条无 MOFid 标记）；MOFid 拓扑 ERROR/unknown 的用 CoRE topology 列兜底。
- **结果**：
  - 7 exact：全部是 known control（BDC pcu=MOF-5、BDC fcu=UiO-66、DOBDC pcu、2,6-NDC pcu=IRMOF-8、BPDC pcu/fcu=IRMOF-10、BTC tbo=HKUST-1）；
  - 3 topo+ligand（金属类似物）：V0006_pcu、V0038_pcu、V0063_pcu；
  - 4 metal+ligand（不同拓扑）：V0000_nbo、V0010_pcu、V0052_pcu、V0063_fcu；
  - 254 no_match（最终互斥分层；256 是 fallback 拓扑前的旧数）；**CO₂ 头部候选（V0164/V0039/V0035/V0032/V0033/V0058）全部 no_match**。
- **结论**：头部候选不在 CoRE 2024（86% 覆盖），但这不等于已确认全新——CoRE 2024 不是全集，一些 known control 也不在其中。要确认还需 CoRE 2019（服务器 21,830 个 CIF）、BW-DB、CSD 和文献检索。
- **产出**：`generation/novelty_core.py`、`novelty_core.csv`、`scored_full_novelty.csv`；README 已加 Novelty 核查一节。

## 2026-10-23 ⑱ Nexerra 接入：推理跑通，批次质量待调

- **环境**：conda env `envs/nexerra`（Python 3.10，torch 2.5.1+cu124，rdkit 2024.9.6，5.4 GB）；VAE 553.8 MB 通过断点续传下载；用仓库 tokenizer 文件重建最小 `tokenized_dataset_min.pkl`；`pip install -e .` 完成。注意：env 的 pip 动到了系统 Python 的用户包（rdkit 2026.3.6、numpy），已重装 numpy 1.26.4/pandas/sympy 恢复系统脚本。
- **ScafDesign**：100 和 1000 samples 各只产出 5 个 linker；用 `C(=O)([O-])` 替换 `[Lr]` 后都是三齿羧酸，但 **tbo 组装 0/5 通过**——模型生成的臂是柔性二烯链，3-c 几何不匹配。
- **Direct Design**：
  - 二苯并噻吩种子 1000 samples：硬化学过滤后 0 个；
  - BDC 种子 500 samples：原始 dump 500 个 → 转换后 14 个唯一合法二齿羧酸 → 42 次组装 → **9 个合格 CIF**（pcu 4、nbo 3、fcu 2）。
- **关键实现细节**：`[Lr]` 必须替换成 `C(=O)([O-])`（最后一个原子接芳环，羧酸碳接在芳环上）；`C(=O)[O-]` 在杂芳环上触发价键错误，`C(=O)O` 会把芳环接到氧上（甲酸酯）。另外 `Design.py` 的 `--filters` 是 `type=bool`，`--filters False` 会被解析成 True；已修补并加 raw dump。
- **打分/novelty**：9 个候选，7 个域内、2 个域外；3 个预测 log10 S_CO2 > 0（S_CO2 > 1）。最高 N0003_nbo 0.364（配体是 **TDC**，已知）、N0008_nbo 0.307（非芳香、累积双键结构）、N0000_nbo 0.388（域外，gcmc）。CoRE 2024：0 exact、1 topo+ligand（TDC pcu）、1 metal+ligand（TDC fcu）、7 no match。
- **结论**：Nexerra 推理和我们的锚点/组装/打分链路已经接通，但这一批是**集成验证**，不是可用候选池：产率低、原始输出包含化学上可疑的配体、ScafDesign 的柔性臂组装失败。需要加 SAscore/SCScore/化学过滤，换 FlowDesign 或更刚性的种子；top 2 需要 Widom/GCMC 验证。BBA inpainting 仍是备选。
- **产出**：`envs/nexerra`、`generation/nexerra_to_variants.py`、`generation/nexerra_pilot/`、`generation/out_nexerra_bdc/`、`generation/scored_nexerra.csv`、`generation/novelty_nexerra.csv`。

### 补充（同日）：刚性过滤与更大 BDC 批次

- **刚性过滤**已加入 `nexerra_to_variants.py`：要求至少一个芳环；非芳香环只能是 5/6 元且无 sp 原子/累积双键；拒绝 allene/ketene/小环；可旋转键 ≤ 6。变体 ID 加 `--prefix` 避免批次撞名。
- **500 个 BDC 原始 SMILES**：424 个重复、13 个无芳环、57 个小非芳环 → **6 个唯一合法二齿配体**（TDC、苯基-BDC、二烯/苯基等）→ 18 次组装 → **4 个 CIF**（TDC pcu/fcu/nbo + 苯基-BDC pcu）。TDC nbo 是唯一预测 CO2 优先的（S_CO2 0.364），但 TDC 是已知配体。
- **1000 个 BDC 原始 SMILES（delta 0.15）**：855 个重复、135 个无芳环 → **10 个唯一合法二齿配体** → 30 次组装 → **3 个 CIF，全是 BDC**（pcu/fcu/nbo）。已知 MOF-5/UiO-66/Cu-BDC 家族。
- **结论**：BDC 种子太窄，Nexerra 的邻域生成收敛到 BDC/TDC 已知化学；ScafDesign 的柔性二烯臂导致 tbo 0/5。FlowDesign 需要 flow checkpoint（63 MB）+ latent bank（423 MB），Zenodo 当前限速约 15 KB/s，不可行。下一选项是 BBA inpainting，或换非 BDC 的刚性种子、缩小 delta 再试。
- **文件**：`variants_nexerra_bdc_rigid.csv`、`out_nexerra_bdc_rigid/`、`scored_nexerra_rigid.csv`、`variants_nexerra_bdc4_rigid.csv`、`out_nexerra_bdc4_rigid/`。

### 补充：FlowDesign 与 BBA 可行性核查

- **FlowDesign**：需要 flow checkpoint（63 MB）+ latent bank（423 MB）；Zenodo 当前限速约 15 KB/s，latent bank 约需 8 小时，本轮不可行。
- **BBA**：`OAReactDiff` 是**化学反应过渡态扩散**框架，不是预训练 MOF 生成器；Zenodo 15308950 是 BBA 数据集（`mof-1n1e.pkl` 498 MB），没有现成 MOF 权重。BBA 需要自己训练/适配，属于多天级工程，不是即插即用。
- **非 BDC 种子**：二苯并噻吩二甲酸 Direct Design（500 samples，delta 0.05）在跑，采样约 4.5 s/it，预计 ~35 分钟；完成后用刚性过滤 + 组装 + 打分评估。
- **当前结论**：Nexerra 是唯一能直接推理的预训练生成器，但在 BDC/ScafDesign 种子上产出的可用候选很少且偏向已知化学；BBA/FlowDesign 短期不可行。项目主线仍是已跑通的「规则式生成 + G+Chem 代理 + GCMC 验证」。
- **二苯并噻吩批次（已完成）**：500 samples，delta 0.05 → 500 个原始 SMILES → 刚性过滤 **0/500**（全部 `small_nonaromatic_ring`），无合法配体/CIF。模型在这个种子下生成的全是小非芳香环，化学上不可用。
- **Nexerra 最终结论**：推理、转换、过滤、组装、打分链路都通了，但预训练模型在测试过的种子/模式下产出的候选要么是已知化学（BDC/TDC），要么被化学/几何过滤全部拒绝；这不是接入问题，是生成质量与项目约束不匹配。下一步若继续生成端，需要 BBA 自训练或换模型，需单独立项。

## 2026-10-23 ⑲ 阶段性报告

- **产出**：项目根目录 `阶段性报告.md`，汇总 10-16 至 10-23 的全部工作：Widom 标签、代理模型、OOD 扩训、生产闭环、Widom/GCMC 验证、CoRE novelty、Nexerra 接入、能力评估与下一步。
- **报告中的状态判断**：评估/验证链路已经跑通并经完整 GCMC 验证；生成层仍是规则式 MVP 和 Nexerra 集成验证；新颖性未确认、实验验证为零、正式命中密度对照未执行。
- **报告结构**：摘要、目标与边界、工作总览、数据与标签、代理模型、生产闭环、验证、novelty、Nexerra、能力评估、风险、下一步、文件索引、关键数字速查。

## 2026-10-23 ⑳ 生产端可行性对照与前瞻性选择试点

- **产出**：`generation/producer_feasibility.md`。对照了现有规则+反馈搜索、RFcode/SmVAE、MOFDiff、LEGO-MOF、EGMOF；记录代码/资产/接口/工作量/最小试验。
- **核查结论**：
  - 现有规则+反馈搜索：完全本地、无需新资产，推荐为主试点；
  - RFcode/SmVAE：代码在，但无预训练权重、环境旧（Python 3.7/CUDA 10.1），需训练/适配；
  - MOFDiff：代码+预训练在，但资产约 6GB、环境重，且不能生成新构筑块；
  - LEGO-MOF：代码 upon request，当前阻塞；
  - EGMOF：desc2mof 79MB + mof2desc 29MB 可做冒烟；但 `generate(target_value)` 需 prop2desc（3GB），且原生 183 维描述符与 G+Chem/PACMOF 不同；build_cif 依赖 xtb。完整 SiH4 目标引导需计算 183 维描述符并训练 prop2desc（中高工作量）。
- **数据口径修正**：`pred_S_CO2` 是 log10 选择性；novelty 最终互斥分层为 7 exact / 3 topo+ligand / 4 metal+ligand / **254 no_match**（256 是 fallback 前旧数）。README、阶段报告已同步。
- **试点**：`generation/pilot_selection/`，从 268 个候选中排除 15 个已验证和 17 个 known control，选 5 个代理高分 + 5 个随机对照；`registration.md` 已冻结候选（sha256）和判定标准（logS_CO2 ≥ 0.3，即 S_CO2 ≥ 2）；np+pol Widom 正在跑，0 超时。
- **下一步**：解析试点、比较 proxy_top5 与 random5 的命中率；如代理组有富集，再做第二轮反馈批次；若没有，记录负面结果并考虑 EGMOF desc2mof 冒烟。

### 试点结果（已完成）

- np 10/10、pol 10/10，0 超时；Widom 合并后 10 个结构全部 ok。
- **proxy_top5：5/5 命中**（真实 logS_CO2 0.332–0.570，中位 0.466）；**random5：1/5 命中**（V0053_nbo 0.368；其余 pcu/fcu 未达标，中位 0.027）。
- 代理预测 vs 真实 logS_CO2：ρ 0.855、MAE 0.090（n=10）；与之前 15 个候选验证的 ρ 0.789/MAE 0.097 同一量级。
- Fisher 单侧 p≈0.024（5/5 vs 1/5），样本小，只作方向性证据。
- 命中集中于 nbo/Cu 桨轮家族；proxy_top5 全是 nbo，random5 唯一命中也是 nbo。
- **结论**：目标引导的选择在生产池上有富集，支持继续做反馈批次；不做过度解读（n=10、仅 Widom、无容量/GCMC、novelty 未确认）。
- **产出**：`generation/pilot_selection/{selected.csv,registration.md,np_henry.csv,pol_henry.csv,pilot_merged.csv,results.csv,report.md}`。
- **下一步**：用 10 个真实标签更新代理/选择器 → 从剩余池按 UCB/EI 选下一批 5–10 个 → 登记后跑 Widom → 比较初始/反馈/随机的命中率；对命中候选做完整 GCMC 和 novelty 核查。

## 2026-10-26 ㉑ 反馈批次选择与运行

- **模型更新**：用 10 个试点真实 Widom 标签 + CRAFTED + 132 个组装标签，训练 5 个 LightGBM 集成（组装/试点权重 20）；预测剩余 in-domain 候选池。
- **选择**：排除已验证 15 个、试点 10 个、known control；按 UCB = mean + 1.0×std 选前 5：
  - V0006_nbo（mean 0.481，std 0.008，UCB 0.489）、V0048_nbo（0.473/0.015/0.488）、V0047_nbo（0.466/0.015/0.481）、V0067_nbo（0.461/0.011/0.473）、V0024_nbo（0.462/0.007/0.469）。
- **登记**：`generation/pilot_selection/feedback_registration.md`，候选 sha256 `3f58c77a74e7f83989d57fe19a5f8b40a93306da2cb40ea46938c34092049f35`；判定标准同首轮（logS_CO2 ≥ 0.3）。
- **运行**：np+pol Widom 已启动（5 个结构，0 超时）；后台等待+解析任务已挂，完成后比较“初始 proxy_top5 5/5 vs random5 1/5 vs 反馈批次”的命中率。
- **产出（待补）**：`feedback_selected.csv`、`feedback_registration.md`、`feedback_merged.csv`、`feedback_results.csv`。

### 反馈批次结果（已完成）

- np 5/5、pol 5/5，0 超时。
- **反馈批次 5/5 命中**（真实 logS_CO2 0.389–0.478，中位 0.466）；pred_mean vs 真实 ρ 0.600、MAE 0.023（n=5）。
- 三轮对比：初始 proxy_top5 **5/5**（中位 0.466，MAE 0.090）；初始 random5 **1/5**（中位 0.027）；反馈 UCB **5/5**（中位 0.466，MAE 0.023）。
- **结论**：目标引导的选择在两轮都达到 5/5，随机 1/5；代理用于 triage 的方向性结论成立。反馈更新主要改善校准（MAE 0.090→0.023），命中率已在 5/5 上限。样本小、仅 Widom、全为 nbo、novelty 未确认。
- **下一步**：命中候选做完整 GCMC（容量/SiH₄ 损失）+ CoRE/文献 novelty，再决定是否进入合成评估。
- **产出**：`feedback_selected.csv`、`feedback_registration.md`、`feedback_merged.csv`、`feedback_results.csv`、`report.md`（已更新）。

## 2026-10-26 ㉒ 命中候选完整 GCMC

- **候选**：两轮 Widom 的 10 个命中结构（首轮 5 个 + 反馈 5 个，全部 nbo）；CoRE 2024 novelty 全部 **no_match**（无 exact/topo/metal 命中）。
- **登记**：`generation/pilot_selection/gcmc_registration.md`；判定标准冻结为 `GCMC logS_CO2 >= 0.3` 且 `q_SiH4 <= 1.5 mol/kg`，同时记录 q_CO2。
- **运行**：298 K、1 bar、CO₂ 1000 ppm、PACMOF/UFF/Ewald、30k cycles / 5k init；10 个候选已启动，0 超时；后台等待+解析已挂。
- **下一步**：解析 GCMC，比较 Widom/GCMC，按 q_SiH4 约束判定；对通过者做 CoRE 2019/BW-DB/CSD 与合成可及性核查。

### 完整 GCMC 结果（已完成）

- **10/10 通过**：GCMC logS_CO2 0.374–0.592（S_CO2 2.36–3.91）；q_SiH4 0.782–1.159 mol/kg（全部 ≤1.5）；q_CO2 0.0022–0.0044 mol/kg。
- 头部：V0041_nbo（0.592）、V0024_nbo（0.512）、V0023_nbo（0.510）、V0006_nbo（0.502）。
- Widom vs GCMC：ρ 0.758、MAE 0.029（n=10）。
- CoRE 2024 novelty：10/10 no_match；仍需 CoRE 2019/BW-DB/CSD/文献确认。
- **结论**：两轮目标引导选择的 10 个候选在 Widom 和完整 GCMC 下都通过；随机对照 Widom 只有 1/5。支持代理 + 反馈选择作为 triage；样本小、全 nbo、已知骨架、无实验。
- **产出**：`gcmc_results.csv`、`gcmc_hits_results.csv`、`gcmc_registration.md`；`report.md` 已更新终判表。

## 2026-10-26 ㉓ 头部候选 novelty / 可合成性核查

- **数据库结构比对**：
  - CoRE 2024：10/10 候选 no_match；
  - CoRE 2019：21,830 个 CIF，按 Cu/羧酸/元素/体积过滤后 1,049 个，头部 4 个 **0 匹配**；
  - CSD MOF Collection：15,906 个实验 CIF，过滤后 1,627 个 Cu/羧酸结构，头部 4 个 **0 匹配**。
  - 方法：自定义 CIF 解析（忽略 occupancy）+ pymatgen StructureMatcher（ltol 0.3、stol 0.5、angle 10、primitive+supercell）。
- **SAscore**：10 个配体 1.76–2.42，全部低复杂度；V0006 配体为 2-aminoterephthalic acid（已知化合物）。
- **文献初查**：2-ATA 的 Cu 配位网络/Cu-MOF 有报道；未找到“2-ATA + Cu paddlewheel + nbo”的明确先例；甲氧基/氟基氨基对苯二甲酸没有直接 MOF 报道，需更针对性检索。
- **结论**：三个数据库均无结构匹配，是有利的新颖性信号；但 0 匹配不等于全球首创（CSD 客体/部分占据、未查 BW-DB/针对性文献），可合成性未确认（SAscore 只是辅助）。不能对外称“全新 MOF”。
- **下一步**：针对 V0041/V0024/V0023/V0006 的配体做 CSD/PubChem/文献逐条检索；确认配体采购/合成路线及目标框架的合成先例，再做实验评估。

### 合成可及性初查（已完成）

- **V0041**：配体 2-amino-5-methoxyterephthalic acid 有文献水解合成路线（MOF 柔性研究，化合物 5b）；GCMC 最高（logS_CO2 0.592），无数据库结构匹配 → **第一优先合成候选**。
- **V0067**：配体 3-methylthiophene-2,5-dicarboxylic acid 可商购（CAS 89677-40-7）→ 低成本备选。
- **V0006**：2-aminoterephthalic acid 可商购；Cu(BDC-NH2) 桨轮 MOF 有报道（H2S、D2/H2、光催化），但未确认 nbo → 已知化学对照。
- **V0023/V0024/V0047/V0048**：氟基/氰基取代配体无直接采购/文献记录，需定制合成，暂缓。
- **边界**：配体路线/可采购不等于目标 MOF 可结晶；未联系供应商/实验团队，未提交实验。详细见 `generation/pilot_selection/synthesis_assessment.md`。
- **下一步**：经授权后做 V0041 的配体采购/合成确认和小规模结晶筛选（Cu 盐 + 配体，DMF/H2O 或 DMF/EtOH，80–120 °C），再做 PXRD/BET/CO2 吸附。

## 2026-10-28 ㉔ 同预算命中密度对照（纯计算，无实验）

- **背景**：用户明确目前没有实验验证选项，后续只做计算；合成评估仅作桌面参考。
- **协议**：CRAFTED 690 固定种子 2026 抽 100 个 held-out 已知库；生成池为 268 个规则式候选排除已验证/试点/反馈/known control；同一 G+Chem 集成（5×LightGBM；CRAFTED train + 132 组装 + 15 生成标签），两臂各按 UCB 选 5 个；同条件 GCMC。
- **第一次选择被否决**：known held-out 的 UCB 选到 D_fs 2.45–2.72 Å 的极小孔结构，预测 logS_CO2 14.7、K_SiH4 低至 1e-19，属于孔道阻塞造成的假高选择性（RFcode 的教训）。该批未跑 GCMC，已作废。
- **修正**：两臂均加孔径/容量护栏 D_fs ≥ 3.3 Å、AV_Volume_fraction ≥ 0.02；命中标准增加 q_CO2 ≥ 0.001 mol/kg。重选后 known 池 73 个、generated 池 165 个；两臂预测 0.34–0.67。
- **候选**：known_holdout = PASMUT、XEQGEH、XENMOU、CAXWAB、FIPXEJ；generated = V0154_nbo、V0027_nbo、V0158_nbo、V0040_nbo、V0064_nbo。
- **登记**：`generation/pilot_selection/fair_compare_registration.md`，sha256 已冻结；10 个 GCMC 已启动（0 超时待查）。
- **下一步**：解析 GCMC，比较两臂命中率（logS_CO2 ≥ 0.3、q_SiH4 ≤ 1.5、q_CO2 ≥ 0.001），报告同预算命中密度。

### 初步对照结果（9/10 完成）

- **生成臂 5/5 命中**：V0158_nbo（0.555）、V0027_nbo（0.463）、V0064_nbo（0.463）、V0154_nbo（0.438）、V0040_nbo（0.385）；q_SiH4 0.574–1.059，q_CO2 0.0017–0.0031。
- **known held-out 0/5**：PASMUT logS 2.056、q_CO2 0.252，但 q_SiH4 2.212 超 1.5；FIPXEJ logS 1.119 但 q_SiH4 1.716；CAXWAB logS 0.433 但 q_SiH4 2.372；XENMOU −0.039、XEQGEH −0.193 选择性不足。
- **关键**：容量护栏 q_SiH4 ≤1.5 把 known 臂所有高选择性结构排除了；阈值敏感性：≤1.5 → generated 5/5 vs known 0/5；≤2.0 → 5/5 vs 1/5（FIPXEJ）；≤2.5 → 5/5 vs 3/5（PASMUT、FIPXEJ、CAXWAB）。PASMUT 的 q_CO2 0.252 远高于生成臂，容量优先时结论会不同。
- known 臂的代理校准较差（XENMOU/XEQGEH 预测 0.41–0.47，真实 −0.04/−0.19；FIPXEJ 0.34→1.12）；生成臂预测 0.39–0.44，真实 0.39–0.56。可能部分来自训练集含生成标签/132 组装结构，不能单独归因于候选质量。
- 结论：初步方向性证据支持“生成/选择在同预算下优于已知库”，但样本小（5/臂）、PASMUT 未完成、无实验；需等 PASMUT 并考虑阈值敏感性/更大预算。
- **产出**：`fair_compare_report.md`、`fair_gcmc_results.csv`、`fair_compare_results.csv`。

### 扩展批次（10 个/臂，2026-10-29）

- 按同一模型/划分/UCB 排名追加每臂第 6–10 名；新增候选见 `fair_compare_extension_registration.md`。
- **new-5**：generated **4/5**（V0056_nbo logS 0.446 但 q_SiH4 1.741 超 1.5）；known **0/5**（SENWEP logS 2.023 但 q_SiH4 2.834）。
- **combined-10**：generated **9/10**，known **0/10**；中位 logS 0.441 vs 0.373。
- 阈值敏感性（combined）：q_SiH4 ≤1.5 → 9 vs 0；≤2.0 → 10 vs 1；≤2.5 → 10 vs 4。
- 扩展是看到首轮结果后追加的；new-5 与 combined-10 结论一致，避免了只看合并数的误导。
- **产出**：`fair_compare_extension_selected.csv`、`fair_ext_results.csv`、`fair_compare_combined.csv`、`fair_compare_combined.py`；报告已更新。


## 2026-10-29 ㉕ 全池普查：737 个 GCMC（扩大预算，用户要求 ≥500）

- **背景**：用户要求扩大计算规模，不止 20 个同预算样本，至少 500 个 GCMC。
- **设计变更**：不再做 UCB 小样本选择，改为**两臂全池普查**，消除选择偏差；对"设计候选 vs 已知库"的命中率做完整估计。
- **设计臂 218**：268 个合格规则式 CIF 中排除已验证 15、试点 10、反馈 5、known control 17 后，通过护栏者。**包含 53 个此前被 `action=="proxy"` 过滤掉的 `action=="gcmc"` 候选**（此前 UCB 对照遗漏了这批代理评分最高的结构）。
- **已知臂 519**：CRAFTED 690 中通过同一护栏（D_fs ≥ 3.3 Å、AV ≥ 0.02）的全部结构。
- **条件**：298 K、1 bar、CO₂ 1000 ppm + SiH₄ 平衡；PACMOF/UFF/Ewald；30k/5k；与既往完全一致。
- **判定（冻结）**：logS_CO2 ≥ 0.3 且 q_SiH4 ≤ 1.5 且 q_CO2 ≥ 0.001；另报 2.0/2.5 阈值敏感性、Wilson 95% 区间。
- **登记**：`generation/pilot_selection/exhaustive/campaign_registration.md`，sha256 `e1756068...c160`。
- **运行**：2026-10-29 16:46 启动，48 并行，单任务超时 5 h；预计 16–24 h。服务器端 `wait_parse.sh` 在全部结束后自动解析为 `exhaustive/campaign_results.csv`。
- **注意**：两臂样本量不等（218 vs 519），比较的是命中率而非命中数；已知臂包含代理训练集结构（本普查不使用代理筛选，不影响 GCMC 结果，但解释时需注明）。

## 2026-10-29 ㉖ 2027 重复划分完成：generated 10/10 vs known 2/10

- 20 个 GCMC 于 16:53 全部完成、0 超时；`fair2027_results.csv` 已拉回本地。
- **生成臂 10/10**：logS_CO2 0.315–0.476，q_SiH4 0.67–0.93，q_CO2 0.0018–0.0027。
- **已知臂 2/10**：PURQEZ（logS 1.774, q_SiH4 0.158）、PEGBEK01（0.465, 1.444）命中；其余 6 个选择性够但 q_SiH4 1.56–4.22 超限，2 个选择性不足。
- 阈值敏感性（q_SiH4 ≤1.5 / 2.0 / 2.5）：known 2/10 → 3/10 → 5/10；generated 恒为 10/10。
- **两划分合并（各 10 个/臂）**：generated 19/20（0.95，Wilson 0.76–0.99）vs known 2/20（0.10，0.03–0.30）。
- 解读：2026 划分的 known 0/10 是划分特异性，但生成臂优势在 2027 划分仍成立；已知库失败几乎全是容量（q_SiH4）问题，其中位 logS_CO2 反而更高（0.544 vs 0.387）。
- 产出：`fair2027_results.csv`、`fair_compare_2027_results.csv`；`fair_compare_report.md` 已追加该节。

## 2026-10-30 ㉗ 全池普查中期结果（724/737，未完成 13 个大超胞）

- **完成情况**：737 个中 724 个 `ok`；13 个未完成（12 个生成臂 fcu 大超胞 4288–5248 原子 + TATPOV 3456 原子）。其中 11 个触及 5 h 超时，已挂链式脚本，主批量结束后用 12 h 超时重跑，再统一解析。
- **命中率（冻结判定 logS≥0.3、q_SiH4≤1.5、q_CO2≥0.001）**：
  - 生成臂 **63/206 = 30.6%**（Wilson 95%: 24.7–37.2%）
  - 已知库臂 **28/518 = 5.4%**（3.8–7.7%）；Fisher 精确检验 p = 3.8×10⁻¹⁸
- **拆解（关键）**：差距几乎全部来自容量约束，而非选择性。
  - 仅选择性（logS≥0.3）通过率：生成 36.4% vs 已知 29.5%（接近）
  - 仅 SiH₄ 容量（q_SiH4≤1.5）通过率：生成 78.2% vs 已知 14.9%（差距来源）
- **路由**：`gcmc` 路由 31/53 = 58.5%，`proxy` 路由 32/153 = 20.9%——此前 UCB 对照漏掉的 53 个确实是高质量结构。
- **校准**：设计臂 pred_S_CO2 vs GCMC logS_CO2 的 Spearman ρ = 0.675（p≈9×10⁻²⁹）。
- **命中质量（重要局限）**：生成臂命中 logS 中位 0.456、q_CO2 0.002–0.004（无一个 >0.01）；已知库命中 logS 中位 0.864、最高 2.347，12/28 的 q_CO2 >0.01（最高 0.203）。即：**生成臂胜在"低 SiH₄ 摄取下满足门槛"的密度，已知库仍含有绝对性能更强的个体**。若工艺要求有效 CO₂ 容量（如 q_CO2≥0.01），生成臂 0 命中、已知库 12 命中。
- **结论口径**：不能只说"生成臂 30.6% vs 5.4%"；必须同时报告选择性-容量分解，并建议改用 Pareto 前沿而非单一二值门槛来评价。

## 2026-10-30 ㉘ 按 NEXT_STEPS 推进：多组分、SiH4 力场敏感性、novelty 硬核查

- **多组分 / 过程条件**（优先级 2）：15 个候选（二元普查命中里 logS 最高的 10 设计 + 5 已知），4 个条件（298 K/1 bar、273 K/1 bar、323 K/1 bar、298 K/5 bar），4 组分 SiH₄ 0.997 / CO₂ 0.001 / N₂ 0.001 / CH₄ 0.001；共 60 个 GCMC，14:47 启动，20 并行。登记 `multicomponent_registration.md`，sha256 `bc839883...`。
- **SiH4 力场敏感性**（优先级 3）：8 个候选（5 设计 + 3 已知），4 个变体（ε ±20%、σ ±0.1 Å），32 个 GCMC；链式脚本等多组分结束后自动启动。登记 `sih4_sensitivity_registration.md`，sha256 `0cb3e6a5...`。
- **Novelty 硬核查**（优先级 4）：top 5 设计命中（V0186/V0177/V0165/V0146/V0178）做结构级比对——CSD MOF Collection（15,906）、CoRE 2024（20,276 文件）、CoRE 2019（12,020 CIF，服务器），pymatgen StructureMatcher，元素+体积预过滤。进行中。
- **BW-DB**：本地与服务器均未找到数据集，暂无法核查，已在报告中注明。
- 未完成：以上三组结果分析；novelty 的文献逐条检索；选择性–容量 Pareto 分析；普查 12 个大超胞重跑。

## 2026-10-30 ㉙ 验证阶段报告与生成端试点计划

- 产出 `generation/pilot_selection/exhaustive/REPORT.md`：全池普查（725/737）、过程条件矩阵（53/60）、SiH₄ 力场敏感性（25/32）、novelty 覆盖与匹配（CSD 15,906 / CoRE 2024 Cu 1,417 / CoRE 2019 Cu 1,901，均 0 匹配）、设计短名单与未完成清单。
- 关键结果：设计臂 30.6% vs 已知库 5.4%（p=3.8×10⁻¹⁸），差距来自 SiH₄ 容量而非选择性；已知库命中个体更强（12/28 q_CO2>0.01，设计臂 0）；5 bar 下设计臂因 q_SiH4≈4.1 未过门槛，已知低摄取命中 3/3 仍达标（DEBGIA/KUNWEW 待定）。
- 敏感性：ε 主导（±20% → q_SiH4 0.69×/1.44×），排名 ρ 0.83–0.94 稳定；V0146 在 ε+20% 翻转；V0165/V0177/V0178/V0186 稳定。
- 短名单：V0186_nbo、V0177_nbo、V0165_nbo、V0178_nbo；条件性 V0146_nbo。BW-DB 未查。
- 产出 `generation/pilot_generation_plan.md`：MOFDiff / MOFFlow-2 / EGMOF 小规模试点（资产、顺序、门槛、风险）。
- 未完成：12 个大超胞 fcu、7 个多组分、8 个敏感性、BW-DB、其余 58 个设计命中的 novelty。

### 2026-11-02 最终收尾

- 全池普查 **737/737 完成**（12 个大超胞用 12 h 超时重跑后全部完成，0 超时）。最终：设计臂 63/218 = **28.9%**（23.3–35.2），已知库 28/519 = **5.4%**（3.8–7.7），Fisher p = 4.9×10⁻¹⁷；选择性单项 34.9% vs 29.5%，容量单项 73.9% vs 14.8%。
- 多组分 **58/60**（DEBGIA 在 273 K/1 bar 与 5 bar 超时）；设计臂 298/323 K 全中、273 K 8/10、5 bar 0/10；已知臂 298/323 K 全中、273 K 4/4、5 bar 3/4。
- 力场敏感性 **32/32**：ε ±20% → q_SiH4 0.66×/1.46×，ρ 0.93–0.98；翻转候选为 V0146_nbo 与 DEBGIA；V0165/V0177/V0178/V0186 稳定。
- `REPORT.md` 已更新为最终版并追加数据文件清单。

### 2026-11-02 生成端试点启动（EGMOF）

- 验证报告最终版已写入 `exhaustive/REPORT.md`；多组分 2 个 DEBGIA 超时运行已用 8 h 超时重跑。
- EGMOF 仓库已克隆到 `generation/pilots/EGMOF`（README 显示需 Python ≥3.12、uv、torch ≥2.10、pormake、molSimplify、xtb 用于 build_cif）。
- 服务器已安装 uv 0.13.6（用户本地），`uv sync` 正在创建隔离环境（下载 CUDA 轮子中）。未使用系统 pip，避免污染用户包。
- 下一步：下载 prop2desc（3 GB）+ desc2mof/mof2desc（108 MB），跑 10 样本 smoke test；若 xtb 缺失，先记录 build_cif 限制。

## 2026-11-03 EGMOF 试点首轮结果

- 100 样本：89/100 可组装 CIF；87 过护栏、27 域内、3 个域内+护栏+预测≥0.3。
- Widom 15 个（np/pol 全完成）：代理 vs Widom Spearman 0.554；qtz_x（Widom 0.512）、pyr（0.462）通过选择性门槛；fsc_N564 代理 0.52 → Widom −0.167。
- 完整 GCMC 4 个：qtz_x logS 0.711 / q_SiH4 2.40；pyr 0.685 / 1.84；fsc −0.162 / 5.97 —— 域内 3 个均因 q_SiH4>1.5 未过冻结判定，但 qtz_x/pyr 的 (logS, q_CO2) 优于规则式设计池上限（0.636/0.004）。
- 护栏外 tsx：GCMC logS 5.291、q_SiH4 0.003、q_CO2 0.595，原始判定通过但 D_fs 1.74 Å、AV=0，属孔道阻塞/扩散受限可疑案例，需动力学分析，不作为成功证据。
- BW-DB 下载完成（3.99 GB）。

## 2026-11-04 MOFFlow-2 试点首轮结果

- 环境/资产：micromamba 环境（py3.10.12、torch 2.0.1+cu117、PyG、openbabel），HF 镜像下载 8.93 GB；修复 MKL、GLIBCXX、pkg_resources、spglib 依赖。
- 100 条件序列 → 77 个有效结构（77%）；75 过护栏、58 域内（75%）、12 个域内+护栏+预测≥0.3；金属 V 39/Cu 30/Zn 6/Cr 1/Ni 1，V 不在代理训练集。
- Widom 15 个：13/15 logS≥0.3；代理 vs Widom Spearman 0.275（对 V 失效）。
- GCMC 8 个：0/8 通过冻结判定（全部 q_SiH4>1.5）；mofflow2_017 logS 2.819、q_CO2 1.868、q_SiH4 2.83，超过 DEBGIA 的选择性/容量；069 2.424/0.733/2.76。
- 三引擎对比：MOFFlow-2 选择性/容量最高但 SiH4 摄取最高；EGMOF 中间；规则式池低摄取低容量。报告第 9 节已更新。

## 2026-11-05 MOFDiff 基线试点

- 环境复用 MOFFlow-2（torch 2.0.1+cu117）；代码 ghproxy；资产 pretrained 134 MB + bb_emb_space 2.13 GB（解压 17 GB），Zenodo 并行 Range 下载 8 分钟完成；修复 .env/hparams 绝对路径与环境变量。
- 10 样本 smoke：采样 10 → 组装 7 CIF；7/7 护栏、1/7 域内、0 个域内+预测≥0.3；高预测样本均为大孔域外。
- 100 样本无条件采样完成（samples.pt 514 MB），组装进行中；完成后接同一漏斗。
- 三引擎对比已写入 REPORT.md 第 10 节。

### 2026-11-06 MOFDiff 100 样本漏斗

- 100 无条件样本 → 79 CIF（79%）；77 护栏、29 域内（37%）、5 个域内+护栏+预测≥0.3；金属 Zn 57/Cu 18/V 2/Cr 1/Ba 1。
- 头部域内：sample_10（Cu，0.592）、sample_66（Cu，0.589）、sample_28（0.337）、sample_74（0.329）、sample_42（Zn，0.322）。
- Widom 15 个已启动：np 15/15 完成，pol 进行中。过程中发现 MOFDiff 原始 CIF 缺 space group，np 组全部秒退；改用 PACMOF 充电 CIF 后恢复。

### 2026-11-06 MOFDiff Widom 与 GCMC

- Widom 15 个域内候选：11/15 logS≥0.3；头部 sample_78（Cr）4.668、sample_74（Cu）3.329、sample_21（Zn）2.611、sample_10（Cu）2.596。
- 代理 vs Widom Spearman = −0.014，代理对 MOFDiff 结构完全失效（sample_78：pred 0.06 vs Widom 4.67）。
- K_CO2 极大，Henry 外推 1 bar 不成立；已对 6 个候选（含 sample_66 对照）启动 GCMC，15:33、6 并行。

### 2026-11-06 记录补充与更正（不改旧条目，按追加更正）

- **多组分最终为 60/60，不是 58/60**（更正 2026-11-02 条目）：DEBGIA 的 273 K/1 bar 与 5 bar 用 8 h 超时重跑完成，0 超时。最终矩阵：273 K 设计 8/10、已知 5/5；298 K 设计 10/10、已知 5/5；323 K 设计 10/10、已知 5/5；5 bar 设计 0/10、已知 **3/5**（GULPIN/MIKJAR/PURQEZ 过；KUNWEW、DEBGIA 因 q_SiH4 1.90–? 超 1.5 未过）。5 bar 下已知臂此前“3/3”是缺 DEBGIA/KUNWEW 的部分结果，不能再用。
- **EGMOF 环境修复（此前只记录了 uv sync 启动）**：PyPI 直连超时→清华镜像；`prop2desc_ckpt.zip` 内含多模型，下载脚本把 mof2desc 误当 prop2desc→手工选定 `wilmer_CO2_uptake_2.5bar/best.ckpt` + `hparams.yaml`；mof2desc checkpoint 引用旧模块 `easy_adapt_mof`→加兼容 shim；`egmof.py` 未导入 `ZENODO_RECORD`→修补。smoke 10/10 CIF；100 样本 89 CIF。
- **EGMOF 目标口径**：使用的是 CO₂ 2.5 bar 吸附量模型（target_value=5.0，训练均值 4.76），不是 SiH₄/CO₂ 选择性；RF/WMSE 引导未启用，生成样本无 pred_value 过滤。
- **MOFFlow-2 环境细节**：原 `env.yml` 的 `pyg` 通道不可镜像→精简 env + PyG pip 轮子；HF 直连 DNS 被劫持（解析到 31.13.85.169）→hf-mirror.com；GitHub 直连超时→ghproxy；修复 MKL/GLIBCXX（LD_LIBRARY_PATH）/pkg_resources（setuptools<81）/spglib（typing_extensions+networkx+sympy）；`make_ood_inputs.py` 不兼容带前导空格的 CIF 头→strip 解析。100 条件序列 6 s、结构预测 200 s。
- **MOFDiff 环境细节**：Zenodo 单连接约 60 KB/s→16 线程 Range 并行（8 分钟）；`.env` 与 `hparams.yaml` 内作者绝对路径需改写；`EGULP_PATH/RASPA_PATH/DATASET_DIR` 等变量为空但导入必填。MOFDiff 原始 CIF 缺 space group → np Widom 组全部秒退，改用 PACMOF 充电 CIF 后恢复。
- **Pareto 结果**：q_SiH4≤1.5 下 737 个候选中仅 **DEBGIA** 位于 (logS, q_CO2) 前沿；不设容量约束时前沿为 XILDUT（logS 2.498、q_CO2 0.478、q_SiH4 1.517）。设计池上限 0.636/0.004。
- **报告章节对应**：验证与三引擎结果见 `exhaustive/REPORT.md` 第 1–5、8–10 节；生成端计划见 `generation/pilot_generation_plan.md`。
- **仍未记录/未完成**：MOFDiff 6 个候选的 GCMC 结果（运行中）；MOFDiff `optimize.py` 条件生成对照（未开始）。

## 2026-11-09 MOFDiff GCMC 解析与结构可靠性核查（重要：此前 MOFDiff 性能结果作废）

- **补解析 11/06 完成的 6 个 MOFDiff GCMC**（`MOFDiff/pilot100/mofdiff_widom/gcmc_runs`，298 K、1 bar、CO₂ 1000 ppm、30k/5k、PACMOF/UFF/Ewald）。5 个完成、sample_78 在 4 h 超时（到 cycle 25,000/30,000；部分平均 q_SiH4 3.28、q_CO2 2.11，未收敛）。
  | 候选 | 金属 | GCMC logS_CO2 | q_SiH4 (mol/kg) | q_CO2 (mol/kg) | 冻结判定 |
  |---|---|---|---|---|---|
  | sample_10 | Cu | 2.757 | 2.084 | 1.191 | 否（q_SiH4） |
  | sample_74 | Cu | 2.562 | 2.651 | 0.968 | 否（q_SiH4） |
  | sample_21 | Zn | 2.528 | 2.733 | 0.922 | 否（q_SiH4） |
  | sample_94 | Cu | 1.224 | 4.500 | 0.075 | 否（q_SiH4） |
  | sample_66（阴性对照） | Cu | −0.149 | 2.180 | 0.0015 | 否（选择性，符合预期） |
  | sample_78 | Cr | 超时 | — | — | — |
- **结构合理性核查推翻了上述表观结果（关键）**：这 6 个结构是 assemble 后未经弛豫的 CIF。最小原子间距 0.241–1.073 Å（sample_74 O–O 0.241 Å、sample_78 C–C 0.280 Å、sample_94 H–C 0.440 Å、sample_10 O–H 0.558 Å）；sample_66 与 sample_78 各含 2 个不连通片段（分别为 56+20、87+60 原子，游离配体）；sample_78 的 Cr 配位数仅 1、sample_94 的 Cu 仅 2、sample_21 的 Zn–N 1.24 Å。MOFDiff 官方流程要求 assemble 后必须 `uff_relax.py`（LAMMPS/UFF）弛豫、Zeo++/MOFid 有效性过滤、MEPO/QEq 充电；本试点此前直接从 assemble CIF 做 PACMOF + Widom/GCMC，**属流程缺陷**。
- **结论**：K_CO2 0.267–3.314 mol/kg/Pa（误差 ±100%）与 q_CO2≈1 mol/kg 是过近原子/游离片段造成的假强结合位点；§10.4–10.5 的 MOFDiff Widom/GCMC 不能作为性能证据，四引擎对比中 MOFDiff 行作废、待重做。**不要把 sample_10 的 logS 2.76 / q_CO2 1.19 当作发现。**
- **补做 UFF 弛豫**：新建 `/home/ruiqi/venv_mofrelax`（lammps 2023.8.2 + lammps-interface 0.2.2 + pymatgen + python-dotenv），用 standalone 版绕过 mofdiff 包对 pytorch_lightning 的依赖，复现官方 `lammps_relax`（UFF、box/relax、minimize）。代码：服务器 `plausibility/uff/run_all_uff.sh` + `/tmp/uff_relax_standalone.py`；本地已固化到 `generation/mofdiff_plausibility/`（`uff_relax_standalone.py`、`check_mofdiff_plausibility.py`、`plausibility.json`、`gcmc_results.csv`）。
  - 先行 4 个：sample_10 dmin 0.558→0.984 Å、原胞 V 1167.8→1075.6（−7.9%）；sample_21 0.849→0.940、1993.2→2156.9（+8.2%）；sample_66 1.073→0.984、2218.2→2192.8（−1.1%）；sample_74 弛豫后 O–O 0.007 Å（UFF 把原子推穿，结构无效）；sample_94 lammps-interface 报 Dihedral 原子 ID 错误（未弛豫）。
  - **全量 79 个 assembled CIF 的 UFF 弛豫已启动**（`plausibility/uff/run_all_uff.sh`，12 并行、单任务 1 h 上限），完成后需按有效子集（单片段、dmin>0.9 Å、体积合理）重算 Zeo++/PACMOF → 护栏/适用域 → Widom/GCMC，才能得到 MOFDiff 的真实性能。
- **sample_78 的 12 h 重跑已启动**（从头跑，预计 ~5 h）；原 25k checkpoint 在多次启动中被覆盖，无法续算。
- **全量 UFF 弛豫完成（79/79 提交，77 个 LAMMPS 成功）**：按“UFF 成功 + dmin≥0.9 Å + 单连通片段 + 原胞原子数一致 + 体积变化在 0.75–1.25”的有效性标准，**41/79（52%）有效**。V_ratio 中位 0.967（0.822–1.157）。另 38 个即使 UFF 后仍有 <0.9 Å 重叠（dmin 0.21–0.90），2 个 LAMMPS 失败（sample_78 CIF 解析失败、sample_94 lammps-interface Dihedral 错误）。
  - 有效子集的金属只剩 Cu 与 Zn（V/Cr/Ba 结构全部未通过），与之前“金属分布 Zn 57/Cu 18/V 2/Cr 1/Ba 1”对照，说明 V/Cr/Ba 的组装结构在本流程下不可用。
  - sample_10 弛豫后孔隙塌缩：D_fs 3.33→1.82 Å、AV 0.034→0.000；代理预测 13.54（典型孔道阻塞假高值），护栏不通过。
- **弛豫后重跑漏斗（41 个有效结构，Zeo++ 41/41、PACMOF 72 个 CIF 全部成功、代理同口径）**：护栏 38/41、域内 20/41、护栏+域内+pred≥0.3 **仅 1 个（sample_66，pred 0.305）**，而弛豫前是 5 个。sample_21 pred 0.251→−0.018，sample_42 0.322→−0.012，sample_10 0.592→13.54（但护栏失败）。即 **MOFDiff 的“可用候选数”在正确弛豫后从 5 降到 1**。
- **弛豫后 Widom 重评已启动**：12 个候选（sample_66/30/99/41/52/20/36/64/29/73/21/42）的 np+pol 共 24 个任务，12 并行、8 h 上限（`plausibility/uff/widom/`）。完成后解析 henry、对头部跑 GCMC，再更新四引擎对比。
- 产出（服务器）：`plausibility/uff/uff_summary.csv`、`valid_list.csv`、`prim/`、`pacmof_valid/`、`zeo_valid.csv`、`chem_valid.csv`；本地镜像：`generation/mofdiff100_uff_{summary,zeo,chem,scores}.csv`。
- **sample_78 的未弛豫 12 h GCMC 重跑已取消**（已到 cycle 2000/30000）：该结构 UFF 弛豫后 CIF 无法解析（无结构），未弛豫 GCMC 已无证据价值；目录留 `CANCELED` 说明。

### 2026-11-10 弛豫后 Widom 结果（12 个候选，24/24 完成，0 超时）

- 12 个候选的 np+pol Widom 于 17:45 全部完成。logS_CO2 = log10(K_CO2/K_SiH4)：
  | 候选 | 代理 pred | Widom logS | K_SiH4 | K_CO2 | U_CO2 (kJ/mol) |
  |---|---|---|---|---|---|
  | sample_41 | 0.098 | **0.615** | 2.0e-5 | 8.1e-5 | −26.1 |
  | sample_21 | −0.018 | **0.447** | 2.3e-5 | 6.4e-5 | −25.7 |
  | sample_73 | 0.302 | **0.435** | 2.5e-5 | 6.8e-5 | −22.6 |
  | sample_99 | 0.090 | **0.424** | 4.6e-5 | 1.2e-4 | −27.7 |
  | sample_42 | −0.012 | **0.331** | 1.2e-5 | 2.5e-5 | −21.3 |
  | sample_20 | 0.074 | 0.202 | 2.5e-5 | 3.9e-5 | −23.8 |
  | sample_52 | 0.054 | 0.181 | 4.0e-5 | 6.1e-5 | −24.0 |
  | sample_29 | 0.324 | 0.056 | 7e-6 | 8e-6 | −11.9 |
  | sample_30 | 0.224 | −0.009 | 7.3e-5 | 7.2e-5 | −27.6 |
  | sample_64 | 0.368 | −0.026 | 2.8e-5 | 2.6e-5 | −18.0 |
  | sample_36 | 0.419 | −0.098 | 1.8e-5 | 1.4e-5 | −14.4 |
  | sample_66 | 0.305 | −0.131 | 1.8e-5 | 1.3e-5 | −14.9 |
- **代理 vs Widom Spearman = −0.65（n=12）**：代理对弛豫后 MOFDiff 结构的排序是反相关的。唯一通过完整漏斗的 sample_66（pred 0.305）Widom 为负；代理预测最高的 36/64/29 也全部为负；Widom 最好的 41/21 被代理排在低位。再次确认 CRAFTED 代理在 MOFDiff 结构上失效（不仅是未弛豫时）。
- Widom 吸能合理（U_CO2 −21…−28、U_SiH4 −15…−20 kJ/mol），与未弛豫时 K_CO2≈0.27–3.3 mol/kg/Pa 的假象形成对比。弛豫后的最好 logS 0.615 与规则式设计池上限 0.636 同量级。
- **GCMC 已启动**：5 个 Widom 命中（41/21/73/99/42）+ sample_66 对照，6 并行、8 h 上限（`uff/widom/gcmc_runs/`）；完成后自动解析到 `widom/gcmc_results.csv`。
- 产出：`widom/results/henry_wide.csv`、`widom/widom_vs_proxy_uff.csv`；本地镜像 `generation/mofdiff100_uff_henry.csv`、`generation/mofdiff100_uff_widom_vs_proxy.csv`。

### 2026-11-10 弛豫后 GCMC 结果（6/6 完成，0 超时）

- 6 个候选于 10:12 全部完成（298 K、1 bar、CO₂ 1000 ppm、PACMOF/UFF/Ewald、30k/5k），自动解析到 `widom/gcmc_results.csv`：
  | 候选 | GCMC logS | q_SiH4 | q_CO2 | 冻结判定 | Widom logS | 代理 pred |
  |---|---|---|---|---|---|---|
  | sample_41 | 0.608 | 2.065 | 0.0084 | 否（容量） | 0.615 | 0.098 |
  | sample_99 | 0.585 | 2.523 | 0.0097 | 否（容量） | 0.424 | 0.090 |
  | sample_73 | 0.512 | 2.300 | 0.0075 | 否（容量） | 0.435 | 0.302 |
  | sample_21 | 0.475 | 2.118 | 0.0063 | 否（容量） | 0.447 | −0.018 |
  | **sample_42** | **0.421** | **0.896** | **0.00236** | **通过** | 0.331 | −0.012 |
  | sample_66 | −0.086 | 1.762 | 0.0014 | 否（选择性） | −0.131 | 0.305 |
- **1/6 通过冻结判定：sample_42**（logS 0.421、q_SiH4 0.896≤1.5、q_CO2 0.00236≥0.001）。阈值敏感性：q_SiH4≤1.5 → 1/6；≤2.0 → 1/6；≤2.5 → 4/6；≤3.0 → 5/6。容量仍是分水岭。
- **Widom vs GCMC 在弛豫后高度一致**：Spearman 0.771、Pearson 0.974（未弛豫时是 ρ 0.965 但基于假结构；这次结构已核对）。说明弛豫后的 Widom 可作可靠 triage。
- **关键但微妙的结论**：MOFDiff 弛豫后确实能产出达标候选（sample_42 的 logS 0.421 / q_CO2 0.0024，与规则式设计池命中的中位 0.456 / 0.002–0.004 同量级）；但**代理不能把它选出来**（pred −0.012，排 41 个中的下游），而唯一通过漏斗的 sample_66 被 GCMC 判负。即：引擎有可用输出，目标引导的选择器在 MOFDiff 上失效。
- 不能把 1/6 当作“命中密度”与规则式/已知库比较：这 6 个是按 Widom 选出的，不是按代理/漏斗选出的。公平比较需要对 41 个有效结构做随机抽样或重训代理后再选。
- 产出：`widom/gcmc_results.csv`；本地镜像 `generation/mofdiff100_uff_gcmc.csv`。

### 2026-11-10 全量 41 个有效结构的 Widom 与代理扩训

- 82 个 Widom 任务 15:30 全部完成（0 超时）：41/41 np+pol。
- **无偏 Widom 命中率（logS≥0.3）**：40 个可评估（sample_10 孔道塌缩、K_SiH4≈5e-31，排除）中 **12/40 = 30.0%（Wilson 18.1–45.4%）**；logS≥0.2 为 18/40=45.0%。
- 命中降序：sample_25 0.848、sample_23 0.805、sample_41 0.615、sample_27 0.541、sample_47 0.483、sample_21 0.447、sample_73 0.435、sample_99 0.424、sample_34 0.397、sample_51 0.371、sample_71 0.343、sample_42 0.331。
- **代理 vs Widom 在全部 40 个上 Spearman = +0.078**：之前 12 个上的 −0.65 是小样本噪声；代理对 MOFDiff 结构基本无排序能力。
- **扩训不修复**：生产训练集 + 其余 39 个 MOFDiff 标签（LOO，权重 1/5/20）→ ρ 0.058/0.060/0.015、EF10=0、R² 仍为负。仅在 MOFDiff 内部训练（39→1 LOO）：G-only ρ −0.002；**G+Chem ρ 0.377、EF10 5.0、R² 0.136**；metal one-hot 无增益。Chem 特征有信号，但 40 个标签远不足以修复 CO2 排序；与“CO2 需 100+ 标签”的既往判断一致。
- 实际建议：MOFDiff 的 CO2 triage 直接用 Widom（41 个 25 分钟）比代理更便宜、更可靠；代理扩训需 100+ 标签或更强的孔道/配位描述符。
- **已补跑剩余 7 个 Widom 命中**（23/25/27/34/47/51/71）的 GCMC（`gcmc_runs2`，7 并行、8 h），完成后得到“Widom 选中的 12 个命中”的完整 GCMC 通过率。
- 产出：`widom/results_all/henry_*.csv`（41 个）；本地镜像 `generation/mofdiff100_uff_henry_all.csv`、`generation/mofdiff_aug_eval_41.csv`（扩训指标）、`generation/mofdiff_aug_eval_41_preds.csv`。
- **剩余 7 个命中的 GCMC 中期（6/7，sample_23 仍在跑）**：sample_25 0.815/1.980/0.0130（容量未过）；sample_27 0.511/1.555/0.0050（容量差 0.055 未过）；sample_34 0.370/2.072/0.0049（容量未过）；**sample_47 0.503/0.998/0.0032（通过）**；**sample_51 0.605/1.177/0.0047（通过；注意其护栏 AV=0.0195 略低于 0.02，但冻结判定不含护栏）**；**sample_71 0.426/1.277/0.0034（通过）**。
- 合并前 6 个（41/21/73/99/42/66）：**Widom 命中 12 个中已评 11 个，冻结通过 4 个（42、47、51、71）= 36.4%**。按 40 个可评估有效结构计，粗估有效结构冻结命中率 ≈ 4/40 ≈ 10%（小样本、待 sample_23）。

### 2026-11-11 全部 41 个有效结构 GCMC 完成（最终）

- 剩余 28 个结构并行跑完（`gcmc_runs3`，28 并行，19:25 完成，0 超时）；三批合并 **41/41**。
- **冻结命中 4 个：sample_42、sample_47、sample_51、sample_71；4/41 = 9.8%（Wilson 3.9–22.5%）**。阈值敏感性 q_SiH4 ≤1.5/2.0/2.5/3.0 → 4/7/11/13。
- **Widom triage 有效性**：Widom 命中 12 个中 4 个过 GCMC，未命中 29 个中 0 个（Fisher p = 0.0049）。在代理 ρ≈0 的情况下，Widom 是唯一有效的 MOFDiff 选择器。
- **命中质量**：logS 0.421–0.605、q_SiH4 0.896–1.277、q_CO2 0.0024–0.0047；与规则式设计池命中（中位 logS 0.456、q_CO2 0.002–0.004）同量级。
- **分母口径**：按 UFF 有效结构 4/41 = 9.8%；按 assembled CIF 4/79 = 5.1%；按原始 100 样本 4.0%。对照：规则式设计池 28.9%（218 个护栏内候选）、已知库 5.4%（519）。有效结构命中率介于两者之间，但按原始生成数计接近已知库。
- 高选择性但容量不过：sample_23 logS 1.153、q_CO2 0.0407，但 q_SiH4 2.86；sample_10 确认为非吸附（q_SiH4=q_CO2=0）。
- 产出：`gcmc_results2.csv`、`gcmc_results3.csv`；本地合并 `generation/mofdiff100_uff_gcmc_all41.csv`。

## 2026-11-11 转向结构生成：三引擎统一结构质量筛查

- 用户决定：暂缓 SiH₄/CO₂ 性能评价，专注**结构生成本身**；规则式 + 反馈保留为保底基线（ToBaCCo 式拓扑枚举是成熟路线，不作为创新点）。
- 统一口径对三引擎各 100 样本做结构筛查（precheck 不依赖 UFF；StructureMatcher 去重；UFF 弛豫 + 有效性）：
  | 指标 | MOFDiff | MOFFlow-2 | EGMOF |
  |---|---|---|---|
  | 可组装 CIF | 79/100 | 77/100 | 89/100 |
  | 原始几何干净 | 26/79（32.9%） | 40/77（51.9%） | 36/89（40.4%） |
  | 含断开片段 | 22（27.8%） | 12（15.6%） | 4（4.5%） |
  | <0.9 Å 重叠 | 37 | 37 | 52 |
  | 去重唯一 | 79/79 | 69/77 | 89/89 |
  | UFF 可参数化 | 77/79 | 26/77 | 89/89 |
  | UFF 后有效 | 41/79（51.9%） | 25/77（32.5%）* | 80/89（89.9%） |
  | 唯一化学式 | 79（100%） | 54（70%） | 88（99%） |
  | 金属 | Zn57/Cu18/V2/Cr1/Ba1 | V39/Cu30/Zn6/Ni1/Cr1 | Zn59/Cu16/Cd5/Zr3/Co2 |
- * MOFFlow-2 的 UFF 失败主要是 lammps-interface 工具问题（42 个 `Invalid atom ID in Dihedrals`、8 个交互式 EOF），不是结构无效；需 CIF 规范化/MACE fallback 后才能公平评估。
- 结论：三引擎都有 40–67% 的原始结构缺陷，结构有效性核查/弛豫是生成流程必需环节；EGMOF 可弛豫率最高，MOFFlow-2 原始几何最干净但多样性最低，MOFDiff 无重复但片段缺陷最多。
- 产出：`generation/structure_generation_quality.md`、`generation/structure_quality/`（本地 CSV 镜像）；服务器 `generation/pilots/*/pilot100/plausibility/uff/`、`generation/precheck/`。
- 下一步：工具失败与结构失败分离（坐标规范化 + MACE fallback）；novelty（CoRE/CSD/BW-DB 定位）；构筑块新颖性；扩大样本；条件生成对照。

### 2026-11-11 工具失败分离 + MACE fallback（完成）

- 尝试修复 lammps-interface 的 dihedral bug：CIF 坐标 wrap 重写、给交互提示传入多个确认，均失败（mofflow2_002/008 仍报 `Invalid atom ID in Dihedrals`）。判定为工具 bug，不是坐标问题。
- MACE-MP fallback：对 51 个 MOFFlow-2 工具失败 + 2 个 MOFDiff 工具失败结构做弛豫（150 步、fmax 0.2、每卡 1 个任务、OMP 线程限制为 2；先前 8 并发因线程超卖卡住）。
- **结果**：MOFFlow-2 51 个中 **26 个有效**（体积比 0.948–1.034，dmin≥0.9、单片段）；其余 25 个仍多片段/重叠，属真实缺陷。MOFDiff 2 个仍无效。
- **最终有效率（UFF ∪ MACE）**：MOFDiff **41/79（51.9%）**、MOFFlow-2 **51/77（66.2%）**、EGMOF **80/89（89.9%）**。
- **条件有效性**（UFF 可处理的结构中）：MOFFlow-2 96.2%、EGMOF 89.9%、MOFDiff 53.2%——MOFDiff 的损耗主要来自装配本身，而非弛豫器。
- 排名修正：按最终有效率 **EGMOF > MOFFlow-2 > MOFDiff**；MOFFlow-2 从 32.5% 修正到 66.2%。
- 产出：服务器 `plausibility/uff/combined_summary.csv`、`plausibility/mace/`；本地 `generation/structure_quality/{mofflow2,mofdiff}_combined.csv`；`structure_generation_quality.md` 已更新。
- 下一步：novelty（CoRE/CSD/BW-DB 定位）、构筑块新颖性、扩样本、条件生成对照。

### 2026-11-11 公开 MOF 数据库上传到服务器

- 本地 `C:\Users\PC\Desktop\MOF-公开数据库` 已上传到 `/share/rickyswork/ai_mof/databases/`（约 7.6 GB），单独文件夹，附 `README.md` 清单。
- 内容：CSD_MOF_Collection 15,906 CIF（636 MB）；core2024 20,276 CIF（377 MB）；hmof 20,649 CIF（296 MB）；mosaec-db 309,179 CIF（3.4 GB，base/MEPOML/REPEAT）；CRAFTED-2.0.0 8,142 CIF + 等温线/焓/力场（301k 文件，678 MB）；isodb-library-master 构筑块库（非 CIF，343 MB）；原始 zip 保留在 `zips/`。
- 传输：已有 zip 的用 scp + 服务器端 unzip；无 zip 的用 `tar czf - | ssh 'tar xzf -'` 流式传输。上传速度约 5–6 MB/s。
- 仍缺 BW-DB（MOFDiff 训练集，约 4 GB），novelty/记忆化检查需要时再下载。
- 下一步：用该库对三引擎结构做 StructureMatcher novelty 分层与构筑块新颖性统计。

### 2026-11-11 结构 novelty 与构筑块新颖性（完成）

- 数据库镜像 + 轻量索引：CSD 15,906 / CoRE 2024 20,276 / hMOF 20,649 / MOSAEC 309,179（合计 365,010 CIF）；索引 `databases/index/`（gcd 化学式 + 体积）。
- **精确结构匹配**（同化学式必要预筛 + StructureMatcher）：三引擎 **0 结构重复**。同式候选：MOFDiff 2/2/2/2（CSD/CoRE/hMOF/MOSAEC）、MOFFlow-2 0/3/2/1、EGMOF 0/8/16/13；但都不是同一结构。有效弛豫结构复核仍 0。
- **宽松匹配**（元素集合 + 体积 0.5–2.0 + 每库体积最近 400 个 + StructureMatcher）：CSD/CoRE/hMOF 仍 **0**（有界搜索；MOSAEC 只做精确预筛）。
- **EGMOF BB**：89 个结构用 30 个拓扑、54 个 node BB、65 个唯一组合（9 个重复）；固定库 → BB 级 novelty=0，novelty 只在组合层面。
- **MOFFlow-2 BB**（vs 187,047 训练序列 / 148,102 有机 SBU）：83 个 RDKit 有效唯一有机 SBU，其中 **18 个（21.7%）不在训练集**；**17/100 样本含新 BB**；6 个金属节点 1 个新；79/100 唯一序列、69/100 序列新；**25 个无效 SMILES（23 唯一）**。
- 结论：三引擎在 36.5 万参考结构中均无结构重复；MOFFlow-2 具备真实的新构筑块生成能力（约 22% SBU、17% 样本），但伴随约 5% 化学无效输出；EGMOF 只能重组合固定 BB。
- 限制：BW-DB 缺失（MOFDiff 记忆化未查）；宽松匹配有界（top400）；MOSAEC 未做宽松匹配；“新颖”不等于可合成。
- 产出：`structure_generation_quality.md` §7；本地 `generation/novelty/`（exact/valid/loose/BB）；服务器 `generation/novelty/`、`databases/index/`；脚本 `fast_db_index.py`、`novelty_lookup.py`、`novelty_loose.py`、`mofflow2_bb_novelty.py`。
- 下一步：对新 SBU 逐条化学审查；下载 BW-DB 查 MOFDiff 记忆化；扩样本；条件生成对照。

### 2026-11-11 新 SBU 化学审查（完成）

- 18 个训练集外、RDKit 有效的有机 SBU：**12 个判为可行 MOF 连接体**（11 个 ≥2 羧酸根、1 个双吡唑 N 给体、1 个三羧酸 charge −3 正常）；6 个不可行（2 个卡宾自由基 `[C]`、2 个单羧酸 bind=1、2 个非连接体：偶氮小分子、亚硝酸类 `O[N-]O`）。
- SAscore 中位 3.62（2.59–6.76），可行连接体集中在 2.98–4.00。
- **与训练 SBU 的最近邻 Tanimoto：14/18 ≥0.7，0/18 <0.4** → 所有“新”SBU 都是已知 SBU 的近邻类似物，没有全新骨架。MOFFlow-2 的 BB novelty 是 analog/decoration，不是 scaffold innovation。
- BW-DB 下载已启动（Zenodo record 10806179，3.99 GB，16 线程 Range）；当前约 0.28 MB/s，预计数小时，完成后解压做 MOFDiff 记忆化检查。
- 产出：`generation/novelty/mofflow2_novel_sbu_review.csv`；脚本 `review_novel_sbus.py`。

### 2026-11-11 生成输出化学后过滤（完成）

- 规则（`filter_generated_sbus.py`）：含金属 → 节点跳过；非碳阴离子（`[O-2]`/`[OH-]`/卤素等白名单）→ 节点组分接受；含碳有机 SBU 检查 RDKit/自由基/电荷（硬有效）+ ≥2 结合基团（羧酸/芳 N/酚羟基/腈/胺/硫醇/膦酸/磺酸，连接体适用）；非碳非节点小分子记为 guest 单独统计。
- 校准（训练集 20,000 条序列 vs 生成 100 条）：硬有效 88.3% vs **81.0%**；连接体适用 83.6% vs **77.0%**；无 guest 61.5% vs **55.0%**；连接体适用且无 guest 48.5% vs **41.0%**。
- 端到端（序列→组装 CIF→UFF/MACE）：化学有效 41/100；**化学+结构有效 18/100（18%）**。生成失败原因：guest 45、RDKit 无效 21、bind<2 6、自由基 3、电荷 1。
- 早期“3–6% 通过”是 `[O-2]` 被误分类为有机 SBU 所致，已修正；生成化学质量接近训练分布（85–93%）。
- 产出：`generation/novelty/mofflow2_chemfilter_sequences.csv`、`mofflow2_chemfilter_end2end.csv`；脚本 `filter_generated_sbus.py`。
- 下一步：扩样本；条件生成对照；BW-DB 下载中（速度慢）。
- **待办**：79 个 UFF 结果汇总与有效子集；有效结构的 PACMOF 充电与漏斗重算；UFF 弛豫后的 CIF 无电荷，不能直接沿用旧 PACMOF 文件。若有效子集过小，MOFDiff 无条件基线只能作为“生成器原始输出质量”的证据，不能与规则式/EGMOF/MOFFlow-2 做性能排名。

### 2026-11-12 scale1000 扩样本：MOFFlow-2 完成结构筛查，MOFDiff/EGMOF 已启动（进行中）

- **MOFFlow-2 scale1000**（11-11 16:22 启动；worklog 此前未记录）：1000 条条件序列（temp 1.0、target 5.0、batch 100）→ **754 可组装 CIF（75.4%）**。
  - precheck（754）：clean_geom **306（40.6%）**；<0.9 Å 重叠 444（58.9%）；断开片段 90（11.9%）；全部含金属。对比 pilot100（40/77=51.9% clean、37 重叠、12 断片），scale1000 重叠率更高、断片率相近。
  - 去重（StructureMatcher）：**676/754 唯一（89.7%），14 个重复组、92 个成员（78 个重复，10.3%）**；与 pilot100 的 8/77=10.4% 一致。
  - UFF：212/754 可参数化（28.1%），**202/754 弛豫后有效（26.8%）**；UFF 可处理的结构中 202/212=95.3% 有效。失败类型以 lammps-interface 的 `Invalid atom ID in Dihedrals` 为主（446），另有 96 个无输出。
  - MACE fallback：541 个 UFF 工具失败送 MACE；截至 11-12 11:05 完成 **425/541（78.6%）**，8 并发、单任务约 15–20 min，预计还需 ~3–4 h。
  - 数据库 novelty（精确同式预筛 + StructureMatcher，365,010 参考结构）：**0 结构重复**；同式候选 CSD 0 / CoRE 15 / hMOF 43 / MOSAEC 50，均非同一结构。
  - 构筑块 novelty（vs 187,047 训练序列 / 148,102 有机 SBU）：1000 条中 **649 唯一序列**、657/1000 序列不在训练集；有机 SBU 504 个唯一，**156 个（31.0%）训练集外**（pilot100 为 21.7%）；**162/1000 样本含 ≥1 个新 BB**；invalid SMILES 741 次（699 唯一）；金属节点 19 唯一、14 新。
  - 序列级化学过滤（1000 条）：hard-valid **47.2%**、linker-suitable **45.6%**、no-guest **57.6%**。与 pilot100 的序列级结果（44.0% / 41.0% / 55.0%）一致。**口径更正**：早前引用的 81%/77% 无法从逐序列 CSV 复现——77% 对应 per-SBU 连接体适用率（pilot100 为 76.9%），81% 口径不明（per-SBU 硬有效 92.3%，per-sequence 硬有效 44%）；后续统一以 per-sequence 为准，per-SBU 作为辅助指标（scale1000：连接体适用 69.1%、硬有效 83.5%）。失败原因：RDKit 无效 557、non-MOF guest 457、bind<2 36、自由基 22。
- **MOFDiff scale1000**：已启动无条件采样（GPU 0，n=1000、batch=100、seed 42）。环境为 `/share/rickyswork/ai_mof/envs/mofflow2`（带 torch_scatter），需 `LD_LIBRARY_PATH=$ENV/lib` 且 `PYTHONPATH=MOFDiff`；`--model_path` 必须绝对路径。2 样本 smoke 耗时 61 s，1000 样本预计数小时。完成后依次 assemble → precheck/dedup/UFF/MACE。
- **EGMOF scale1000**：已启动目标条件生成（GPU 1，`EGMOF/.venv`，n=1000、target 5.0、build_cif=True）。4 样本 smoke 4/4 有效。完成后做同一套 precheck/dedup/UFF/novelty。
- **BW-DB 下载**：11-11 的 16 线程 Range 下载在 2.16/3.99 GB 处中断（文件预分配为全 size，含 129/238 个完整 16MB 块）。Zenodo 对 Range 请求间歇返回 403（限流）。已部署 `bwdb_watch.py`：每 3 min 探测访问，恢复后按零块扫描补齐缺失的 109 块（~1.83 GB），最多 20 轮，完成后 `gzip -t`。仍缺 MOFDiff 记忆化检查。
- 脚本：`generation/resume_dl.py`、`bwdb_watch.py`、`mofdiff_plausibility/dedup_dir2.py`、`chem_filter_seqs.py`、`egmof_scale.py`；本地镜像 `generation/scale1000_mofflow2/`。
- **待办**：MACE 完成后合并 UFF∪MACE（`combine_mace.py`）→ 最终有效率、条件有效率、chem+struct 端到端；MOFDiff/EGMOF 生成完成后跑同一套结构筛查；BW-DB 完成后查 MOFDiff 记忆化。

**11-12 中午更新（生成完成/筛查启动）**：
- MOFDiff 1000 样本采样已完成（`pretrained/mofdiff_ckpt/samples_1000_seed_42/samples.pt`）；`assemble.py` 运行中（~1.5–2.3 s/样本，预计 30–40 min）。注意：无 GPU 时采样极慢（8 样本 4.5 min 未完成），加 `OMP_NUM_THREADS=4–8` 后正常；`model.device` 为 cuda，但采样主要受 CPU/小 batch 影响。
- EGMOF 1000 样本生成完成：prop2desc 采样 1:45；desc2mof 4 个 batch 各 ~60–70 s；`cif/` 实际写出 **751 个唯一 CIF**（963 行结果、951 个带 cif 名，其中 200 个文件名重复被覆盖）→ 重组合导致的重复率约 21%。已启动 precheck + dedup + UFF 批量弛豫（12 并行，751 个；每个约 1–2 min，预计 ~1.5–2 h；`.err` 里的 OpenMPI openib 警告不是失败）。
- 已把 `combine_mace.py` 放到服务器 `/tmp/`，MACE 完成后可直接合并。
- 结论待补：EGMOF 条件可控性（target 5.0）与 751 个唯一结构的有效率；MOFDiff 1000 的装配率与后续 UFF/MACE。

**MOFFlow-2 scale1000 最终（结构口径）**：
- MACE fallback 结束：541/542 个 UFF 工具失败中 **480 个完成**，62 个 **30 min 超时**（`mace_fail_list` 里的 62 个），计入 unresolved，不应当直接当结构缺陷。
- UFF∪MACE：UFF valid 202 + MACE valid 225 → **最终有效 427/754 = 56.6%**（pilot100 为 66.2%）；UFF 可处理结构内有效率 202/212=95.3%。按原始 1000 条计 42.7%。
- 化学+结构端到端（`chemfilter_1000_end2end.csv`）：**166/1000 = 16.6%** 原始序列同时化学与结构有效（占 754 个已组装结构的 22.0%）；pilot100 为 18%。1000 条中 hard-valid 47.2%、linker-suitable 45.6%。
- 与 pilot100 的差异：结构有效率 56.6% vs 66.2%，novelty SBU 31.0% vs 21.7%，去重率 89.7% vs 89.6%，化学端到端 16.6% vs 18%。整体一致，结构有效率略降；62 个 MACE 超时是部分原因。
- 本地镜像新增 `generation/scale1000_mofflow2/combined.csv`、`chemfilter_1000_{sequences,end2end}.csv`。

### 2026-11-12 14:47 scale1000 中期（cron 检查）

- **MOFDiff**：`assemble.py` 完成，**720/1000 可组装（72.0%）**；precheck：clean **249/720（34.6%）**、<0.9 Å 重叠 371（51.5%）、断开片段 174（24.2%）；去重 **720/720 唯一**（同 pilot100 的 100% 化学式唯一）；UFF 批量弛豫进行中（475/720）。已启动 `post_mofdiff_uff.sh` 链（UFF→summary→MACE→combine）。
- **EGMOF**：UFF 批量弛豫完成（751/751，ALL_DONE）；`uff_summary.py` 运行中；数据库 novelty 完成：**0 结构重复**（同式候选 CSD 0、CoRE 50、hMOF 100、MOSAEC 93）；precheck clean 262/751（34.9%）、重叠 485（64.6%）、断片 33（4.4%）。`post_egmof_uff.sh` 在 summary 后会自动跑 MACE fallback 与 combine。
- **BW-DB**：14:46 仍 403（Zenodo 对服务器 IP 限流）；watchdog 继续每 3 min 探测。
- 本地镜像：`generation/scale1000_mofdiff/{precheck,dedup}.csv`、`generation/scale1000_egmof/{precheck,dedup,novelty_exact}.csv`。

### 2026-11-12 16:07 scale1000 更新

- **MOFDiff**：UFF 批量弛豫 720/720 完成（15:06）；`uff_summary.py` 运行中（15:06 启动，预计 ~16:10）。数据库 novelty 完成：**0 结构重复**（同式候选 CSD 0 / CoRE 9 / hMOF 35 / MOSAEC 37）。
- **EGMOF**：`uff_summary` 完成：**UFF ok 743/751，valid 657/751（87.5%）**；MACE fallback 8 个中 3 个完成（15–20 min/个）；完成后自动 combine。
- **BW-DB**：16:05 仍 403，watchdog 正常。
- 注意：`plausibility/PIPE_DONE` 是第一条链（UFF 完成）写的，第二条 summary→MACE→combine 链仍在跑，勿误判为全部完成。

### 2026-11-12 MOFid 补充验证（生成提取完成，完整训练参考进行中）

- 按用户要求补 MOFid：官方 snurr-group 源码独立编译，8 编译线程；Java 17 独立运行时。源码 SHA256 `7ff4f7ab08fc830d87519acf33f34130bdcb37e856b8861b95b2e147fbd71d02`，官方 Python 包版本 1.1.0。
- 训练结构资产可用：MOFFlow-2 `MetalOxo_final_train.lmdb` 187047 条，与序列训练文件条数一致；按上游使用 cell_1 + atom_types + gt_coords（笛卡尔）重建 CIF。复现上游金属节点去点连接表示后，20 条抽样的构筑块集合与同键训练序列全部对应。
- 采用解析字段建立身份：化学片段排序去重；完整键另含 topology 和 cat；文件名与版本元数据不比较。ERROR/NA/UNKNOWN/TIMEOUT/MISMATCH 单列 partial，保留原始输出、逐输入 SHA256 和失败日志。
- HKUST-1 控制：节点/连接体/tbo 正确；原文件、重命名、2x1x1 超胞共 3 次完整键一致。
- 训练抽样（LMDB 字典序前100）：100 化学片段键，95 完整身份，5 partial；用于流程检查。
- 生成结构 1181/1181 提取完成：原始 CIF 754 个，536 化学片段键（71.1%），44 完整身份（5.8%）；弛豫有效 CIF 427 个，408 化学片段键（95.6%），107 完整身份（25.1%）；其余 partial。
- 原始/弛豫 427 对中，376 对都有化学片段键，25 对相同；19 对都有完整身份，9 对相同。涉及键感知、氢电荷表示、组装/弛豫变化，尚待逐对诊断。
- 完整训练参考流水线已启动：重建187047训练CIF -> 16并发MOFid -> 自动比较。路径 `/share/rickyswork/ai_mof/generation/mofid_validation/full_reference/`，日志 prepare.log/run.log；完成标记 ALL_DONE。完整覆盖前无匹配只记 no_match_in_processed_reference；不发布全训练集新颖率。
- 之前156/504保留为序列 canonical SMILES 差集口径；MOFid框架/连接体结果单列。
- 本地报告 `generation/mofid_validation.md`；完整生成结果及控制结果已同步 `generation/mofid_validation/`。脚本 mofid_prepare.py/mofid_validate.py/mofid_compare.py/mofid_controls.py/mofid_summarize.py/run_mofid_reference.sh。

### 2026-11-12 项目工作地图

- 新增 PROJECT_MAP.md：模块级能力清单、证据入口、当前主线/性能支线、P0-P3 工作队列与验收条件；覆盖三引擎、规则/锚点/组装、Nexerra、粗粒化自组装、质量/身份/新颖性、特征/代理/模拟/公平对照、任务入口等。
- 新增 generation/project-map.html：12 模块交互总览，可切换当前主线/研究缺口/已有性能管线；默认标题显示功能状态。
- 图源 generation/project-map.architecture.json；9/9 showcase 校验通过，0错误0警告；Chrome 四种桌面尺寸无溢出，深浅色截图经视觉复核。收据 generation/project-map.handoff.json。
- 地图状态为工作日志快照；后续先追加日志，再更新能力状态和待办验收条件。

### 2026-11-12 分层研究工作台重做

- 根据用户对旧版过于粗略、脉络不清的反馈，新增 generation/project-workbench.html，采用项目专用的分层研究图。
- 六视图：全局研究脉络、生成路线拆解、质量关口与分流、身份与新颖性证据、性能评价与历史反馈、工作队列与依赖；共60个语义节点。
- 节点详情包含目标、输入、产物、验收条件、现有发现、文件依据和下一动作；支持上游/下游追踪、搜索、缩放、SVG导出和当前浏览器备注。
- 显式表示三引擎中间表示差异、原始分母、UFF工具失败的MACE分流、结构缺陷/未解决分类、三类新颖性参考与研究闭环。
- 工作依赖修正：全训练参考匹配与生成结构诊断可并行；节点状态仍为2026-11-12文件快照。
- 全部证据路径核验存在；6视图无节点文本裁切、无连线穿越无关卡片；实际测试展开、双上游追踪、搜索、备注、缩放、SVG解析通过。截图覆盖1440/1920桌面以及六个视图。
- 更新 PROJECT_MAP.md 以新版为主要入口；旧版Archify概览保留为历史。
- 可维护源：generation/build_workbench.py + project-workbench.template.html；检查结果 generation/project-workbench.check.json。

### 2026-11-12 工作台打开体验复核

- 用户反馈不好打开后，补查交付入口与窄窗口。原浏览器运行测试通过，但HTML文件链接可能由编辑器接管，未覆盖真实进入方式。
- 新增根目录 打开项目工作台.cmd 与 generation/serve_workbench.py：仅监听127.0.0.1，启动/复用服务并打开浏览器；当前端口8765。本机网页证据改为统一只读预览。
- 提交Codex浏览器面板打开请求，工具返回queued；独立HTTP浏览器检查已完成。
- 改善1100px以下顶部导航、窄窗口初始适宽；history哈希更新容错。
- 六视图和主要交互从HTTP入口复测通过；600/900px无水平溢出且地图适宽；首页和证据返回200，非引用文件与路径穿越返回404，重复启动复用服务PID。
- 复核说明 generation/WORKBENCH_REVIEW.md；更新 PROJECT_MAP.md 的推荐打开方式。

### 2026-11-13 scale1000 三引擎全部完成（最终结果）

- 三引擎各 1000 原始样本已全部跑完结构筛查（precheck → dedup → UFF → MACE fallback → combine）。最终口径：

| 指标 | MOFDiff（无条件） | MOFFlow-2（CO₂ 条件） | EGMOF（CO₂ 条件） |
|---|---|---|---|
| 原始生成 | 1000 | 1000 序列 | 1000 请求（963 行 / 751 唯一 CIF） |
| 可组装/唯一 CIF | 720（72.0%） | 754（75.4%） | 751（75.1% 原始；78.0% 963 行） |
| 原始几何干净 | 249/720（34.6%） | 306/754（40.6%） | 262/751（34.9%） |
| <0.9 Å 重叠 | 371（51.5%） | 444（58.9%） | 485（64.6%） |
| 断开片段 | 174（24.2%） | 90（11.9%） | 33（4.4%） |
| 去重后唯一结构 | 720/720（100%） | 676/754（89.7%） | 751/751（100%）* |
| 唯一化学式 | 717/720（99.6%） | 316/754（41.9%） | 719/751（95.7%） |
| UFF 可参数化/有效 | 685 / 418 | 212 / 202 | 743 / 657 |
| MACE 补充有效（超时） | 7（18） | 225（62） | 2（5） |
| **最终结构有效** | **425/720（59.0%）** | **427/754（56.6%）** | **659/751（87.7%）** |
| 占原始生成 | 42.5% | 42.7% | 65.9% |
| 化学+结构端到端 | —（BB 来自缓存） | **166/1000（16.6%）** | —（固定 BB 库） |
| 数据库精确结构重复 | 0 | 0 | 0 |
| 同式候选 CSD/CoRE/hMOF/MOSAEC | 0/9/35/37 | 0/15/43/50 | 0/50/100/93 |
| BB 新颖性 | 固定 BB 缓存 | 156/504 新 SBU（31.0%）；162/1000 样本 | 固定库（仅组合） |
| 体积范围 Å³ | 788–40,150 | 564–7,045 | 166–174,116 |

- * EGMOF 对 751 个落盘文件去重为 100%；但 963 行生成结果中约 21% 的文件名重复被覆盖，按原始行计唯一率 78.0%。
- 结论：
  1. 规模放大后结构有效率排序 **EGMOF 87.7% > MOFDiff 59.0% ≈ MOFFlow-2 56.6%**；pilot100 的 MOFFlow-2 66.2% > MOFDiff 51.9% 在大样本下收敛。
  2. MOFFlow-2 原始几何最干净（clean 40.6%、断片 11.9%），但化学端到端仅 16.6%、化学式唯一率仅 41.9%（BB 词汇有限、同式异构多）；结构有效率与 MOFDiff 相当而分子多样性明显更差。
  3. EGMOF 最终有效率最高、断片最少，但原始重叠最多（64.6%）、约 21% 输出重复；BB 固定，novelty 只在组合层面。
  4. MOFDiff 结构/化学式几乎全唯一（99.6%），但装配缺陷最重（断片 24.2%、重叠 51.5%），最终有效率与 MOFFlow-2 同档。
  5. 三引擎在 365,010 个参考结构中均 **0 结构重复**；MOFFlow-2 是唯一有真实新 SBU 的引擎（31% SBU、16.2% 样本），但仍以近邻类似物为主。
- MACE 超时（18/62/5）记为 unresolved，不是结构判定失败；分母含超时项，因此 MOFDiff/MOFFlow-2 的最终有效率是保守下限。
- BW-DB：Zenodo 对服务器 IP 的 403 限流持续超过 24 h（到 11-13 10:18 仍 403）；watchdog 已重启为 48 h，解封后自动补齐。MOFDiff 记忆化检查仍待 BW-DB。
- 本地：`generation/scale1000_{mofdiff,egmof,mofflow2}/`（precheck/dedup/uff_summary/combined/novelty 等）；服务器脚本 `post_mofdiff.sh`、`post_mofdiff_uff.sh`、`post_egmof_uff.sh`。

### 2026-11-13 10:25 MOFid 全训练参考完成与最新进展核对

- 服务器全量训练参考于04:02完成：187047/187047已处理；171978完整身份（91.94%）、15069部分解析。
- 自动比较结果：原始754个中44个可比完整身份均未匹配；弛豫有效427个中107个完整身份，8个匹配训练参考、99个未在已完整解析参考中匹配，其余320个未完整识别。
- 8个命中样本对应2种唯一身份：rna同一身份7个（015/041/278/368/567/604/664），pcu身份1个（326）。完整身份匹配与化学片段集合匹配分别统计；后者原始73个、弛豫54个。
- 已同步本地 comparison/comparison.json、matches.csv、training_reference_summary.json；更新MOFid报告与工作台状态为11月13日。
- 实时复核千样本combined：MOFDiff425/720有效，EGMOF659/751有效；MOFFlow-2保留427/754有效。三引擎结构筛查全部完成。
- BW-DB截至10:24仍403，MOFDiff训练集记忆化参考仍缺。后续重点为命中样本核查、MOFid部分解析归因、生成器条件响应与多种子独立对照。

### 2026-11-13 连接体—框架组合小试v1（完成）

- 用户授权后执行小规模可归因试验。先登记PROTOCOL.md并冻结输入/哈希，再组装和统一弛豫。
- 来源：MOFFlow-2千样本化学合格、有原生CIF、单一有机连接体类型、恰两个羧酸锚点的70个唯一候选。按固定哈希排序及训练内外分层选20个（8训练序列外、12训练内），选择不使用原生结构成功或MOFid标签。20个标准化后连接体唯一，原生节点均为V。
- B模板固定pcu/N16(Zn4O)，该组合取自EGMOF有效输出pcu+N16+E102。干预改变节点/拓扑/构建方式，连接体固定；不把效果仅归于组装算法。
- 阳性控制BDC、BPDC经同流程组装、统一MACE、MOFid全部通过，原始/目标身份保持。
- 正式B：19/20在固定seed=7构象和20°连接方向判据下不兼容，1个组装成功；无补样、未放宽阈值。
- A20个与B1个全部采用相同MACE-MP medium float64、变胞BFGS150步、fmax0.2、maxstep0.05；共21次正式+2次控制=23次，全部完成、无超时。最多每GPU一个任务，线程限制2。
- 几何有效A7/20、B1/20；收敛A1/20、B1/20；MOFid恢复目标连接体A5/20、B1/20；完整拓扑A0/20、B1/20；联合主终点A0/20、B1/20（配对exact McNemar p=1，未建立总体改善证据）。八个训练外片段全部被模板方向检查拒绝。
- 唯一重新组装案例L14，原生mofflow2s_542、seq742、训练内连接体CCOc1cc2cc(C(=O)[O-])cc(OCC)c2cc1C(=O)[O-]。原生dmin0.484Å、3片段、拓扑ERROR；模板dmin1.082Å、1片段、23步收敛、目标连接体恢复、pcu完整身份。
- L14模板身份在171978条已完整识别训练参考中0匹配；15069条部分解析的覆盖缺口保留。
- 结论：固定线性pcu模板的主要损失是几何兼容性；得到一个可复核转移案例。下一轮应按连接方向/局部配位几何匹配模板，保留本轮冻结协议和失败分母。
- 本地generation/linker_framework_pilot/（协议、代码、结果、CIF、图、AUDIT.json）；完整原始日志归档evidence_archive/与results_bundle.tar.gz，已校验冻结哈希、20唯一连接体、23完成记录、21正式MOFid和终点计数。服务器generation/linker_framework_pilot_20261113/。
- 工作台同步小试结论与证据链接，浏览器检查通过。


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


## 2026-11-13：DAO-P登记为后续备选

按用户要求记录：先测完当前工作，再评估DAO-P优点能否接入；关注噪声态能量、坐标/晶胞梯度引导与MOF域适配。已写入generation/DAO_CANDIDATE.md、NEXT_STEPS.md与生产端可行性备选。当前未安装、未复现、不启动DAO任务。


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

- 结项交付复核：26个CIF的哈希、几何、严格身份和优化日志收敛均通过；CANDIDATES.zip完整性通过；工作台六视图、交互、600/900窗口和三个新增证据HTTP入口检查通过。服务器8卡已空闲，未留后台计算。阶段完成标志generation/budget_confirmation/PHASE_COMPLETE.json已生成。

## 2026-11-16：收敛敏感性对照完成

用户授权对26个既有交付结构严格精修，并诊断4个S300失败终态及其D19终态。协议先登记，34条从旧终态用相同MACE/float64、变胞BFGS，广义力阈值0.05、最多追加300步/1200秒。全部34条计算完成，31条收敛；26主样本全部收敛并保留严格连接体集合、pcu及原完整框架身份。追加步数中位112.5（27–171），能量变化中位−0.00933 eV/原子，体积变化中位−7.33%（−12.82%至+0.75%）。2.5 Å下26个结构Zn配位数均保持，角RMS偏差中位6.71°→5.11°，22/26下降；其他截断敏感性保留。

诊断8条中2条为既有D19成功且保持成功，新增救回0；单/双连接体成功数仍26/30、28/30。S_B15/B29等可收敛但身份仍失败，S_B02能量异常下降而残余力极大，完整保留失败记录。7个主样本物理原子力略超0.05（最高0.05124 eV/Å），广义力均低于0.05，两者分别记录。

产物generation/convergence_sensitivity/REPORT.md、results/收敛精修对照.png、per_structure.csv、逐步历史及26个accepted_primary精修CIF。原输入、模型和运行脚本哈希、步数与收敛记录审计均通过；原候选包未改写。建议后续目标条件/吸附对照统一使用精修后的结构与处理条件。精修从旧CIF重启优化器和变胞参考，不解释为纯阈值独立因果效应；本轮未算吸附或形成能。

## 2026-11-16：回归目标条件响应与分离性能主线

用户确认精修结果并要求更新worklog、回归主线。新试验协议generation/conditional_response/PROTOCOL.md已在生成前登记：同一条件模型、目标2/5、配对种子1601/1602，每组600条，共2400条；化学过滤后每组哈希抽最多15种，跨组身份共享计算，统一种子7/pcu/N16与0.2→0.05两阶段优化。先核对训练prop范围，再执行生成，不按结果补采样。

检查官方本地README、dataset_seq.py及seq_module.py确认：条件标签是CO₂工作容量，训练直接读取prop，推理直接嵌入target_property。分别检验目标条件能否改变候选、以及能否迁移到项目SiH₄/CO₂分离性能；不把该数值标成项目选择性目标。吸附沿已有管线衔接，实际力场/电荷/超胞与工况在性能结果产生前另行冻结。

- 条件采样实际完成2400/2400：s1601目标2/5合格序列4/118、唯一身份4/49；s1602目标2/5合格序列1/112、唯一身份1/46（每组分母600）。同种子跨目标原序列600/600改变，合格身份交集均0。沿当前单连接体二羧酸路线的兼容性差异明显，低目标样本不足15按协议全取、不补样。四组入选4/15/1/15，共35组成员、29种唯一连接体，已启动相同两阶段优化。
- 训练prop范围−0.199905至5.115154，99%分位2.35803；目标5接近上沿，结果按此解释。新增脚本命名冲突和PACMOF写出精度问题及修复见generation/conditional_response/OPERATIONS_NOTES.md；原始采样和原精修候选不变。

- 本轮29种连接体结构处理及MOFid实际完成。四组收敛且严格验收3/4、11/15、1/1、13/15；去重24种有效结构，目标2为4种、目标5为20种。C013大残余力两阶段均跑满预算，失败保留。生成/固定抽样/结构签名及分母审计通过。
- 24种有效结构PACMOF/原几何保持/净电荷检查全部通过，Zeo++24行0错误；v3独立控制Widom/GCMC均正常结束。新CIF空间群标签已做数值几何不变的旧RASPA兼容适配，PACMOF使用已有sklearn1.7.2环境。完整运行偏差记录不覆盖原失败。
- 正式性能对照已启动96个任务（24结构×2种子×Henry/GCMC），16并发，当前仍在采样。配置在性能结果前登记并签名，见PERFORMANCE_PROTOCOL.md及服务器performance/frozen.json；全体有效结构均运行，不按Henry再选GCMC。自动汇总入口performance/summary.json、per_candidate.csv、AUDIT.json，完成标记PERFORMANCE_ANALYSIS_DONE。当前结论为条件影响当前组合路线候选明显；项目分离性能是否改善仍待计算。

## 2026-11-17：主线96项吸附对照全部完成并复核

服务器11月16日16:58已完成96/96正式Henry/GCMC及自动解析；今天10:06起核查完成标志、进程和结果。当前simulate进程0，性能审计96完成、0错误，重新执行生成/抽样/结构/性能关联审计通过。24种候选的Henry与GCMC均具有两个模拟种子，原始结果和哈希保留。

按唯一身份合并，目标2/5有效候选4/20种；Henry选择性中位0.890/0.832，混合GCMC选择性中位0.867/0.848，最佳0.968/1.641。逐生成种子GCMC中位1601：0.862→0.849，1602：0.968→0.849。目标5中5/20种S_CO2>1（C009、C011、C016、C021、C024），目标2为0/4；C024最佳1.641，C021为1.631。

结论：条件确实改变当前固定组合路线的候选集合与产率；本批整体分离选择性中位数没有提高，目标5中出现少量更优候选。目标2只有4种且其中一生成种子仅1种，作为初步描述性比较。原模型条件为CO₂工作容量，项目选择性按迁移效果解释。未触发预登记50%相对误差/零CO₂提示；数值收敛尚未独立延长运行复核。

本地已取回summary、per_candidate、parsed_runs与AUDIT，更新REPORT、README、NEXT_STEPS、PROJECT_MAP及工作台。下一步用已有性能标签分析选择性/容量/SiH₄损失，形成项目目标驱动对照方案；本次进度核查没有启动新批次计算。

## 2026-11-17：整理项目工作与研究思路

新增PROJECT_OVERVIEW.md作为当前总览，按最终成功标准、生产/验证链、历史评价底座、三引擎角色、组合路线、结构精修、条件/性能结果与下一步决策串联。明确26个B系列和24个C系列为不同试验批次，历史737任务为另一批规则/已知库评价，保留各批分母与证据。

整理时以历史冻结S_CO2≥2、q_SiH4≤1.5、q_CO2≥0.001回看当前24种候选，0/24通过（全部S<2）；明确标为追加的历史标准参照，不改本轮预登记终点。当前主线重点为利用项目性能标签提高候选命中密度，先分析选择性/容量/SiH₄损失，再登记小规模反馈对照。DAO-P保留备选。

清理NEXT_STEPS、PROJECT_MAP、生成层README中已过时的“仍在运行/暂停吸附/条件待补”入口状态；历史时间线保留。工作台同步加入项目总览与当前决策依据。本次仅整理本地文档和图表入口，未启动新的服务器计算或上传报告。

## 2026-11-17：用户纠正项目总目标，恢复模块交付定位

用户指出原始意图是做AI设计MOF模块，助手此前把SiH₄/CO₂案例的性能指标写成项目最终目标，造成目标层级与优先级偏移。已纠正：产品目标是可调用的设计模块，接收受支持需求/约束、返回多个候选CIF及来源、验证状态、失败说明；SiH₄/CO₂为已有应用验证案例，选择性/容量/命中率仅用于该案例评价。

既有引擎比较、组装、精修、MOFid和96项吸附结果保留，不修改冻结实验。下一步优先定义模块输入输出、封装已验证路线、统一任务编排和候选交付，再按需扩展自然语言入口与应用评价。继续深入分离性能反馈和DAO-P列为扩展研究，不能自动取代模块交付。

已同步修正PROJECT_OVERVIEW、NEXT_STEPS、PROJECT_MAP、生成层README及工作台优先级。本次只校正定位与文档，未启动新的计算或实现未经讨论的完整接口。

## 2026-11-17：AI设计MOF模块v0.1实现与验收

用户授权按EGMOF主底座、MOFFlow-2连接体探索、场景适配分离的方案推进。新增mof_design包及pyproject.toml，提供Python API和CLI（engines/scenes/validate/run/submit/status/cancel），严格任务配置、两个后端、预算/取消/超时、元素/拓扑后过滤、MACE两阶段精修、可选MOFid、分层去重、状态/事件、来源签名和原子发布的候选ZIP。控制端标准库，重依赖与权重沿runtime指定环境复用，未训练新模型。

20项本地测试通过，覆盖配置、分母、去重、路径边界、包完整性、便携任务ID、真实子进程超时与异步取消。Windows taskkill可能被受限环境拒绝，增加自有直接工作进程终止兜底；Linux树终止逻辑不变。Wheel已构建，独立目录安装导入验证通过；源快照、试验记录及该Windows补丁范围见mof_design/ACCEPTANCE.md。

真实服务器目录generation/design_module_v01_20261117。EGMOF任务design_6e6ab023c5164c0f请求2、最多8、实际3次提案交付2（673.0秒）；C0002因MOFid未完整识别而拒绝。连接体探索design_f0c4b4c54c1f4389原序列100、请求2、最多6、实际2提案交付2（261.0秒）；连接体集合和pcu检查通过。两条服务端资产/源代码/候选ZIP审计和本地便携包审计均通过，原生生成/科学验证代码与本地一致；随后仅Windows监督器分支做已单测的兜底改动。

本地交付module_delivery/v0.1.0，含安装包、两条真实候选包、请求/结果/审计、用法与测试日志。当前场景为已有CO₂性质模型，单位按原生标尺且未独立核实；EGMOF未加载RF，WMSE引导跳过，不能将结果作独立性能预测。拓扑约束需MOFid；约束为生成后过滤。模块暂不含训练入口、自然语言/网页或跨用户GPU调度，复杂模型运行沿已验证服务器环境。具体气体/场景训练留待实际需求。

- 最终发布补充：服务器隔离目录generation/design_module_v01_release_20261117使用最终代码完成Linux20/20测试和runtime预检，Windows20/20亦通过。源生模型验收快照单独保留，避免改写其源代码签名。取回tests.linux.log；两条原生任务与后续模块测试均结束，8张GPU已空闲。最终入口module_delivery/v0.1.0/INDEX.md，含wheel、源码、用法、验收记录、两个候选ZIP与发布哈希。

## 2026-11-20：新模块独立功能复测完成

用户授权测试新模块。对已交付v0.1.0重新独立安装，engines/scenes入口通过，Windows单元测试20/20通过。新增module_testing/20261120/run_acceptance.py，冻结请求、种子、预算、GPU和源代码哈希；服务器使用最终发布快照design_module_v01_release_20261117，新输出module_test_20261120，保留11月17日全部原始记录。

9项功能验收全部通过：未知场景、跨引擎场景、未知约束、无效预算4项正确拒绝；1秒超时和原生序列初始化阶段取消均终止且无任务残留进程；固定Zn框架遇到禁Zn约束正确拒绝候选并交付零CIF，失败原因forbidden_elements。该约束控制任务的预期状态为failed。

真实正向任务EGMOF design_720d2362be5a46b2（seed20261120）请求2、预算6、实际2提案交付2，148.592秒；MOFFlow-2连接体探索design_99c3c75f7ad84848（seed20261121）100条序列、请求2、预算4、实际2提案交付2，95.855秒。四候选均记录MACE两阶段收敛（fine fmax=0.05）、原子保持、几何通过和MOFid完整识别。EGMOF为pcu/fsc，连接体路线均pcu且连接体身份一致。

服务器独立重读导出CIF：原子数130/48/83/107与声明一致，最小原子距离1.0863/1.0454/1.0971/1.0099 Å；EGMOF禁Cd/Hg/Pb约束满足。五任务服务端资产/交付审计及下载后的便携审计全部通过，ZIP与CIF哈希一致。该审计核对记录和包完整性，未额外重算能量/力。本次功能小样本用于验证调用与交付流程；未新增吸附模拟或模型训练，未发现需要修改生产代码的问题。

证据已下载至module_testing/20261120/results/server/RESULTS.json，各任务包含请求、状态、候选记录、MOFid、CIF及候选ZIP；本地安装检查install_check.json、单测unit.windows.log与portable_audit.json位于results。控制任务取消发生在序列初始化，不作为中途优化取消验证。

## 2026-11-20：增加自动生成报告环节

用户提出需要生成报告环节。现有REPORT.md仅为简短摘要；新增标准库report.py，在delivery.finalize中生成离线REPORT.html和Markdown入口并收入候选ZIP。报告展示目标/场景原生单位声明、种子/预算/约束、任务耗时、交付计数、候选几何指标、实际优化收敛、MOFid拓扑、拒绝原因、来源与哈希链接及逐候选完整记录。HTML对所有外部文本转义，CIF链接检查目录边界，无远程资源或新增推断。

使用本日五个真实任务的复制目录生成示例（两个成功、约束失败、取消、超时），新候选ZIP均通过便携审计；原始任务记录及v0.1.0发布包保持原版。21项测试通过，新增测试覆盖零交付、拒绝原因和恶意HTML文本转义。示例入口module_testing/20261120/report_examples/egmof_user/REPORT.html，全部审计见同目录上级AUDIT.json。本次工作区功能已接入未来任务交付，尚未重发wheel或部署服务器；浏览器视觉验收尚未执行。


## 2026-11-20：研究人员材料报告第一版

用户授权推进面向研究人员的单材料报告和批次对比。新增mof_design/material_report.py，交付自动生成MATERIALS.html、materials.csv/json及每候选材料档案、结构投影、可用的连接体二维图，与任务报告双向链接并随ZIP交付。新增material-report命令支持为已有任务生成档案且不改原ZIP/来源签名；可选reports依赖声明加入pyproject。

材料数据从最终CIF实际提取：计算晶胞组成、元素/金属、原子数、晶胞参数/体积、计算质量密度、最小距离；spglib空间群记录0.01 Å容差，MOFid拓扑/节点/连接体与两阶段优化记录直接关联。图为笛卡尔三方向原子投影和晶胞边线，连接体图保留识别电荷。孔隙、应用性能、新颖性均显式待评价，本次没有启动孔隙/吸附计算或训练。

在衍生report_examples目录为四个真实候选生成档案，并检验取消/超时/约束失败的零候选入口；原服务器和本地冻结验收数据未改。新增2项测试覆盖已知立方晶胞体积/密度/组成和CIF篡改错误；报告3项测试通过，既有模块20项测试通过。五类任务便携审计通过，档案相对链接和ZIP条目检查通过，结果见report_examples/MATERIAL_REPORT_AUDIT.json。浏览器工具因本地file协议限制拒绝打开预览，未绕过该限制；本轮完成数据/链接/打包验证，浏览器视觉复核待完成。当前改动在本地工作区，尚未替换服务器发布快照及旧wheel。


## 2026-11-20：本地工作整理与可携带快照

按用户要求将当前工作收拢到module_delivery/local_snapshot_20261120，提供INDEX.html统一入口、代码/配置/测试、真实验收记录、四候选CIF和任务/材料报告、项目总览/交接/工作日志。文件MANIFEST.json记录SHA256与大小，同级ZIP保存可携带快照。快照不包含大模型权重、虚拟环境或全部历史研究数据，运行配置继续引用现有服务器资产。

整理时重跑20项模块测试和3项报告测试均通过，日志保留module_testing/20261120/results。更新NEXT_STEPS与PROJECT_OVERVIEW，明确本地报告增强版本与11月17日发布版的区别，待办为浏览器视觉复核、后续版本打包部署及按需孔隙/应用评价。本次仅本地整理，没有服务器操作或新计算。


## 2026-11-20：上传 GitHub 模块仓库

按用户明确指令上传至 https://github.com/ricky0748/mof_design.git 。独立克隆目录module_delivery/github_mof_design，main首个提交67b871f，包含当前模块源码、两类报告、23项测试、四真实候选及验收材料、统一README和本地快照入口，共290个文件。上传前在仓库副本重跑20+3项测试通过，推送成功。Git按原始字节跟踪文件以保留CIF/记录哈希；未包含权重、环境和全部历史研究目录。


## 2026-11-20：补传完整项目源码

用户指出初次GitHub提交只包含模块快照，要求补齐项目工作。已补充generation、anchor_rules、cg_assembly、r2_probe、widom_sih4等研究目录的源码、配置、阶段报告、文本结果、组装模板与图件，保留原目录结构。SOURCE_INVENTORY.json逐文件登记补传内容、大小和SHA256，并声明排除权重、环境、缓存、压缩包、论文PDF及完整生成CIF数据。历史服务器专有文件不在本地源码范围。本次为归档与上传，不修改研究算法或重新运行大型计算。
