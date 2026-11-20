# 连接体—框架组合小试 v1

2026-11-13，已完成。

- [预登记协议](PROTOCOL.md)：20个冻结连接体，8个训练序列外、12个训练内；相同连接体下比较原生V框架和固定pcu/Zn4O构建方案。
- [结果报告](results/REPORT.md)：原生7/20几何有效，模板1/20几何有效；主终点（几何+目标连接体+拓扑）原生0/20、模板1/20。
- [成功案例弛豫CIF](results/relaxed/B_L14.cif)：目标连接体恢复、pcu识别、23步收敛；对应原生样本mofflow2s_542。
- [逐配对数据](results/pairs.csv)、[冻结清单](results/frozen.json)、[样本](results/selected.json)、[审计记录](AUDIT.json)。
- `results/pilot_results.png`、`pilot_results.svg`：端点对照和连接方向偏差图。
- **完整原始证据**位于 `evidence_archive/`，另有完整压缩包 `results_bundle.tar.gz`。`results/` 保留常用结果、CIF和绘图；审计使用完整证据目录。

主要观察：19个连接体在固定seed=7构象和预登记20°方向阈值下不兼容线性pcu模板；8个训练外片段全部在此关口被拒绝。得到一个训练内连接体的重新组装案例，固定模板整体收益尚未建立。后续重点是按连接方向与局部配位几何选择兼容模板。

原生V节点与模板Zn4O的变化、固定单构象、单模板和150步MACE预算均属于本轮试验范围。几何有效与优化收敛分别报告。

## 复现

服务器试验目录：`/share/rickyswork/ai_mof/generation/linker_framework_pilot_20261113/`。

顺序：`prepare.py`冻结输入 → `build.py --controls-only` → `run_relax.py --controls-only` → `evaluate.py manifest --controls-only` → 官方MOFid → `evaluate.py report --controls-only` → `pipeline.sh`正式组装/统一弛豫/MOFid/报告。

`prepare.py`会拒绝覆盖已有冻结清单。复现实验请用独立输出目录并适配脚本中的路径；保留现有输入和结果。`plot_results.py`从本地结果生成图。

正文报告的机制观察在终点计算后补充；样本、主终点和阈值保持预登记。最终分析脚本哈希与证据包哈希保存在`AUDIT.json`，执行期脚本哈希保存在原始证据的`execution_receipt.json`。


> 2026-11-13解释更正：v2取消直线预筛后，同20连接体全部通过联合终点。原先19次预筛拒绝应视为手工规则误拒；此前模板不适配的解释已修正。详见 ../linker_framework_pilot_v2/results/REPORT.md。原始数据与协议保留。
