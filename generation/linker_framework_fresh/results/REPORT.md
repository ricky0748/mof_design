# 全新生成批次与双构象种子结果

序列种子719固定生成200条；排除旧40种连接体后，冻结实际18种连接体。A原生，U7/U19为固定pcu/N16与构象种子7/19。

| 指标（分母18） | A | U7 | U19 |
|---|---:|---:|---:|
| 几何有效 | 1/18 | 16/18 | 18/18 |
| 150步收敛 | 2/18 | 16/18 | 18/18 |
| 目标连接体恢复 | 2/18 | 17/18 | 18/18 |
| 完整拓扑身份 | 0/18 | 17/18 | 18/18 |
| 联合终点 | 0/18 | 16/18 | 18/18 |

两构象种子均通过：16/18；至少一种通过：18/18。两项分开报告，不能把择优后的结果称为单次生成成功率。

```json
{
  "n": 18,
  "arms": {
    "A": {
      "geometry": 1,
      "converged": 2,
      "target_recovered": 2,
      "topology_identified": 0,
      "joint": 0
    },
    "U7": {
      "geometry": 16,
      "converged": 16,
      "target_recovered": 17,
      "topology_identified": 17,
      "joint": 16
    },
    "U19": {
      "geometry": 18,
      "converged": 18,
      "target_recovered": 18,
      "topology_identified": 18,
      "joint": 18
    }
  },
  "statuses": {
    "A": {
      "completed": 18
    },
    "U7": {
      "completed": 18
    },
    "U19": {
      "completed": 18
    }
  },
  "paired_A_U7": {
    "right_only": 16,
    "neither": 2,
    "exact_mcnemar_p": 3.0517578125e-05
  },
  "paired_A_U19": {
    "right_only": 18,
    "exact_mcnemar_p": 7.62939453125e-06
  },
  "both_seeds_pass": 16,
  "either_seed_pass": 18,
  "same_seed_success_status": 16,
  "expected_pcu": {
    "U7": 17,
    "U19": 18
  },
  "unique_formal_jobs": 54,
  "aliases": {},
  "reread_discrepancies": [],
  "old_gate": {
    "U7": {
      "rejected": 18,
      "rejected_and_pass": 16
    },
    "U19": {
      "rejected": 18,
      "rejected_and_pass": 18
    }
  },
  "unique_U_frameworks": 19,
  "reference_processed": 187047,
  "reference_identified": 171978,
  "training_matches": [
    {
      "samples": [
        "U7_F03",
        "U19_F03"
      ],
      "training_ids": [
        "224094",
        "233675",
        "306761",
        "63238"
      ]
    },
    {
      "samples": [
        "U7_F16",
        "U19_F16"
      ],
      "training_ids": [
        "44355",
        "84814"
      ]
    }
  ],
  "physical_relaxation_seconds": 4363.5380000000005
}
```

组装同时改变节点、拓扑和初始坐标；结果评价整个重建方案。该批次固定目标条件，目标响应、配位应变、热力学稳定性和吸附性能另评。主表以最终CIF复读指标为准，内存与复读差异逐条列出。

身份计数审计：全部已识别U输出共19种身份，其中联合终点通过的有效输出为18种。无效几何特有身份单列于AUDIT.json；不将其计为有效新框架。


## 补充审计

本批A直接使用新模型预测CIF；前两批A来自历史UFF输出，跨批次主表不能单独用于归因序列种子。训练片段标签在选样冻结后计算，采用组成必要条件预筛再作精确规范化匹配，未参与选样；参考中不可解析字符串数如实保留。

```json
{
  "training_fragment_strata": {
    "raw_canonical_in_train": {
      "True": {
        "n": 17,
        "A": 0,
        "U7": 15,
        "U19": 17
      },
      "False": {
        "n": 1,
        "A": 0,
        "U7": 1,
        "U19": 1
      }
    },
    "normalized_in_train": {
      "True": {
        "n": 17,
        "A": 0,
        "U7": 15,
        "U19": 17
      },
      "False": {
        "n": 1,
        "A": 0,
        "U7": 1,
        "U19": 1
      }
    }
  },
  "unparsed_training_strings": 0,
  "coordination": {
    "2.3": {
      "all_zn_cn4": 34,
      "structures_with_cif": 36
    },
    "2.5": {
      "all_zn_cn4": 34,
      "structures_with_cif": 36
    },
    "2.7": {
      "all_zn_cn4": 34,
      "structures_with_cif": 36
    }
  }
}
```

Zn–O截断2.3/2.5/2.7 Å均保留，四面体角RMS见coordination.json；失败构建和无输出未补样。源文件、冻结哈希、逐任务签名与映射复核见AUDIT.json。


最终有效身份范围：18种有效框架中，F03和F16对应2种身份命中训练参考，另16种在171978条完整训练参考中未匹配；15069条部分解析仍为覆盖缺口。F17在187047条训练序列有机片段的两种精确规范化口径中均未匹配，且两构象组均通过；该训练片段审计中不可解析字符串数为0。所有通过联合终点的U输出还核对了目标连接体集合完全一致。
