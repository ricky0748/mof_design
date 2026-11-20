# 锚点规则（第一版）

用来替换 Nexerra 里"[Lr] 占位 + 纯几何选锚点"的那一段，接在"生成配体"和"拓扑组装"之间。组装器第一阶段选用 PORMAKE（`pip install pormake`，自带 2404 个拓扑和节点构筑块库）。

## 解决的问题

| Nexerra 的做法 | 问题 | 本模块的做法 |
|---|---|---|
| 配位基团统一抽象成 `[Lr]` | 丢掉了羧酸、唑、吡啶的区别，而这些区别决定开放金属位和孔口化学 | 用 SMARTS 识别配位基团，每个锚点带类型标签 |
| 锚点在所有 C–H 上按"平均两两距离最大"来选 | N 给体（唑、吡啶）根本表达不了；锚点位置可能和真实配位位置不一致 | 锚点由化学基团决定，N 给体沿孤对方向放 X |
| 锚点与节点无关 | 同一个配体在不同节点下配位方式不同 | 可以指定目标节点族，节点接受不了的基团记为"孔道基团" |

最后一点的典型例子是 MOF-303 的 PZDC：如果不指定节点，PZDC 会被识别成羧酸 + 吡唑共 4 个连接点；指定 Al 棒节点后，只有两个羧基配位，吡唑 NH 被标成孔道基团。实际结构里 PZDC 正是这样配位的，而这个 NH 恰好是 MOF-303 吸水、吸甲醛的关键位点。

## 规则表（`anchor_rules.py` 里的 `RULES`）

| 规则 | 优先级 | 默认给体 | 说明 |
|---|---|---|---|
| tetrazolate | 10 | N2、N3（远离取代基的一侧） | N1、N4 记为可选给体 |
| 1,2,4-triazolate | 9 | N1、N2、N4 | 例如 CALF-20 |
| 1,2,3-triazolate | 9 | N1、N3 | 含苯并三唑 |
| pyrazolate | 8 | N1、N2（外双齿） | 用 `--pyrazolate-single-x` 可改为整个吡唑只放一个 X |
| imidazolate | 8 | N1、N3 | 例如 ZIF |
| carboxylate | 5 | 2 个 O | 默认羧基 C 归节点，X 放在原羧基 C 的位置（ToBaCCo 约定） |
| pyridyl | 3 | 六元环 sp2 N | 与羧基邻位时视为螯合，降为可选给体 |

- 唑类的 SMARTS 不依赖芳香性，能识别 CoRE/MOFid 里常见的非芳香、带自由基的写法（例如 `C1=C[N]C=N1`）。
- 规则按优先级认领原子，同一个原子不会被两条规则重复匹配。
- 扩展方法：往 `RULES` 里加一条字典即可。`TODO_CLASSES` 里列了已知但还没实现的给体：膦酸、磺酸、N-氧化物、脂肪胺柱撑配体（DABCO）、酚氧/儿茶酚、氰基。
- 节点族与可接受锚点的对应关系写在 `NODE_COMPAT` 里，同样可以扩展。

## 输出格式

| 格式 | 说明 |
|---|---|
| PORMAKE xyz（默认，`to_pormake_xyz`） | 第 1 行原子数；第 2 行 X 的索引；之后原子行和键行 `i j S/D/T/A`。X 放在被切断键的中点（羧酸：芳环 C 与羧基 C 的中点；N 给体：沿孤对方向 m_n_dist/2 = 1.0 Å），组装时两侧 X 重合 |
| ToBaCCo CIF | P1 大盒子；连接点为元素 `X`；附带 `_geom_bond` 键表。X 位置随 `x_convention` 而定（`tobacco_atom` 为 X 占据羧基 C 位置） |
| He xyz | LEGO-MOF 风格，保留完整配体，在每个 X 的位置放一个虚拟 He |
| `[Lr]` SMILES | 与 Nexerra / EGMOF 交换数据用，化学上不严格 |
| JSON | 每个锚点的类型、给体原子、可选给体、X 坐标 |

## 用法

```bash
python3 anchor_cli.py linkers.smi --out out/                 # 不指定节点：按化学启发式确定主锚点
python3 anchor_cli.py linkers.smi --out out/ --node Al_rod   # 指定节点：只认节点能接受的基团
```

`linkers.smi` 每行一个 `SMILES 名字`；示例见 `demo_linkers.smi`，对应的输出在 `demo_out*/`。

## 组装（PORMAKE）

```python
import pormake as pm
from anchor_rules import analyze, to_pormake_xyz, Config
r = analyze("OC(=O)c1ccc(cc1)C(=O)O", node="Zn4O")
open("BDC.xyz", "w").write(to_pormake_xyz(r["_mh"], r["_anchors"], Config()))
db = pm.Database()
fw = pm.Builder().build_by_type(topology=db.get_topo("pcu"), node_bbs={0: db.get_bb("N16")},
                                edge_bbs={(0, 0): pm.BuildingBlock("BDC.xyz")})
fw.write_cif("IRMOF-1.cif")
```

常用节点构筑块：Zn4O = N16（6-c），Cu 桨轮 = N17（4-c），Zr6 = N419（12-c）。组装成功率测试见 `assembly_test.py` 与 `组装测试报告.md`。

## 验证

见 `锚点规则验证报告.md`（基于 CoRE MOF 2024 的全部 MOFid 配体）。
