# 同预算命中密度对照：扩展登记（2026-10-28）

- 候选文件：`generation/pilot_selection/fair_compare_extension_selected.csv`，sha256 `edf68471c8a331c36845656096577742fac6043250d4a30c773330e6a2876363`
- 背景：首轮每臂 5 个已完成（known 0/5，generated 5/5）。本扩展按**同一模型、同一 held-out 划分、同一 UCB 排名**取每臂第 6–10 名，追加 5 个/臂。
- 透明度：扩展决定是在看到首轮 5 个结果之后做出的；因此新 5 个是前瞻性样本，但合并后的 10 个/臂包含已观察样本。报告分别给出 **new-5** 和 **combined-10** 的命中率。
- 模型/协议/护栏不变：G+Chem 集成；D_fs ≥3.3 Å、AV≥0.02；UCB=mean+1.0×std。
- GCMC 条件不变：298 K、1 bar、CO₂ 1000 ppm、SiH₄ 平衡；PACMOF/UFF/Ewald；30k/5k。
- 命中标准不变：GCMC logS_CO2 ≥0.3、q_SiH4 ≤1.5、q_CO2 ≥0.001。
- 登记时间：2026-10-28（UTC）

## 新增候选

| 臂 | 候选 | pred_mean | pred_std | UCB |
|---|---|---|---|---|
| known_holdout | SENWEP | 0.337 | 0.052 | 0.389 |
| known_holdout | CAXWIJ | 0.344 | 0.025 | 0.369 |
| known_holdout | ATOXEN | 0.264 | 0.100 | 0.363 |
| known_holdout | FUDQIF | 0.223 | 0.116 | 0.339 |
| known_holdout | LACJAC | 0.233 | 0.023 | 0.256 |
| generated | V0056_nbo | 0.408 | 0.013 | 0.420 |
| generated | V0015_nbo | 0.410 | 0.008 | 0.418 |
| generated | V0026_nbo | 0.405 | 0.007 | 0.412 |
| generated | V0021_nbo | 0.390 | 0.018 | 0.408 |
| generated | V0005_nbo | 0.395 | 0.007 | 0.402 |
