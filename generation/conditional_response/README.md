# 目标条件响应与分离性能主线

协议：[PROTOCOL.md](PROTOCOL.md)；性能配置：[PERFORMANCE_PROTOCOL.md](PERFORMANCE_PROTOCOL.md)；运行偏差：[OPERATIONS_NOTES.md](OPERATIONS_NOTES.md)。

服务器独立目录：`/share/rickyswork/ai_mof/generation/conditional_response_20261116`。原预算确认与收敛敏感性结果不覆盖。

## 已完成的生成响应

| 目标 | 序列随机种子 | 生成条数 | 当前路线合格序列 | 唯一合格连接体 | 抽取种类 |
|---|---:|---:|---:|---:|---:|
| 2 | 1601 | 600 | 4 | 4 | 4 |
| 5 | 1601 | 600 | 118 | 49 | 15 |
| 2 | 1602 | 600 | 1 | 1 | 1 |
| 5 | 1602 | 600 | 112 | 46 | 15 |

两个配对种子均600/600原序列改变，合格连接体身份交集均0。35条组成员对应29种唯一连接体；低目标不足15按原协议全取，不追加采样。该漏斗衡量单有机连接体类型/二羧酸固定组装路线的兼容性，整体模型化学质量需要看独立分层指标。

条件标签为CO₂工作容量；项目性能为SiH₄/CO₂分离，分别解释条件响应和迁移效果。训练prop最小−0.199905、最大5.115154、99%分位2.35803，目标5接近训练上沿。

## 运行与状态

`generate.py`完成四组生成；`pipeline.sh`依次抽样、组装、两阶段优化、MOFid和结构审计；`performance_pipeline.sh`在结构审计和v3控制通过后执行PACMOF、双种子Henry/GCMC与结果审计。

真实完成标记依次为GENERATION_DONE、STRUCTURES_DONE、STRUCTURE_ANALYSIS_DONE、PERFORMANCE_RUNS_DONE、PERFORMANCE_ANALYSIS_DONE。启动脚本不等于阶段完成。逐结构最终记录为records/S_C*.json（不含.progress.json）；逐步轨迹包含coarse/fine两阶段。

吸附接口控制performance_preflight_v3已通过电荷/几何检查及100cycle Widom/GCMC；控制数值不纳入四组性能统计。v1/v2的失败记录保留。性能计算使用服务器已有python3/sklearn1.7.2环境，结构优化沿原MACE环境。

2026-11-17核查：96/96正式Henry/GCMC全部完成并解析，11月16日16:58已汇总，性能及全链路审计通过。目标2/5的GCMC选择性中位数0.867/0.848，最佳值0.968/1.641；条件改变候选与产率，整体选择性未提高，目标5中有5/20候选S_CO2>1。详细结果见[完成报告](REPORT.md)。
