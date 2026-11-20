# 生成层当前入口（2026-11-17）

整体思路与当前结论先读[项目总览](../PROJECT_OVERVIEW.md)。当前组合路线为MOFFlow-2连接体→固定pcu/Zn₄O→单构象7→MACE优化及广义力0.05统一精修→严格身份/结构验收→性能对照。同预算比较的26/30、28/30及成本取舍保留在[原试验报告](budget_confirmation/PHASE_CLOSEOUT.md)。

AI设计MOF模块v0.1现已实现：[统一入口与用法](../mof_design/README.md)、[小批验收](../mof_design/ACCEPTANCE.md)。默认EGMOF及连接体探索各交付2份通过验收的CIF。[条件与性能对照](conditional_response/REPORT.md)作为独立应用案例归档。后续按实际需求适配场景。以下为历史规则MVP文档。

---

# 生成层 MVP：规则式种子邻域采样 → 锚点 → 组装 → CIF

这是项目生产层的第一个可跑通版本。目标不是做最终生成模型，而是先把
**「配体变体 → 锚点 → PORMAKE 组装 → 候选 CIF → 元数据」** 这条链路跑通，
让下游的 Zeo++ 特征、代理打分、适用域门槛和 Widom 扩训都能在真实候选上工作。

生成器后续可以替换成 Nexerra / BBA / DiffLinker，接口保持不变：
输入配体 SMILES + 目标节点/拓扑，输出组装后的 CIF。

## 流程

```
seeds.smi
  └─ enumerate_variants.py   芳香 C–H 单取代枚举 + 锚点/价键过滤
       └─ variants.csv       239 个变体
            └─ build_candidates.py   PORMAKE 组装 + 几何判据
                 ├─ out/cif/*.cif          268 个合格候选（单晶胞，P1）
                 ├─ out/bb/*.xyz           构筑块
                 └─ out/candidates.csv     每次尝试的元数据（含失败）
```

## 约束（与"偏向可合成"的路线一致）

- 只枚举**单取代**，取代基限定为 F、Cl、Br、Me、OH、NH₂、OMe、CF₃、CN、NO₂；
- 保留种子的连接数（2 或 3）和锚点类型（羧酸）；
- RDKit 可解析、无自由基、重原子 ≤ 60；
- 去掉重复的规范 SMILES；种子本身保留；
- 组装判据与 `anchor_rules/assembly_test.py` 一致：方向偏差 ≤ 20°、无碰撞、有机键长 0.85–1.9 Å，三齿额外要求 Locator RMSD ≤ 0.3。

## 用法

```bash
cd generation
python3 enumerate_variants.py                 # -> variants.csv
python3 build_candidates.py                   # -> out/cif, out/candidates.csv
python3 build_candidates.py --limit 20        # 只跑前 20 个变体做冒烟
```

## 当前批次（2026-10-21）

| 指标 | 数值 |
|---|---|
| 种子 | 10 个（BDC、DOBDC、NH₂-BDC、DM-BDC、TDC、NDC、BPDC、BTC、BTB） |
| 变体 | 239 |
| 组装尝试 | 613（二齿 × pcu/fcu/nbo，三齿 × tbo） |
| 合格 CIF | **268**（pcu 118、nbo 93、fcu 47、tbo 10） |
| 失败主因 | 大/柔性配体方向偏差超限、fcu 碰撞率高 |

1,4-NDC 和 BTB 的变体没有合格结构，主要是尺寸/柔性导致方向偏差超 20°，下一版可以给它们配 kgm 等弯曲拓扑，或多构象挑偏差最小的构象。

## 结构格式

- 候选文件是**单晶胞 CIF**（P1，含原子坐标和键表），这是交付/存储格式。
- 下游 Widom/GCMC 会按 12.8 Å 截断自动扩成超胞（`UnitCells n×n×n`），超胞不写回 CIF。
- pol 组（N₂/O₂/CO/CO₂）需要电荷：用 `widom_sih4/pacmof_batch.py` 生成带 `_atom_site_charge` 的 CIF。
- 代理特征（Zeo++）直接在单晶胞上算，不需要超胞。

## 元数据（`out/candidates.csv`）

`variant_id, seed, smiles, n_connections, topo, node, build, dev_max, dev_ok, rmsd, rmsd_ok, n_clash, n_bad_bond, n_atoms, success, cif, error`

后续会补：代理预测值、置信度、适用域标记、Widom 标签、生成器版本、预测登记时间。

## 第一批打分结果（2026-10-21）

`score_candidates.py` 用 CRAFTED 690 + 132 个已标注组装结构（权重 5）训练 np 代理，并在扩训后的适用域上打分：

| 指标 | 结果 |
|---|---|
| 候选 CIF | 268 |
| 走代理（域内，5–95%） | **210** |
| 域外 → 直接 GCMC | **58**（BPDC 36、nbo 34 为主） |
| 域内 S_CH4 中位数 | −0.46 |
| 域内 S_CH4 最好值 | −0.36 |
| 有正 np 选择性的候选 | **0** |

也就是说，这批规则式单取代变体里，没有发现对 H₂/Ar/CH₄ 优先吸附的候选；排名靠前的仍是 2,6-NDC/BPDC 的 nbo/pcu 大孔结构，但它们仍然优先吸 SiH₄。CO₂ 打分要等 PACMOF pol 计算完成。

## Novelty 标注（2026-10-21）

`annotate_novelty.py` 把 268 个候选分层，避免把已知结构当成生成新颖度：

| 层级 | 数量 | 说明 |
|---|---|---|
| `known_control` | **17** | 未取代种子搭出的教科书结构，只作对照 |
| `substituted_variant` | **251** | 已知骨架 + 取代基；配体本身大多不在 CoRE |
| `ligand_in_core` | 3 个结构 / 1 个唯一配体 | 只有 BDC 能在 CoRE 的 1,738 个唯一配体里找到 |

`known_control` 包括：MOF-5/IRMOF-1（BDC + Zn₄O + pcu）、UiO-66（BDC + Zr₆ + fcu）、HKUST-1（BTC + Cu 桨轮 + tbo）、IRMOF-8（2,6-NDC + Zn₄O）、IRMOF-10（BPDC + Zn₄O），以及 DOBDC/TDC/DM-BDC 的类似物。

**结论：这批是“已知骨架 × 新取代配体”，不是“全新骨架家族”。** 骨架眼熟是固定节点/拓扑路线的预期结果，也是可合成性的来源；但框架级 novelty 必须另外用 MOFid 对 CoRE/BW-DB 比对，不能只看配体是否在 CoRE 里。

## Novelty 核查（CoRE MOF 2024）

`novelty_core.py` 用 CoRE 2024 的 MOFid-v1 字符串做框架级比对：把每条 MOFid 拆成「金属节点元素集合 + 有机配体 InChIKey 骨架集合 + 拓扑 + catenation」，生成结构用同样的键去查 CoRE。

- CoRE 2024：9,835 条，8,627 条可用（1,208 条没有 MOFid 标记）；MOFid 拓扑 `ERROR/unknown` 的条目用 CoRE 自己的 topology 列兜底。
- 268 个候选：
  - **7 exact**：全部是未取代的 known control（MOF-5、UiO-66、DOBDC pcu、IRMOF-8、IRMOF-10、HKUST-1 等）；
  - **3 topo+ligand**：同拓扑同配体、金属不同（V0006_pcu、V0038_pcu、V0063_pcu）；
  - **4 metal+ligand**：同金属同配体、拓扑不同（V0000_nbo、V0010_pcu、V0052_pcu、V0063_fcu）；
  - **254 no_match**：在 CoRE 2024 的任何层级都没有命中（最终互斥分层；256 是 fallback 拓扑前的旧数）。
- **所有 CO₂ 头部候选（V0164、V0039、V0035、V0032、V0033、V0058 等）都在 no_match 组。**

**这不是“已确认全新”。** CoRE 2024 不是全集，而且一些 known control（如 DOBDC fcu/nbo、TDC nbo）本身也不在 CoRE 2024 里；absence 不等于 novel。要确认还需要 CoRE 2019（21,830 个 CIF，服务器上有）、BW-DB、CSD 和针对性文献检索。

输出：`novelty_core.csv`、`scored_full_novelty.csv`。

## Nexerra 接入（2026-10-23）

Nexerra-R1 的 VAE 推理已接入，链路为：

```
Nexerra [Lr] SMILES
  → nexerra_to_variants.py（[Lr] → C(=O)([O-])，RDKit/anchor_rules 过滤）
  → build_candidates.py（PORMAKE 组装）
  → Zeo++ G + PACMOF Chem → 代理打分 → 适用域 → CoRE novelty
```

- **ScafDesign**：100/1000 samples 各 5 个 linker；全是三齿羧酸，但 tbo 组装 0/5 通过（臂被生成为柔性二烯链）。
- **Direct Design（BDC 种子）**：500 个原始 SMILES → 14 个唯一合法二齿配体 → 42 次组装 → **9 个 CIF**（pcu 4、nbo 3、fcu 2）。
- **打分**：7 个域内、2 个域外；3 个预测 log10 S_CO2 > 0（S_CO2 > 1）。最高 N0003_nbo 0.364，但其配体是 **TDC（已知）**；N0008_nbo 0.307 是非芳香累积双键结构，化学上可疑。
- **Novelty**：0 exact、1 topo+ligand（TDC pcu）、1 metal+ligand（TDC fcu）、7 no match。
- **注意**：`[Lr]` 必须替换成 `C(=O)([O-])`，不能写成 `C(=O)[O-]` 或 `C(=O)O`（连接点会错）。
- **刚性过滤**：`nexerra_to_variants.py` 默认要求至少一个芳环、非芳香环只能 5/6 元且无累积双键/sp 原子、可旋转键 ≤ 6；变体 ID 用 `--prefix` 区分批次。
- **BDC 更大批次**：500 原始 → 6 个唯一合法二齿配体 → 4 个 CIF（TDC 的 pcu/fcu/nbo + 苯基-BDC pcu）；1000（delta 0.15）→ 10 个唯一 → 3 个 CIF，**全是 BDC**。模型在 BDC 种子下收敛到已知化学。
- **FlowDesign**：需要 flow checkpoint（63 MB）+ latent bank（423 MB）；Zenodo 当前限速约 15 KB/s，暂不可行。
- **定位**：这是集成验证批次，不是可用候选池；需要换非 BDC 的刚性种子、缩小 delta，或改用 BBA inpainting，并对 top 候选做 Widom/GCMC 验证。
- **FlowDesign**：flow checkpoint（63 MB）+ latent bank（423 MB），Zenodo 限速约 15 KB/s，短期不可行。
- **BBA 核查**：`OAReactDiff` 是化学反应过渡态扩散框架，不是预训练 MOF 生成器；Zenodo 15308950 是 BBA 数据集（`mof-1n1e.pkl` 498 MB），无现成 MOF 权重，需要自行训练/适配。
- **二苯并噻吩批次**：500 samples，delta 0.05 → 500 个原始 SMILES → 刚性过滤 **0/500**（全部小非芳香环），无合法配体/CIF。
- **Nexerra 结论**：推理/转换/过滤/组装/打分链路已通，但预训练模型在测试过的种子/模式下产出的候选要么是已知化学（BDC/TDC），要么被化学/几何过滤全部拒绝。继续生成端需要 BBA 自训练或换模型。

## 下一步

1. 等 PACMOF pol 完成，用同一套流程给这批候选补 CO₂/N₂/O₂/CO 打分；
2. 抽 40–60 个新批次候选跑 Widom，验证「新批次 → 扩训 → 打分」闭环；
3. 加 MOFid 框架级 novelty 门槛；`known_control` 单独统计，不计入生成命中率；
4. 下一批生成换掉 BDC/NDC/BPDC/BTC 这些教科书种子，改用更少见的骨架/多取代/唑吡啶配体，或直接接 Nexerra/BBA；
5. 把生成器换成 Nexerra/BBA 时，只替换 `variants.csv` 的来源，后续链路不变。
