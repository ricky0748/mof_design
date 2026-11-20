# 同预算命中密度对照（2026-10-28）

- 候选文件：`generation/pilot_selection/fair_compare_selected.csv`，sha256 `e91f6577051ff4cde2ece6b68f631916a5304c71dd37ceed9386b4c9ee48df45`
- 问题：在同等 GCMC 预算下，生成池的选择命中率是否高于 held-out 已知库？
- 已知库：CRAFTED 690，固定随机种子 2027 抽 100 个 held-out；训练集不含这些结构。
- 生成池：268 个规则式候选中排除已验证 15 个、试点 10 个、反馈 5 个、known control 17 个。
- 模型：G+Chem 集成（5×LightGBM；CRAFTED train + 132 组装 + 15 个生成标签；权重 20）。
- 适用域/孔径护栏：D_fs ≥ 3.3 Å 且 AV_Volume_fraction ≥ 0.02；两臂相同。目的：排除极小孔（D_fs 2.4–2.7 Å）造成的“孔道阻塞假高选择性”（此前试选曾出现 logS_CO2 ≈ 14.7 的记录，已作废，未跑 GCMC）。
- 选择：两个池各按 UCB = mean + 1.0×std 选前 10 个；不做池间调参。
- 精算：298 K、1 bar、CO₂ 1000 ppm、SiH₄ 平衡；PACMOF/UFF/Ewald；30k cycles / 5k init。
- 判定：GCMC logS_CO2 ≥ 0.3、q_SiH4 ≤ 1.5 mol/kg、**q_CO2 ≥ 0.001 mol/kg**（容量地板）；比较两臂命中率。
- 预算：每个臂 10 个 GCMC，共 20 个；不追加临时候选。
- 说明：已知库 held-out 的标签只用于评估，不参与选择；生成池的 15 个已有标签参与训练，但已从池中排除。
- 登记时间：2026-10-29T06:21:23.067099+00:00
