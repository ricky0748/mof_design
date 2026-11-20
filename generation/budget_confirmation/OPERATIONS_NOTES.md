# 实现与落盘偏差记录

1. 原生预测计划8条/批，实际官方predict_dataloader使用batch_size.predict=20；写入的顶层max_batch_size未被读取，worker4生效。偏差在CIF转换/MACE前登记于results/RUNTIME_DEVIATIONS.json，未重启采样、未换样、未修改MACE预算。当前工作代码修正了未来批大小键路径；results中的原冻结代码保留实际运行版本。
2. 冻结启动脚本最后有CR空行，所有报告、审计与ALL_DONE产生后才返回非零。results/INDEPENDENT_REVIEW.json记录此项，模型与科学计算阶段均正常结束；当前工作脚本已归一化LF。
3. A300_B04、S300_B25的CIF复读合并了重叠位点，距离/分量数与内存有差异，均仍为失败。原子数核对使用显式CIF位点数，最终统计未改变。
4. 最终交付26个单构象候选的输出哈希已核对，26个均在预算内收敛。原始结果包保持服务器快照，后续本地结项报告/图/候选包为该快照的可追溯派生产物。
