# 锚点规则 → patchy 粗粒化自组装（HOOMD 5）

把 mof303 里已验证的 `cg_patchy3.py`（六位点八面体节点 + 直链约束）泛化为：**输入任意配体 SMILES + 节点族，自动生成 patchy 自组装体系**。在工作流中的定位：GCMC 之后的头部候选做"能否自组装成目标拓扑"的定性检查，不进打分。

## 流程

```
SMILES + 节点族 ──anchor_rules──> 锚点/X 坐标 ──cg_build──> spec.npz ──run_cg (HOOMD 5)──> .gsd ──analyze_cg──> 指标 JSON
```

| 文件 | 作用 | 依赖 |
|---|---|---|
| `cg_build.py` | 配体粗粒化 + 节点模板 + 随机放置 → `spec.npz` | rdkit、networkx（不需要 hoomd） |
| `run_cg.py` | 读 spec 跑 HOOMD；API 写法与 `cg_patchy3.py` 完全一致 | hoomd 5（服务器 `hoomd5` 环境） |
| `analyze_cg.py` | 配位、占位、桥连、连通、环大小分布 | gsd、networkx |
| `make_cases.py` | 生成 6 个验证用例 × 3 个种子 + `run_all.sh` | — |
| `summarize.py` | 汇总并核对登记的预测 | — |
| `check_specs.py` / `test_analyze.py` | 输入自检 / 分析脚本在理想 sql、kgm、pcu 网格上的单元测试 | — |

## 粗粒化规则

**配体**（自动）：
- 每个环体系（稠环合并）一个 R bead，放在环原子质心。
- 每个连接点 X 一个 C bead，用的是 PORMAKE 约定的 X 坐标。
- 键长取自 3D 构象；R 上每一对邻居之间加一个谐振角。

所以对苯二甲酸的 C–R–C 是 180°，间苯二甲酸是 119°，均苯三甲酸是 3 个 120°，PZDC 是 148°（cg_patchy3 手写的是 120°）。

**长度单位**：用 PZDC 校准，令其 R–C 距离 = 1.2σ（cg_patchy3 的 R0），得到 σ = 1.58 Å。

**节点族**：

| 族 | 位点 | 角约束 | 尺寸 |
|---|---|---|---|
| rod（Al 链，MOF-303） | A×2 轴向 + E×4 赤道 | 与 cg_patchy3 相同 | 位点距中心 0.7σ |
| paddlewheel（Cu 桨轮） | E×4 平面 + B×2 轴向惰性位点（代表溶剂封端） | 对位 180°，相邻 90° | PORMAKE N17 的连接点半径 3.26 Å |
| octahedral（Zn4O） | E×6 | 对位 180°，相邻 90° | PORMAKE N16 的连接点半径 4.33 Å |

**盒子**：节点数密度取 cg_patchy3 的值（36 个 / 16³），再按重复单元长度（节点半径 + 配体半跨度）的立方缩放。

## 位点势：legacy 与 single

拿 mof303 的 `patchy3_fix_v3.gsd` 末帧复查时发现：每个金属确实配了 4 个 C，但并不是 4 个 E 位点各配 1 个。144 个 E 里有 46 个空着，36 个同时吸住 2–4 个 C。原因是 E–C 吸引的截断是 1.5σ，一个位点周围装得下好几个 C。

| 模式 | E–C 吸引截断 | C–C 体积排除 σ | 用途 |
|---|---|---|---|
| `legacy` | 1.5σ | 0.5（与 cg_patchy3 相同） | 只用于复现 mof303 |
| `single`（默认） | 0.8σ | 1.45（接触距离 1.63 > 2×0.8） | 每个位点只能配 1 个 C，环统计才有拓扑意义 |

## 环统计（拓扑指纹）

- **成环用的图**：二齿配体收缩成节点–节点边；三齿及以上的配体作为独立顶点，构成二部图。图上取最小环基。
- **假环过滤**：沿环累加最小像位移，长度超过 L/2 的是绕周期边界的环，单独计数，不进环分布。
- **单元测试**（`test_analyze.py`）：理想 6×6 sql 得到 35 个 4 元环和 2 个周期环；5×5×5 pcu 全是 4 元环；kgm 有限片只有 3 元环和 6 元环。

参考指纹：sql、pcu 以 4 元环为主；kgm 是 3 元环加 6 元环；MOP-1 立方八面体笼是 3 元环加 4 元环。

## 运行（服务器）

```bash
conda activate hoomd5
cd cg_assembly           # 只需拷这个文件夹：cases/*.npz 已生成，服务器不需要 rdkit 或 anchor_rules
bash run_all.sh 6        # 先冒烟测试 4 个用例各 2000 步，再全量 21 个 × 200k 步，6 进程并行
```

服务器上需要 `numpy`、`hoomd`、`gsd`、`networkx`，`hoomd5` 环境里都有。
