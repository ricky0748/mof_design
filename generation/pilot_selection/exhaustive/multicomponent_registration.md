# 多组分 GCMC / 过程条件（2026-10-30）

- 候选文件：`generation/pilot_selection/exhaustive/multicomponent_candidates.csv`，sha256 `bc839883f16d8dba13a4fbc4bcca10c3097421c7045f7f0a9bddfb20a667de09`
- 问题：二元普查的头部命中结构，在加入 N₂/CH₄ 与改变温压后，是否仍保持选择性与容量？
- 候选来源：737 普查已完成结果中，按 logS_CO2 取设计臂前 10、已知库臂前 5（均为冻结判定下的命中结构）。
- 组成（4 组分，ppm 级为代理值）：SiH₄ 0.997、CO₂ 0.001、N₂ 0.001、CH₄ 0.001。
- 条件矩阵：298 K/1 bar（与二元基线直接对照）、273 K/1 bar、323 K/1 bar、298 K/5 bar。
- 精算：PACMOF/UFF/Ewald；30k cycles / 5k init；单位胞沿用对应二元运行。
- 判定（沿用冻结标准）：logS_CO2 ≥ 0.3、q_SiH4 ≤ 1.5、q_CO2 ≥ 0.001；并记录 S_N2、S_CH4。
- 预算：15 候选 × 4 条件 = 60 个 GCMC。
- 分析：与二元基线比较 S_CO2/q_SiH4 的变化；Spearman 排名相关；各条件下命中集合的变化。
- 登记时间：2026-10-30T06:46:59.385799+00:00
