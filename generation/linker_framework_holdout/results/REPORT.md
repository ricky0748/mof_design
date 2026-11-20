# 留出连接体验证结果

同一千样本池中未进入v1/v2的20种连接体；构象种子19。未新生成完整批次。

| 指标（分母20） | 原生A | 无预筛U |
|---|---:|---:|
| 几何有效 | 2/20 | 20/20 |
| 预算内收敛 | 1/20 | 19/20 |
| 目标连接体恢复 | 2/20 | 20/20 |
| 完整拓扑身份 | 0/20 | 20/20 |
| 联合终点 | 0/20 | 20/20 |

训练外标记样本数：0。逐CIF复读的几何通过/失败分类与内存记录一致；距离、原子数或连通分量数值差异保存在reread_discrepancies，逐条保留。完整原始结果、预登记和冻结哈希随附。

```json
{
  "A": {
    "geometry": 2,
    "converged": 1,
    "target_recovered": 2,
    "topology_identified": 0,
    "joint": 0
  },
  "U": {
    "geometry": 20,
    "converged": 19,
    "target_recovered": 20,
    "topology_identified": 20,
    "joint": 20
  },
  "n": 20,
  "paired": {
    "right_only": 20,
    "exact_mcnemar_p": 1.9073486328125e-06
  },
  "novel": 0,
  "unique_runs": 40,
  "aliases": {},
  "audit_pass": true,
  "expected_pcu": 20,
  "reread_discrepancies": [
    {
      "name": "A_H19",
      "in_memory": {
        "natoms": 140,
        "volume": 2395.428715781922,
        "dmin": 0.003337542478024382,
        "fragments": 10
      },
      "reread": {
        "natoms": 139,
        "volume": 2395.428715781922,
        "dmin": 0.4585471001364297,
        "fragments": 10
      }
    }
  ],
  "old_gate_cross_table": {
    "20": {
      "rejected": 19,
      "rejected_but_joint_pass": 19
    },
    "30": {
      "rejected": 13,
      "rejected_but_joint_pass": 13
    },
    "35": {
      "rejected": 1,
      "rejected_but_joint_pass": 1
    }
  },
  "unique_U_frameworks": 20,
  "reference_processed": 187047,
  "reference_identified": 171978,
  "training_matches": {
    "[\"[O-]C(=O)C12CCC(CC1)(CC2)C(=O)[O-].[Zn][O]([Zn])([Zn])[Zn]\",\"pcu\",\"0\"]": [
      "125035"
    ]
  }
}
```

报告脚本首次因CIF复读数值差异暂停；冻结版report.py保存在report_frozen.py，本报告脚本追加差异记录并核对几何分类一致，未修改计算和评价阈值。

联合终点描述几何和身份质量；后续配位应变、相对能量稳定性及吸附性能独立评价。

训练身份命中对应样本：[{"sample": "U_H04", "training_ids": ["125035"]}]。19种U框架身份在完整参考中未匹配，15069条参考部分解析。
