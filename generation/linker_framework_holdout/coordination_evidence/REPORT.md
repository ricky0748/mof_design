# Zn4O配位几何探索性审计

对两批40个U结构与2个BDC控制的原始/弛豫CIF逐一复算。Zn–O邻居截断2.3、2.5、2.7 Å同时报告，未据结果设立新通过阈值。角度偏差仅在四配位Zn上计算。

```json
{
  "2.3": {
    "structures": 40,
    "all_zn_cn4": 40,
    "zn_sites": 160,
    "cn4_sites": 160,
    "coordination_outliers": []
  },
  "2.5": {
    "structures": 40,
    "all_zn_cn4": 40,
    "zn_sites": 160,
    "cn4_sites": 160,
    "coordination_outliers": []
  },
  "2.7": {
    "structures": 40,
    "all_zn_cn4": 38,
    "zn_sites": 160,
    "cn4_sites": 158,
    "coordination_outliers": [
      {
        "id": "U_L12",
        "cn": [
          4,
          4,
          5,
          4
        ]
      },
      {
        "id": "U_H05",
        "cn": [
          5,
          4,
          4,
          4
        ]
      }
    ]
  }
}
```

优化能量变化是在同一结构组成内的初末差，反映弛豫过程；它未计算分解参考或形成能，不直接作为热力学稳定性指标。优化器fmax来自变胞FrechetCellFilter，包含晶胞自由度。

逐结构数据见per_structure.csv；原计算与既有联合终点不变。