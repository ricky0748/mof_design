# AI MOF Design

基于现有开源生成模型的 MOF 设计模块，支持 **EGMOF 主生成**与 **MOFFlow-2 连接体探索 + 固定 pcu/Zn₄O 组装**，交付候选 CIF、验证记录、任务报告和面向研究人员的材料档案。

当前仓库包含 2026-11-20 本地项目源码、各阶段研究脚本、配置、文档与文本汇总数据。报告功能已接入当前源码；原服务器 v0.1.0 发布快照与旧安装包尚未更新。仓库不包含模型权重、第三方模型源码、运行环境及全部历史研究数据。

## 当前能力

- Python API / CLI：配置检查、提交、状态、取消、超时及预算控制。
- 生成后约束过滤、可选 MACE 两阶段结构优化、几何检查、MOFid 身份识别和去重。
- 多候选 CIF、来源签名、失败原因及 ZIP 交付。
- `REPORT.html`：生成任务过程报告。
- `MATERIALS.html`：候选对比入口；每个材料包含结构投影、连接体图、晶胞参数、计算密度、空间群及验证依据。
- 孔隙、吸附性能、参考集新颖性在材料报告中标明实际评价状态，按需增加独立计算。

## 安装与使用

Python 3.10+：

```bash
pip install -e '.[validation,reports]'
python -m mof_design engines
python -m mof_design scenes --runtime mof_design/examples/runtime.server.json
```

运行模型前，需要按 [模块使用说明](mof_design/README.md) 安装上游模型与权重，并将示例 runtime 中的路径修改为自己的环境。示例配置中的服务器路径为原项目环境路径。现有模型场景为 CO₂ 性质条件，目标数值采用原模型标尺。

```bash
python -m mof_design validate --request mof_design/examples/egmof.json --runtime runtime.local.json
python -m mof_design submit --request mof_design/examples/egmof.json --runtime runtime.local.json --out design_runs
python -m mof_design status design_runs/TASK_ID
python -m mof_design material-report design_runs/TASK_ID
```

新任务自动生成并打包两类报告。`material-report` 为已有任务刷新材料档案，保留已有候选 ZIP 和来源签名。

## 查看真实结果

HTML 报告下载仓库后用浏览器打开；GitHub 文件页主要展示源代码。

- [本地成果统一入口](INDEX.html)
- [EGMOF 候选材料对比](module_testing/20261120/report_examples/egmof_user/MATERIALS.html)
- [连接体候选材料对比](module_testing/20261120/report_examples/linker_user/MATERIALS.html)
- [真实验收结果](module_testing/20261120/results/server/RESULTS.json)
- [材料报告审计](module_testing/20261120/report_examples/MATERIAL_REPORT_AUDIT.json)

本轮真实任务两条路线各请求 2 个、交付 2 个候选；9 项功能验收通过。20 项模块测试与 3 项报告测试通过。报告数据、相对链接及候选包已检查；浏览器视觉复核待完成。

```bash
python -m unittest discover -s tests -p test_mof_design.py
python -m unittest discover -s tests -p 'test_*report.py'
```

## 项目记录与范围

[项目总览](PROJECT_OVERVIEW.md) · [下一步](NEXT_STEPS.md) · [工作日志](worklog.md) · [第三方来源](mof_design/THIRD_PARTY_NOTICES.md)

项目总目标是可调用的 AI MOF 设计模块。SiH₄/CO₂ 是历史应用验证案例。部分历史文档引用的研究目录保留在原项目工作区，不包含在本仓库快照中。当前结果为计算候选；实验可合成性、稳定性和具体应用性能需独立验证。


## 完整项目目录

| 目录 | 内容 |
|---|---|
| `mof_design/`、`tests/` | 可调用模块与测试 |
| `generation/` | 三引擎评价、结构精修、MOFid、条件响应、吸附对照与项目工作台 |
| `anchor_rules/` | 锚点规则、结构组装与验证 |
| `cg_assembly/` | 粗粒化组装及分析 |
| `r2_probe/` | 探索评价与化学特征分析 |
| `widom_sih4/` | Henry/Widom 输入、力场、分析与适用域相关工作 |
| `module_testing/` | 模块验收、真实候选、任务和材料报告 |
| `tmp/` | 两个保留的研究脚本；安装检查副本已排除 |

[SOURCE_INVENTORY.json](SOURCE_INVENTORY.json) 逐文件记录本次补传路径、大小及哈希，并列出排除范围。源码与配置保持原路径；大模型权重、虚拟环境、缓存、第三方压缩包、论文PDF及完整生成结构数据留在原环境。部分计算在服务器执行，仅服务器存在且尚未取回的文件不在本地上传范围。

`MANIFEST.json` 是第一次模块快照的清单；完整源码补传范围以 `SOURCE_INVENTORY.json` 为准。
