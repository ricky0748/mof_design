# 生产端选择试点结果

2026-10-23 · 登记文件 `registration.md` · 结果 `results.csv` · 合并标签 `pilot_merged.csv`

## 设置

- 候选池：268 个规则式候选；排除已用于 Widom/GCMC 验证的 15 个、17 个 known control，仅保留 `action=proxy` 的候选。
- 选择：`proxy_top5` = `pred_S_CO2` 最高的 5 个；`random5` = 其余候选中 `random_state=42` 随机 5 个。
- 条件：298 K，1 bar，CO₂ 1000 ppm，SiH₄ 平衡；PACMOF 电荷 + UFF + Ewald；Widom np+pol，5000 cycles。
- 判定标准（运行前冻结）：`logS_CO2 >= 0.3`（S_CO2 >= 2）记为命中。
- 候选文件 sha256：`6c48729a0afb6475e742ec615001fbb5656f934d8b24939f0ef80f770da4aa3e`。
- 运行：np 10/10、pol 10/10，0 超时。

## 结果

| 候选 | 组 | 拓扑 | 预测 logS_CO2 | 真实 logS_CO2 | 命中 |
|---|---|---|---|---|---|
| V0157_nbo | proxy_top5 | nbo | 0.499 | 0.475 | ✓ |
| V0031_nbo | proxy_top5 | nbo | 0.486 | 0.406 | ✓ |
| V0041_nbo | proxy_top5 | nbo | 0.486 | 0.570 | ✓ |
| V0034_nbo | proxy_top5 | nbo | 0.473 | 0.332 | ✓ |
| V0023_nbo | proxy_top5 | nbo | 0.471 | 0.466 | ✓ |
| V0015_pcu | random5 | pcu | 0.018 | 0.027 | ✗ |
| V0053_nbo | random5 | nbo | 0.392 | 0.368 | ✓ |
| V0042_pcu | random5 | pcu | 0.056 | −0.079 | ✗ |
| V0140_fcu | random5 | fcu | −0.042 | −0.344 | ✗ |
| V0013_pcu | random5 | pcu | 0.028 | 0.123 | ✗ |

| 组 | n | 命中 | 真实 logS_CO2 中位数 | 预测中位数 |
|---|---|---|---|---|
| proxy_top5 | 5 | **5** | 0.466 | 0.486 |
| random5 | 5 | **1** | 0.027 | 0.028 |

- 代理预测 vs 真实 logS_CO2：**ρ = 0.855，MAE = 0.090**（n=10）。
- Fisher 单侧检验（5/5 vs 1/5）p ≈ 0.024；样本很小，只作方向性证据。

## 解读

1. **目标引导的选择在真实 Widom 标签上表现出富集**：proxy_top5 全部达到 `logS_CO2 ≥ 0.3`，random5 只有 1 个。
2. **代理的排序与真实值一致**：ρ 0.855、MAE 0.090，和之前 15 个候选验证的 ρ 0.789/MAE 0.097 同一量级。
3. **命中集中在 nbo/Cu 桨轮家族**：proxy_top5 全是 nbo；random5 唯一的命中 V0053_nbo 也是 nbo（且预测 0.392，属于随机组里的高分）。pcu/fcu 的随机候选全部未达标。
4. **不能过度解读**：n=10；阈值和候选池是预先冻结的，但随机组包含一个高代理分候选；本轮只做 Widom，不含完整 GCMC/容量；候选仍是已知骨架上的取代变体，novelty 未确认。

## 结论与下一步

- 结论：**代理可以把生产池里更可能达标的候选排到前面**，支持继续做反馈批次，而不是停在固定枚举后排序。
- 下一步（按 NEXT_STEPS）：
  1. 用这 10 个真实标签更新代理/选择器；
  2. 从剩余候选池按 UCB/EI 选下一批 5–10 个，登记后跑 Widom；
  3. 比较“初始批次 vs 反馈批次 vs 随机”的命中率；
  4. 对命中候选做完整 GCMC（容量/SiH₄ 损失）和 novelty 核查。

## 反馈批次结果（2026-10-26）

用首轮 10 个真实标签更新 G+Chem 集成（5 个 LightGBM；组装/试点权重 20），从剩余 in-domain 池按 UCB = mean + 1.0 × std 选 5 个，登记后跑 Widom：

| 候选 | 拓扑 | pred_mean | pred_std | UCB | 真实 logS_CO2 | 命中 |
|---|---|---|---|---|---|---|
| V0006_nbo | nbo | 0.481 | 0.008 | 0.489 | 0.478 | ✓ |
| V0048_nbo | nbo | 0.473 | 0.015 | 0.488 | 0.442 | ✓ |
| V0047_nbo | nbo | 0.466 | 0.015 | 0.481 | 0.466 | ✓ |
| V0067_nbo | nbo | 0.461 | 0.011 | 0.473 | 0.389 | ✓ |
| V0024_nbo | nbo | 0.462 | 0.007 | 0.469 | 0.468 | ✓ |

反馈批次：**5/5 命中**，真实 logS_CO2 中位 0.466；pred_mean vs 真实 ρ 0.600、MAE 0.023（n=5）。

### 三轮对比

| 组 | n | 命中 | 真实 logS_CO2 中位 | 预测 MAE |
|---|---|---|---|---|
| 初始 proxy_top5 | 5 | 5 | 0.466 | 0.090 |
| 初始 random5 | 5 | 1 | 0.027 | — |
| 反馈（UCB，更新后） | 5 | 5 | 0.466 | 0.023 |

- 目标引导的选择在首轮和反馈轮都达到 5/5，随机只有 1/5；**代理用于 triage 的方向性结论成立**。
- 反馈更新把 MAE 从 0.090 降到 0.023，改善了校准；命中率已是 5/5，无法再提升。
- 反馈 5 个全是 nbo；命中仍集中在 nbo/Cu 桨轮家族。
- 样本很小（n=5/5/5），只做 Widom，不含完整 GCMC/容量；候选仍是已知骨架上的取代变体，novelty 未确认。

### 追加结论

- 目标引导的生产选择已经从“固定枚举后排序”推进到“用真实反馈更新代理、再选下一批”，并保持 5/5 命中。
- 下一步应把命中候选（V0006/V0048/V0047/V0067/V0024，以及首轮的 V0157 等）做完整 GCMC（容量/SiH₄ 损失）和 CoRE/文献 novelty 核查，再决定是否进入合成评估。

## 完整 GCMC 终判（2026-10-26）

条件：298 K、1 bar、CO₂ 1000 ppm、SiH₄ 平衡；PACMOF 电荷 + UFF + Ewald；30k cycles / 5k init。判定标准（运行前冻结）：`GCMC logS_CO2 ≥ 0.3` 且 `q_SiH4 ≤ 1.5 mol/kg`。

| 候选 | 拓扑 | GCMC logS_CO2 | S_CO2 | q_SiH4 (mol/kg) | q_CO2 (mol/kg) | 通过 |
|---|---|---|---|---|---|---|
| V0041_nbo | nbo | 0.592 | 3.91 | 1.113 | 0.00436 | ✓ |
| V0024_nbo | nbo | 0.512 | 3.25 | 0.782 | 0.00279 | ✓ |
| V0023_nbo | nbo | 0.510 | 3.24 | 0.815 | 0.00302 | ✓ |
| V0006_nbo | nbo | 0.502 | 3.18 | 0.880 | 0.00310 | ✓ |
| V0047_nbo | nbo | 0.487 | 3.07 | 0.956 | 0.00293 | ✓ |
| V0048_nbo | nbo | 0.448 | 2.81 | 1.001 | 0.00281 | ✓ |
| V0031_nbo | nbo | 0.434 | 2.72 | 1.159 | 0.00315 | ✓ |
| V0157_nbo | nbo | 0.422 | 2.64 | 0.827 | 0.00219 | ✓ |
| V0067_nbo | nbo | 0.397 | 2.49 | 0.896 | 0.00224 | ✓ |
| V0034_nbo | nbo | 0.374 | 2.36 | 0.921 | 0.00218 | ✓ |

- **10/10 通过**：GCMC logS_CO2 0.374–0.592（S_CO2 2.36–3.91）；q_SiH4 0.782–1.159 mol/kg（全部 ≤1.5）；q_CO2 0.0022–0.0044 mol/kg。
- Widom vs GCMC：ρ 0.758，MAE 0.029（n=10），与之前的验证一致。
- CoRE 2024 novelty：10/10 **no_match**；仍需 CoRE 2019/BW-DB/CSD/文献确认。

### 最终结论

- 两轮目标引导选择（proxy_top5 和反馈 UCB）选出的 10 个候选，在 Widom 和完整 GCMC 下都通过 CO₂ 选择性 + 容量约束；随机对照只有 1/5 通过 Widom 阈值。
- 这支持“代理 + 反馈选择”作为生产端的候选 triage 工具；但样本小（n=10）、全部 nbo、全部已知骨架取代变体，novelty 未确认、无实验验证。
- 下一步：对 V0041/V0024/V0023/V0006 等头部做 CoRE 2019/BW-DB/CSD + 文献 novelty 硬核查，再做合成可及性（采购/文献路线 + SAscore/SCScore），最后才是实验评估。

## Novelty 与可合成性核查（2026-10-26）

### 数据库比对

| 数据库 | 范围 | 头部 4 个结果 |
|---|---|---|
| CoRE MOF 2024 | 9,835 条 MOFid 字符串（8,627 可解析） | 10/10 候选 **no_match** |
| CoRE 2019 | 21,830 个 CIF；按 Cu/羧酸/元素/体积过滤后 1,049 个 | **0 匹配**（loose StructureMatcher：ltol 0.3、stol 0.5、angle 10、primitive+supercell） |
| CSD MOF Collection | 15,906 个实验 CIF；过滤后 1,627 个 Cu/羧酸结构 | **0 匹配**（同一 matcher 设置） |

### SAscore（配体）

| 候选 | 配体 | SAscore |
|---|---|---|
| V0006_nbo | 2-aminoterephthalic acid | 1.76 |
| V0041_nbo | 2-amino-5-methoxyterephthalic acid | 1.93 |
| V0023_nbo | 2-amino-4-fluoroterephthalic acid | 2.01 |
| V0024_nbo | 2-amino-5-fluoroterephthalic acid | 2.18 |
| 其余 6 个 | 甲基/氰基/羟基/CF3/噻吩取代 | 2.05–2.42 |

SAscore 全部 < 2.5，属于低复杂度、易合成的一类；但 SAscore 只是辅助指标，不证明 MOF 可合成。

### 文献初查

- 2-aminoterephthalic acid（V0006 的配体）在 Cu 配位网络/Cu-MOF 中有报道；搜索到的明确 paddlewheel 例子用的是另一种氨基三羧酸 H3ATTCA，未找到“2-ATA + Cu paddlewheel + nbo”的明确先例。
- 2-amino-5-methoxy / 2-amino-4/5-fluoro terephthalic acid 没有搜到直接的 MOF 报道；需要更针对性的 CSD/文献检索。

### 结论与边界

- 头部候选在 CoRE 2024 / CoRE 2019 / CSD 实验库的结构级比对中都没有匹配；这是一个**有利的新颖性信号**。
- 但 **0 匹配不等于全球首创**：CSD 结构可能带客体/部分占据，StructureMatcher 可能漏配；未查 BW-DB 全库和针对性文献；V0006 的配体本身是已知化合物，Cu-2-ATA 配位网络已有报道。
- 可合成性只做到 SAscore 和初步文献；配体采购/文献路线、目标框架的合成先例都还没有逐条确认。
- 在完成针对性 CSD/文献检索和合成评估之前，不能对外称“全新 MOF”，也不能承诺可合成。

### 合成可及性初步评估

详见 `synthesis_assessment.md`。结论：

- **V0041_nbo** 第一优先：GCMC 最高（logS_CO2 0.592），配体 2-amino-5-methoxyterephthalic acid 有文献水解合成路线，三个数据库无结构匹配。
- **V0067_nbo** 第二：配体 3-methylthiophene-2,5-dicarboxylic acid 可商购（CAS 89677-40-7），成本低。
- **V0006_nbo** 对照：配体 2-aminoterephthalic acid 可商购，Cu(BDC-NH2) 桨轮化学有报道，但 novelty 最低。
- V0023/V0024/V0047/V0048：氟基/氰基取代配体需定制合成，暂缓。
- 边界：配体可采购/有路线不等于目标 MOF 能结晶；未联系供应商、未询价、未提交实验。建议的实验搜索范围仅供内部讨论，不能从 CIF 承诺配方。
