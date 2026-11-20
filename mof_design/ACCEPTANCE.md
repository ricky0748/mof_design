# v0.1 验收记录（2026-11-17）

交付：可安装Python/命令行模块，统一任务入口、EGMOF默认后端、MOFFlow-2连接体探索、场景登记、约束检查、验证、状态/取消/超时与候选包。本轮未训练新模型或继续气体分离研究。

## 本地测试与打包

`python -m unittest discover -s tests -p test_mof_design.py -v`：20/20通过。覆盖场景/引擎匹配、未知字段、有限目标值、预算、元素冲突、拓扑与身份验证、规范化幂等、重复/失败提案分母、路径边界、CIF损坏检测、任务隔离、终态拒绝重跑、子进程预算、异步取消及便携包原任务ID。

单元测试使用的假提案适配器与下方真实模型验收分开。Wheel构建并在独立安装目录导入通过；控制端不强制安装模型依赖。

最终源代码又在Linux发布目录`/share/rickyswork/ai_mof/generation/design_module_v01_release_20261117`完成20/20测试及runtime配置预检；Windows与Linux日志分别为交付目录的tests.log、tests.linux.log。最终目录与下方原生模型验收快照分开保留，全部GPU任务已结束。

## 真实端到端验收

服务器目录`/share/rickyswork/ai_mof/generation/design_module_v01_20261117`。统一submit/status接口；EGMOF上游提交`5cc217defa6a0225af8fafb364a6fb7b764ceea2`，使用已有权重。

| 模式 | 任务ID | 实际尝试 | 交付 | 执行墙钟 | 结果 |
|---|---|---:|---:|---:|---|
| EGMOF | design_6e6ab023c5164c0f | 3（上限8） | 2份CIF | 673.0秒 | completed |
| MOFFlow-2探索 | design_f0c4b4c54c1f4389 | 2（上限6，原序列100） | 2份CIF | 261.0秒 | completed |

均开启两阶段MACE精修和MOFid。EGMOF的C0002因MOFid未完整识别而拒绝，保留原因；交付C0001与C0003，来源分别为`mot+N417+N223+E38+E45`与`pcu+N16+E84`。探索模式交付两个连接体的pcu/N16框架，目标连接体类型集合及pcu检查通过。

服务端两份审计均通过：请求/场景、主要资产与模块源代码哈希、计数、最终CIF哈希、ZIP CRC和包内CIF字节、记录中的几何/收敛/完整身份。下载后两份便携包也通过本地审计；没有独立重算力或能量。

原生模型验收的源快照保留在该服务器目录。最终打包前补充了Windows taskkill被拒时终止自有直接工作进程的兜底，并以真实等待子进程测试通过；Linux终止逻辑、生成适配器和科学验证代码未改。只读审计工具另修正了便携目录重命名后的任务ID显示，并增加回归测试。

本地证据：`module_delivery/v0.1.0/acceptance/egmof/`及`linker/`。包含候选ZIP、请求/场景、全部提案与拒绝记录、索引、CIF、AUDIT及PORTABLE_AUDIT；原始日志与优化/MOFid详细记录在服务器任务目录。

## 能力范围

- 场景为现有CO₂吸附量/工作容量模型。目标按原生标尺传入，单位未独立核实，未声明任意气体条件能力。
- EGMOF未加载RF预测器，日志显示WMSE引导解码跳过；prop2desc接收条件目标，结果不带已验证性能预测。
- 约束为生成后过滤。EGMOF记录完整MOFid识别结果；探索模式另核对目标连接体集合与pcu。
- 当前为单机/服务器模块，无跨机器SSH调度、跨用户GPU队列、网页或自然语言解析。设备由runtime显式配置。
- 该小批证明调用与交付可执行；大规模产率、更多场景及并发资源能力需要独立验收。
