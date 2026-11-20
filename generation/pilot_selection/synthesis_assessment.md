# 合成可及性初步评估（2026-10-26）

范围：10 个通过完整 GCMC 的候选。只做配体已知性/可采购性和框架化学先例的初步核查；不代表可合成，也不构成实验配方。

## 配体与先例

| 候选 | 配体 | 配体已知/可采购 | 框架先例 | 优先级 |
|---|---|---|---|---|
| **V0041_nbo** | 2-amino-5-methoxyterephthalic acid | **有文献合成路线**：由二甲基-2-氨基-5-甲氧基对苯二甲酸酯水解得到（Aromatic Substituent Effects on MOF Flexibility，化合物 5b） | Cu/氨基-BDC 桨轮化学有报道；未找到该配体 + Cu + nbo 的直接先例 | **1** |
| **V0067_nbo** | 3-methylthiophene-2,5-dicarboxylic acid（CAS 89677-40-7） | **可商购**（BenchChem/Smolecule 有目录） | 噻吩二甲酸 MOF 有报道；该配体 + Cu nbo 未确认 | **2** |
| **V0006_nbo** | 2-aminoterephthalic acid（2-ATA） | **可商购** | Cu(BDC-NH2) 桨轮 MOF 有多次报道（H2S、D2/H2、光催化等），但未确认 nbo 拓扑 | **3 / 对照** |
| V0157_nbo | 含 CF3 的萘二甲酸 | 需确认采购/合成 | 相关氟化线性二羧酸 Cu MOF LIFM-100 有报道（CO2/R22）；不是同一配体 | 3 |
| V0031_nbo | 甲基/氨基对苯二甲酸 | 简单取代 BDC，可能可采购/一步合成 | 氨基-BDC 桨轮化学有先例；nbo 未确认 | 3 |
| V0034_nbo | 氨基/羟基对苯二甲酸 | 简单取代 BDC，需确认采购 | 同上；nbo 未确认 | 3 |
| V0023_nbo | 2-amino-4-fluoroterephthalic acid | **无直接文献/采购记录**，需定制合成 | 无直接先例 | 4 |
| V0024_nbo | 2-amino-5-fluoroterephthalic acid | **无直接文献/采购记录**，需定制合成 | 无直接先例 | 4 |
| V0047_nbo | 2-cyano-5-amino（或异构）terephthalic acid | 无直接记录，需定制合成 | 无直接先例 | 4 |
| V0048_nbo | 2-cyano-5-amino（或异构）terephthalic acid | 无直接记录，需定制合成 | 无直接先例 | 4 |

SAscore：全部 1.76–2.42（低复杂度）；它只是辅助指标，不证明 MOF 可合成。

## 推荐

1. **V0041_nbo**：综合最优。GCMC logS_CO2 0.592（10 个里最高）、q_SiH4 1.113；配体有文献水解路线；CoRE 2024/2019/CSD 均无结构匹配。建议作为第一个合成候选。
2. **V0067_nbo**：配体可商购（CAS 89677-40-7），GCMC logS_CO2 0.397；作为低成本备选。
3. **V0006_nbo**：配体 2-ATA 可商购，Cu(BDC-NH2) 桨轮化学有先例；适合作为**已知化学对照**，novelty 最低。
4. V0023/V0024/V0047/V0048：需要定制合成氟基或氰基取代配体，合成周期和风险更高，暂缓。

## 边界

- 配体有路线/可采购 ≠ 目标 MOF 能结晶；Cu 桨轮 + 线性二羧酸 + nbo 是已知家族，但这些具体取代组合的框架合成未在数据库或文献中找到直接先例。
- 未联系供应商、未询价、未向实验团队提交任何合成任务；需要授权后再做。
- 建议的实验搜索范围（仅供内部讨论）：Cu(II) 盐 + 配体，DMF/H2O 或 DMF/EtOH 溶剂热，80–120 °C，调节酸/碱和浓度；先做小规模结晶筛选，再做 PXRD/BET/CO2 吸附。不要从 CIF 承诺确定配方。

## 来源

- 2-amino-5-methoxyterephthalic acid 的合成/化合物 5b：Aromatic Substituent Effects on the Flexibility of Metal-Organic Frameworks（Academia 页面）。
- 3-methylthiophene-2,5-dicarboxylic acid CAS 89677-40-7：BenchChem / Smolecule。
- Cu(BDC-NH2) 桨轮 MOF：Dastbaz et al. 2024（D2/H2）、Gupta et al. 2021（H2S）、Tao et al. 2024（Cr(VI)）。
- 氟化线性二羧酸 Cu MOF LIFM-100：Qiu et al., Inorg. Chem. 2020, 59, 14856（DOI 10.1021/acs.inorgchem.0c02123）。
