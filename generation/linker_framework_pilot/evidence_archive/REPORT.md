# 连接体—框架组合小试结果

2026-11-13；配对固定20个唯一连接体；8个训练序列外片段、12个训练内片段。

A：原生MOFFlow-2框架；B：相同连接体，pcu/N16模板构建。两臂统一新MACE计算。

| 指标（分母20） | A 原生 | B 模板 |
|---|---:|---:|
| 预算内几何有效 | 7/20 | 1/20 |
| 150步内优化收敛 | 1/20 | 1/20 |
| MOFid恢复目标连接体 | 5/20 | 1/20 |
| 完整拓扑身份 | 0/20 | 1/20 |
| 主终点：几何+连接体+拓扑 | 0/20 | 1/20 |

B组装状态：{"incompatible": 19, "built": 1}

主终点配对结果：{"neither": 19, "B_only": 1, "exact_mcnemar_p": 1}

阳性控制BDC/BPDC均通过几何、目标连接体恢复和完整拓扑检查。

## 解释范围

固定的是连接体；节点、拓扑和化学计量随构建方案改变。结果用于评估指定模板下的连接体可用性；纯组装算法效果需要同节点/拓扑的后续对照。

方向不兼容、计算失败和未解决样本都保留在20个分母中；部分MOFid解析单列。150步预算内几何有效与优化收敛分别报告。

## 逐配对结果

| ID | 原生金属 | 训练外 | B方向偏差 | A主终点 | B主终点 | B状态 |
|---|---|---|---:|---|---|---|
| L01 | V | True | 31.9 | False | False | incompatible |
| L02 | V | True | 32.4 | False | False | incompatible |
| L03 | V | True | 28.5 | False | False | incompatible |
| L04 | V | True | 28.4 | False | False | incompatible |
| L05 | V | True | 29.0 | False | False | incompatible |
| L06 | V | True | 32.6 | False | False | incompatible |
| L07 | V | True | 28.6 | False | False | incompatible |
| L08 | V | True | 28.8 | False | False | incompatible |
| L09 | V | False | 31.9 | False | False | incompatible |
| L10 | V | False | 30.2 | False | False | incompatible |
| L11 | V | False | 31.1 | False | False | incompatible |
| L12 | V | False | 29.9 | False | False | incompatible |
| L13 | V | False | 27.5 | False | False | incompatible |
| L14 | V | False | 13.5 | False | True | completed |
| L15 | V | False | 31.1 | False | False | incompatible |
| L16 | V | False | 31.0 | False | False | incompatible |
| L17 | V | False | 34.4 | False | False | incompatible |
| L18 | V | False | 31.0 | False | False | incompatible |
| L19 | V | False | 33.4 | False | False | incompatible |
| L20 | V | False | 31.8 | False | False | incompatible |

## 机制观察与下一步

19/20在固定seed=7构象与20°方向阈值下不兼容；多数连接方向相对X–X轴偏差约28–34°。本轮的主要损失发生在模板兼容性阶段。八个训练序列外片段均未越过该关口。

下一轮应先根据连接方向和局部配位几何分类，再冻结兼容模板；可探索支持弯曲二连接构筑块的节点/拓扑。保留本轮固定pcu协议与失败分母，不通过放宽阈值重写结果。

样本均来自V节点原生框架，而B使用Zn4O。MACE对两种金属环境的可靠性尚未专项校验，结果按预算内结构筛查解释。

### 可复核重新组装案例：L14

源样本 mofflow2s_542，原始序列索引742。连接体 `CCOc1cc2cc(C(=O)[O-])cc(OCC)c2cc1C(=O)[O-]`；训练序列外标记=False。

A：最短距离0.484 Å、片段数3、拓扑ERROR。
B：最短距离1.082 Å、片段数1、拓扑pcu、23步收敛；MOFid恢复目标连接体。

案例B_L14在171978条已完整识别的训练框架身份中匹配数为0；参考预期187047条，部分解析的覆盖缺口仍保留。

## 实际计算与产物

正式A弛豫20个、B弛豫1个，另含2个阳性控制，共23次MACE调用；正式样本无超时和运行异常。19个B兼容性拒绝保留在分母。

逐结构运行秒数合计：{"A": 830.8, "B": 11.0}（含加载，非串行墙钟时间）。

冻结清单 frozen.json / selected.json；配对结果 pairs.csv / pairs.json；原始和弛豫CIF raw/、relaxed/；逐结构优化与MOFid日志 records/、logs/、mofid/。
