# 收敛敏感性对照

预登记见 [PROTOCOL.md](PROTOCOL.md)。服务器目录：`/share/rickyswork/ai_mof/generation/convergence_sensitivity_20261116`。

执行顺序：`run.py` → `finish.sh`（等待计算、MOFid、`report.py`、`audit.py`）。运行环境沿用原实验。每条任务上限1200秒/300个追加步数。

本地 `results/` 保存服务器结果快照；`plot_cn.py` 读取快照生成中文对照图。`REPORT.md` 记录最终结论。`accepted_primary_manifest.json` 仅包括原26个交付结构中在本轮同时收敛、几何和严格身份通过者，其余诊断样本单列。原候选包不覆盖。

文件说明：`frozen.json` 固定输入/模型/运行脚本与协议；`records/*.history.jsonl` 为逐步能量、原子力、广义力及体积；`per_structure.csv` 为逐结构对照；`summary.json` 分26主样本/8诊断样本；`AUDIT.json` 验证原输入未改写、记录轨迹与收敛一致。此审计没有独立重新计算力。

统计说明：优化停止使用过滤器广义力；物理原子最大力另外记录，二者因变胞坐标变换可以不同。位移按同原子索引、原晶胞度量的分数坐标最小镜像并移除整体平移计算，包含内部重排，不含纯晶胞形变；没有对称性重映射。配位角仅统计指定截断下四配位Zn，配位数变化另报；身份相同不表示原子几何相同。
