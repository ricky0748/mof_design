# 全池普查：设计候选 vs 已知库（GCMC 命中密度）

- 候选文件：`generation/pilot_selection/exhaustive/campaign_selected.csv`，sha256 `e1756068ba682fb48bacaaaf19c26714ec4451609737fef243bf13243a2cb160`
- 问题：在同一条 GCMC 条件下，**整个**设计候选池与**整个**合格已知库的命中密度各是多少？
- 与 UCB 小样本对照的区别：不做代理选择、不抽样；两臂所有合格结构全部精算。
- 设计臂：218 个规则式候选（268 个合格 CIF 中，排除已验证 15、试点 10、反馈 5、known control 17 个后，通过护栏者；含 proxy 165 + gcmc 53 两种路由）。
- 已知臂：519 个 CRAFTED MOF（690 个中通过同一护栏者）。
- 护栏（两臂相同）：D_fs ≥ 3.3 Å、AV_Volume_fraction ≥ 0.02。
- 精算条件：298 K、1 bar、CO₂ 1000 ppm + SiH₄ 平衡；PACMOF/UFF/Ewald；30k cycles / 5k init；与既往一致。
- 判定（运行前冻结）：GCMC logS_CO2 ≥ 0.3 **且** q_SiH4 ≤ 1.5 mol/kg **且** q_CO2 ≥ 0.001 mol/kg。阈值敏感性（q_SiH4 ≤ 2.0 / 2.5）另行报告。
- 预算：共 737 个 GCMC；不追加、不中途看结果改协议。
- 说明：设计臂的结构来自规则式枚举 + PORMAKE 组装 + PACMOF 电荷；已知臂来自 CRAFTED。两臂均未使用代理分数做取舍，代理预测仅用于事后校准分析。
- 登记时间：2026-10-29T08:45:40.240175+00:00
