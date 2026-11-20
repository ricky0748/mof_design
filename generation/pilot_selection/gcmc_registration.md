# 命中候选完整 GCMC 登记（2026-10-26）

- 候选：两轮 Widom 试点的 10 个命中结构（见下表）。
- 条件：298 K，1 bar，CO₂ 1000 ppm，SiH₄ 平衡；PACMOF 电荷 + UFF + Ewald；30,000 cycles / 5,000 initialization；超胞沿用对应 Widom pol 输入。
- 判定标准（运行前冻结）：
  - `GCMC logS_CO2 >= 0.3`（S_CO2 >= 2）；
  - `q_SiH4 <= 1.5 mol/kg`（容量/产品损失约束）；
  - 同时记录 q_CO2、S_N2、S_CH4。
- 说明：这是对已选命中候选的完整 GCMC 验证，不是新一轮候选选择；Widom 结果和 CoRE 2024 novelty 状态一并记录，运行后不得修改判定标准。

## 候选与运行前信息

| 候选 | 组 | 拓扑 | Widom logS_CO2 | 代理 pred_S_CO2 | CoRE 2024 |
|---|---|---|---|---|---|
| V0157_nbo | initial | nbo | 0.475 | 0.499 | no_match |
| V0031_nbo | initial | nbo | 0.406 | 0.486 | no_match |
| V0041_nbo | initial | nbo | 0.570 | 0.486 | no_match |
| V0034_nbo | initial | nbo | 0.332 | 0.473 | no_match |
| V0023_nbo | initial | nbo | 0.466 | 0.471 | no_match |
| V0006_nbo | feedback | nbo | 0.478 | 0.481 | no_match |
| V0048_nbo | feedback | nbo | 0.442 | 0.473 | no_match |
| V0047_nbo | feedback | nbo | 0.466 | 0.466 | no_match |
| V0067_nbo | feedback | nbo | 0.389 | 0.461 | no_match |
| V0024_nbo | feedback | nbo | 0.468 | 0.462 | no_match |

- 配体 SMILES 见 `generation/pilot_selection/selected.csv` 与 `feedback_selected.csv`。
- 登记时间：2026-10-26（UTC）。
