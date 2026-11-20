# 全新生成批次：seed719

[预登记](PROTOCOL.md)：固定200条序列，排除既有40连接体后最多选20种，原生与构象种子7/19固定pcu组装三臂。输出和预处理缓存隔离，显式data_idx映射，启用冻结哈希和计算签名。

服务器目录：/share/rickyswork/ai_mof/generation/linker_framework_fresh_20261113。阶段顺序为生成冻结、序列采样、选样冻结、原生坐标预测、双种子组装冻结、BDC校准、正式弛豫、官方MOFid、最终CIF复算报告。

不补采样、不补构象，失败保留实际n分母；两种子都通过和至少一种通过分开统计。DAO-P保持后续备选。


## 已完成

实际冻结18种新连接体、54次正式弛豫和2次控制；A/U7/U19联合终点0/18、16/18、18/18，16种双种子均通过。完整证据见results/REPORT.md、AUDIT.json及comparison.png。结果包排除检查点权重链接，来源与哈希保留；本地补充片段分层与配位诊断由finalize_local.py生成。


## 后续评价源代码修订

identity_checks.py提供linker-type-set-v2：严格连接体类型集合及预期拓扑校验。eval_helpers与后续report_fresh并列记录历史joint及strict_joint，BDC校准使用严格终点；9项测试包括原34个已接受U输出及后续真实副片段反例。历史results不变，后续计算使用新目录。六案例几何预处理未采纳，详见../steric_precondition/DECISION.md。
