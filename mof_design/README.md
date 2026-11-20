# AI设计MOF模块 v0.1

统一任务入口：**EGMOF主生成后端＋MOFFlow-2连接体探索**。场景条件、运行环境和生成请求分开配置；输出候选CIF、验证记录、来源与可下载候选包。此版本为Python/命令行模块，未包含网页或自然语言需求解析。

## 使用

在项目根目录运行，或将本包安装到调用环境：`python -m pip install -e . --no-deps`。控制端使用标准库；实际推理/验证在runtime配置指定的既有Python环境中运行，不自动下载权重或训练模型。几何检查需要后端环境具备NumPy、ASE和SciPy。

```bash
python -m mof_design engines
python -m mof_design scenes --runtime mof_design/examples/runtime.server.json
python -m mof_design validate --runtime mof_design/examples/runtime.server.json --request mof_design/examples/egmof.json
python -m mof_design submit --runtime mof_design/examples/runtime.server.json --request mof_design/examples/egmof.json --out design_runs
python -m mof_design status design_runs/<task_id>
python -m mof_design cancel design_runs/<task_id>
```

`run`与`submit`参数相同，前者等待任务结束，后者后台执行。命令返回JSON；当前命令退出码表示命令操作是否执行，任务成败读取`status`字段。`status`返回交付清单和候选包路径；终态与打包有短暂间隔，交付就绪以`package`字段出现为准。`cancel`发出请求，由监督进程终止该任务的子进程树。终态任务不重复执行，重新提交生成新ID及独立目录。

服务器示例文件使用现有项目资产的绝对路径。其他机器应复制runtime并修改路径；Windows控制端能读取能力与配置，真实模型需在配置指定的可用环境执行。模块没有隐式SSH传输层：服务器推理须在服务器调用入口，或由外部调度器调用。

```python
from mof_design import run_design, submit_design, get_status

task = submit_design(
    {"engine": "egmof", "scene": "egmof.co2_uptake_298k_2_5bar",
     "target_value": 5.0, "num_candidates": 2, "max_attempts": 8,
     "seed": 1717, "walltime_seconds": 1800,
     "validation": {"relax": True, "mofid": True}},
    "mof_design/examples/runtime.server.json", "design_runs")
result = get_status(task["task_directory"])
```

## 两种模式及场景

| 后端 | 实际处理 | 本版本的场景条件 |
|---|---|---|
| egmof（默认） | 加载已有prop2desc/desc2mof/mof2desc，逐次生成并组装CIF | 已有Wilmer CO₂、298 K、2.5 bar吸附量检查点 |
| mofflow2_linker | 固定预算序列采样→化学/二羧酸过滤→构象7→pcu/N16组装 | 已有CO₂工作容量条件检查点；限定当前固定模板 |

目标数值按检查点原生标尺传入；其精确物理单位尚未独立核实，runtime显式记录。调用者应选择模型实际支持的场景。当前没有SiH₄/CO₂选择性或任意气体条件的已训练适配器。新增场景可登记对应已训练权重、配置、性质定义和标尺，统一任务接口复用；训练流程不在本模块命令中执行。

## 预算、约束与验证

- `num_candidates`为希望交付的合格唯一候选数；`max_attempts`限制候选提案尝试，达到预算可能只返回部分结果或失败。`walltime_seconds`限制监督进程启动后的执行墙钟，模型加载在内；配置预检与哈希准备发生在提交前。
- 元素白名单/黑名单、最大原子数及拓扑在生成后检查，明确记录为`post_generation_filter`；这些约束没有被宣称为原生神经模型的硬条件。
- 拓扑约束要求开启MOFid并核对最终拓扑。MOFFlow-2探索目前只支持pcu/N16、二羧酸、≤60重原子的连接体，额外约束不改变其模板。
- 默认最多1000原子。`relax=true`采用现有MACE medium、float64变胞BFGS：0.2最多300步，写出复读后0.05最多追加300步；默认单候选验证子任务限时1200秒，另受全任务总预算约束。
- 几何验收：显式原子数保持、最短距离≥0.9 Å、近似单连通；优化后还要求原子序列保持、体积比0.75–1.25及最终广义力收敛。组成检查要求碳和金属，是有限的组成检查，完整价态/合成可行性另需证据。
- `mofid=true`要求完整框架身份；连接体探索还核对期望连接体类型集合及pcu。MOFid成功识别不代表热力学或实验稳定性。
- 去重分层记录：同一源构筑块/拓扑组合、相同CIF字节；开启MOFid时还检查完整框架身份。未启用MOFid的候选标记`identity_verified=false`。
- 每次提案使用独立目录，防止EGMOF同名CIF输出覆盖。全部提案、排除及失败保留；不无限补采样。
- MOFFlow-2的`sequence_samples`是独立的原序列生成预算（默认100），候选尝试数是过滤后提案数；原序列和每条过滤原因保留，池耗尽后不补采样。

任务使用runtime明确分配的设备；当前为本地进程任务管理，尚无跨用户GPU资源调度。调用者应避免多个长任务争用同一GPU。

受限Windows环境若拒绝taskkill，监督器会兜底终止其自有直接工作进程；复杂多进程后端推荐使用已验收的Linux运行环境。该兜底不宣称替代完整的Windows进程树权限管理。

## 交付

```text
design_<id>/
  request.json / scene.json        输入快照及条件定义
  status.json / events.jsonl       状态、阶段、计数和事件
  provenance.json                 模块/上游代码、权重、配置哈希和版本
  candidates.json                 所有提案与验证/排除记录
  cifs/                          通过验收的候选
  manifest.json / summary.json     交付索引、相对路径、哈希与摘要
  candidates.zip / REPORT.md      候选包与批次说明
  logs/ / raw/ / optimized/ / validation/  诊断与验证证据
```

状态：queued、running、completed（达到目标数量）、partial（有交付但数量不足）、failed、cancelled、timed_out。超时/取消也保留已经完成的候选及清单。ZIP写完后原子发布，查询时不返回正在写入的压缩包；打包前复核CIF哈希。GPU固定种子提供可追溯输入，不承诺跨设备逐位一致。

## 验收

本地：`python -m unittest discover -s tests -p test_mof_design.py -v`。单元测试使用明确的假提案适配器和真实CIF验证器，不能替代原生模型验收。真实小批结果单独记录在ACCEPTANCE.md。


## 自动任务报告（当前工作区新增）

任务终结并发布候选包时，自动生成 `REPORT.html` 和 `REPORT.md`，并一同收入 `candidates.zip`。解压整个包后打开 `REPORT.html`，即可离线查看设计条件、预算与约束、请求/提案/交付数量、逐候选几何与优化状态、MOFid拓扑、拒绝原因及来源记录。浏览器打印可导出PDF。报告读取本次计算记录，不额外生成性质预测；完整数值和签名可由报告链接追溯。

取消、超时、失败、部分交付同样生成报告，未执行的检查明确显示。此改动已在工作区验证，11月17日发布的v0.1.0安装包及原始验收包保持原版；使用旧wheel时仍为原摘要报告。


## 研究人员材料档案（当前工作区新增）

候选交付时自动输出 `MATERIALS.html` 批次对比、`materials.csv`、`materials.json`，以及每个已交付候选的 `materials/Cxxxx/index.html`、`material.json`、晶胞三方向投影和可用的连接体二维图，并收入候选ZIP。材料档案与任务过程报告互相链接。

材料数据从最终交付CIF提取，记录计算晶胞化学式、元素/金属、原子数、晶胞参数/体积、质量密度、MOFid拓扑/节点/连接体、优化及几何验证。空间群由可选spglib在symprec=0.01 Å下识别。可选RDKit绘制连接体，保留MOFid分解得到的电荷形式。结构投影展示晶胞内原子和晶胞边线。孔径、孔口、表面积、可达孔体积、应用性能和参考集新颖性目前显式标为待评价，不据图像或目标条件推算。

依赖安装：`pip install '.[reports]'`。控制端缺少分析依赖时仍发布任务与CIF，材料入口会列出未能生成档案的具体错误。对已有任务可运行 `python -m mof_design material-report TASKDIR` 生成/刷新档案；此命令不修改已有候选ZIP或来源签名。完整打包在新任务正常交付时执行。历史冻结任务建议先复制，再生成衍生报告。

真实示例：module_testing/20261120/report_examples/egmof_user/MATERIALS.html 和 linker_user/MATERIALS.html。该功能目前为本地工作区实现，11月17日发布包和服务器发布快照保留原版本。
