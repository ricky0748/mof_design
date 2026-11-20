# 预测登记：生产端选择试点（2026-10-23）

- 候选文件：`generation/pilot_selection/selected.csv`，sha256 `6c48729a0afb6475e742ec615001fbb5656f934d8b24939f0ef80f770da4aa3e`
- 选择规则：在 268 个候选中排除已用于 Widom/GCMC 验证的 15 个、排除 17 个 known control，仅保留 `action=proxy` 的候选；`proxy_top5` = `pred_S_CO2` 最高的 5 个；`random5` = 其余候选中 `random_state=42` 随机 5 个。
- 模型版本：G+Chem（CRAFTED 690 + 132 个组装标签，权重 20；PACMOF 电荷特征）。
- 条件：298 K，1 bar，CO₂ 1000 ppm，SiH₄ 平衡；PACMOF 电荷 + UFF + Ewald；Widom np+pol，5000 cycles。
- 预测值：见 `selected.csv` 的 `pred_S_CO2`（log10 选择性）。
- 判定标准（运行前冻结）：`logS_CO2 >= 0.3`（即 S_CO2 >= 2）记为命中；比较 `proxy_top5` 与 `random5` 的命中数。容量/完整 GCMC 不在本轮判定内。
- 说明：这是前瞻性 Widom 测试；12 个历史 GCMC 结构不进入本轮。登记后候选与判定标准不得修改。
- 登记时间：2026-10-23T08:22:35Z

## 候选

| 候选 | 组 | 拓扑 | pred_S_CO2 | 配体 |
|---|---|---|---|---|
| V0157_nbo | proxy_top5 | nbo | 0.499 | `O=C(O)c1ccc2cc(C(=O)O)c(C(F)(F)F)cc2c1` |
| V0031_nbo | proxy_top5 | nbo | 0.486 | `Cc1c(C(=O)O)ccc(C(=O)O)c1N` |
| V0041_nbo | proxy_top5 | nbo | 0.486 | `COc1cc(C(=O)O)c(N)cc1C(=O)O` |
| V0034_nbo | proxy_top5 | nbo | 0.473 | `Nc1c(C(=O)O)ccc(C(=O)O)c1O` |
| V0023_nbo | proxy_top5 | nbo | 0.471 | `Nc1cc(C(=O)O)c(F)cc1C(=O)O` |
| V0015_pcu | random5 | pcu | 0.018 | `Cc1c(O)c(C(=O)O)cc(O)c1C(=O)O` |
| V0053_nbo | random5 | nbo | 0.392 | `Cc1cc(C(=O)O)c(C)c(F)c1C(=O)O` |
| V0042_pcu | random5 | pcu | 0.056 | `COc1cc(C(=O)O)cc(N)c1C(=O)O` |
| V0140_fcu | random5 | fcu | -0.042 | `O=C(O)c1cc(Cl)c2cc(C(=O)O)ccc2c1` |
| V0013_pcu | random5 | pcu | 0.028 | `O=C(O)c1cc(O)c(C(=O)O)c(Cl)c1O` |
