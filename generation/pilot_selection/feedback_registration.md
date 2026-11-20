# 反馈批次登记（2026-10-26）

- 候选文件：`generation/pilot_selection/feedback_selected.csv`，sha256 `3f58c77a74e7f83989d57fe19a5f8b40a93306da2cb40ea46938c34092049f35`
- 模型：G+Chem 集成（5 个 LightGBM；CRAFTED + 132 个组装标签 + 10 个试点标签；组装/试点权重 20）
- 选择规则：在剩余 in-domain 候选池中排除已验证 15 个、试点 10 个、known control；按 UCB = mean + 1.0 × std 选前 5 个。
- 条件：298 K，1 bar，CO₂ 1000 ppm，SiH₄ 平衡；PACMOF 电荷 + UFF + Ewald；Widom np+pol，5000 cycles。
- 判定标准（运行前冻结）：`logS_CO2 >= 0.3`（S_CO2 >= 2）记为命中；与初始 proxy_top5 的 5/5、random5 的 1/5 比较。
- 登记时间：2026-10-26（UTC）

## 候选

| 候选 | 拓扑 | pred_mean | pred_std | UCB | 配体 |
|---|---|---|---|---|---|
| V0006_nbo | nbo | 0.481 | 0.008 | 0.489 | `Nc1cc(C(=O)O)ccc1C(=O)O` |
| V0048_nbo | nbo | 0.473 | 0.015 | 0.488 | `N#Cc1cc(C(=O)O)cc(N)c1C(=O)O` |
| V0047_nbo | nbo | 0.466 | 0.015 | 0.481 | `N#Cc1cc(C(=O)O)c(N)cc1C(=O)O` |
| V0067_nbo | nbo | 0.461 | 0.011 | 0.473 | `Cc1cc(C(=O)O)sc1C(=O)O` |
| V0024_nbo | nbo | 0.462 | 0.007 | 0.469 | `Nc1cc(C(=O)O)cc(F)c1C(=O)O` |
