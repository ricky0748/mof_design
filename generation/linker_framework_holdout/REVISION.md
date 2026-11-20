# Review修复版本（2026-11-13）

本目录源代码包含新修复；results/与results_bundle.tar.gz保留原始冻结版本，服务器历史实验目录未更改。

## 修改

- compute_config.py统一模型路径、弛豫预算与几何阈值，NeighborList显式skin=0。
- provenance.py为每个任务绑定原始CIF、模型文件、目录Python脚本和全部计算参数；完成后保存弛豫CIF的SHA256。
- run.py在任何任务启动、run.json或manifest写入前核对全部已有正式任务记录。签名缺失、不一致或输出文件被修改时停止，并提示使用新目录；一致记录允许复用。计算结束后再次核对输入签名，避免运行期间变更。
- 正式构建与运行入口均验证冻结输入、脚本、support和模型；pipeline.sh必须显式提供运行目录。

## 验证

13项测试通过，包括两个运行入口集成测试：无签名旧记录在启动子进程前被拒绝，签名一致记录不启动计算并正常生成清单。另覆盖输入、模型、脚本、参数变更及输出缺失/篡改。

40个归档CIF按显式skin=0重新计算：17个原生结构连通分量数改变，最终几何通过/失败判定变化0/40；A仍2/20、U仍20/20。复算数据和图见review_evidence/。

命令：`python -m unittest discover -s generation/linker_framework_holdout -p test_revision.py -v`；`python generation/linker_framework_holdout/quantify_review.py`。

新运行须将本版本脚本、协议和support复制到新的实验目录，再调用`bash pipeline.sh /absolute/new/run/directory`。原实验目录的冻结哈希与无签名记录会被拒绝，历史结果继续用于审计。

本次没有新增GPU弛豫；验证覆盖签名保护与评价复算，不增加新的结构质量样本。
