# 同预算组合路线确认结果

固定600条序列，排除历史58种身份，冻结30种新连接体。A300原生；S300单构象7；D为7/19各150步。严格终点使用最终CIF、完整连接体类型集合和预期拓扑。

| 策略 | 严格成功 | 成功率Wilson95% | 任务墙钟秒 | 秒/有效框架 |
|---|---:|---|---:|---:|
| A300 | 0/30 | 0.0%–11.4% | 5516.7 | NA |
| S300 | 26/30 | 70.3%–94.7% | 1643.3 | 63.20392944921668 |
| D | 28/30 | 78.7%–98.2% | 2846.2 | 101.65019305076983 |

预登记选择：S；S/D规则原因：dual_gain_costs_more_than_20pct。

任务墙钟是GPU分配给进程的端到端时间，包含加载与退出，非核函数计时。D7若复用早收敛S终态，逻辑成本仍完整计入D；物理执行成本另列。原生坐标预测成本另列。

```json
{
  "n": 30,
  "reread_discrepancies": [
    {
      "name": "A300_B04",
      "in_memory": {
        "natoms": 148,
        "volume": 2262.3244160939744,
        "dmin": 0.0018339349365823158,
        "fragments": 62
      },
      "reread": {
        "natoms": 147,
        "volume": 2262.3244160939744,
        "dmin": 0.2761483581034752,
        "fragments": 62
      },
      "geometry_changed": false
    },
    {
      "name": "S300_B25",
      "in_memory": {
        "natoms": 119,
        "volume": 3771.725271236161,
        "dmin": 0.013955560903274683,
        "fragments": 31
      },
      "reread": {
        "natoms": 118,
        "volume": 3771.7252712361674,
        "dmin": 0.5158916365763341,
        "fragments": 33
      },
      "geometry_changed": false
    }
  ],
  "strategies": {
    "A300": {
      "success": 0,
      "n": 30,
      "rate": 0.0,
      "wilson95": [
        0,
        0.11351339317396876
      ],
      "gpu_task_wall_seconds": 5516.6673975512385,
      "seconds_per_valid": null,
      "atom_steps": 1273076
    },
    "S300": {
      "success": 26,
      "n": 30,
      "rate": 0.8666666666666667,
      "wilson95": [
        0.703186733179637,
        0.9469034451594526
      ],
      "gpu_task_wall_seconds": 1643.3021656796336,
      "seconds_per_valid": 63.20392944921668,
      "atom_steps": 215277
    },
    "D": {
      "success": 28,
      "n": 30,
      "rate": 0.9333333333333333,
      "wilson95": [
        0.7867654163738308,
        0.9815229762087295
      ],
      "gpu_task_wall_seconds": 2846.205405421555,
      "seconds_per_valid": 101.65019305076983,
      "atom_steps": 327365
    }
  },
  "branch_metrics": {
    "A300": {
      "geometry": 6,
      "converged": 3,
      "target_recovered": 4,
      "exact_linker_set": 1,
      "topology_identified": 0,
      "strict_joint": 0
    },
    "S300": {
      "geometry": 28,
      "converged": 28,
      "target_recovered": 27,
      "exact_linker_set": 26,
      "topology_identified": 28,
      "strict_joint": 26
    },
    "D7": {
      "geometry": 28,
      "converged": 28,
      "target_recovered": 27,
      "exact_linker_set": 26,
      "topology_identified": 30,
      "strict_joint": 26
    },
    "D19": {
      "geometry": 29,
      "converged": 29,
      "target_recovered": 28,
      "exact_linker_set": 28,
      "topology_identified": 29,
      "strict_joint": 28
    }
  },
  "branch_statuses": {
    "A300": {
      "completed": 30
    },
    "S300": {
      "completed": 30
    },
    "D7": {
      "completed": 30
    },
    "D19": {
      "completed": 30
    }
  },
  "paired_S_D": {
    "both": 26,
    "dual_only": 2,
    "neither": 2
  },
  "both_dual_branches_pass": 26,
  "dual_converged_candidates": 28,
  "dual_geometry_only_pass": 29,
  "strata": {
    "raw_canonical_in_train": {
      "True": {
        "n": 26,
        "A300": 0,
        "S300": 22,
        "D": 24
      },
      "False": {
        "n": 4,
        "A300": 0,
        "S300": 4,
        "D": 4
      }
    },
    "normalized_in_train": {
      "True": {
        "n": 26,
        "A300": 0,
        "S300": 22,
        "D": 24
      },
      "False": {
        "n": 4,
        "A300": 0,
        "S300": 4,
        "D": 4
      }
    }
  },
  "paired_bootstrap": {
    "seed": 1302,
    "repetitions": 2000,
    "cost_per_valid95": {
      "A300": {
        "interval": null,
        "nonzero_success_draws": 0
      },
      "S300": {
        "interval": [
          49.40949567859543,
          86.89887368067248
        ],
        "nonzero_success_draws": 2000
      },
      "D": {
        "interval": [
          89.78301364494006,
          117.94678019058924
        ],
        "nonzero_success_draws": 2000
      }
    },
    "dual_single_cost_ratio95": [
      1.2419245953030444,
      1.9195320982184
    ],
    "yield_difference95": [
      0.0,
      0.16666666666666666
    ]
  },
  "decision": {
    "recommendation": "S",
    "reason": "dual_gain_costs_more_than_20pct"
  },
  "stage_times": {
    "sequence": {
      "wall_seconds": 345.34089298546314,
      "returncode": 0,
      "command": [
        "/share/rickyswork/ai_mof/envs/mofflow2/bin/python",
        "-m",
        "experiments.predict_seq",
        "inference.ckpt_path=/share/rickyswork/ai_mof/generation/budget_confirmation_20261113/seq_module_cond/ckpt.pt",
        "inference.seed=1301",
        "inference.total_samples=600",
        "inference.temperature=1.0",
        "inference.target_property=5.0",
        "inference.batch_size=50",
        "hydra.run.dir=/share/rickyswork/ai_mof/generation/budget_confirmation_20261113/hydra_seq"
      ]
    },
    "native_prediction": {
      "wall_seconds": 282.4956018961966,
      "returncode": 0,
      "command": [
        "/share/rickyswork/ai_mof/envs/mofflow2/bin/python",
        "-m",
        "experiments.predict",
        "inference.task=gen",
        "inference.ckpt_path=/share/rickyswork/ai_mof/generation/budget_confirmation_20261113/sp_module/ckpt.pt",
        "inference.seed=1301",
        "inference.gen.metal_lib_path=/share/rickyswork/ai_mof/generation/pilots/MOFFlow-2/data/metals/metal_lib_train.pkl",
        "inference.gen.mof_seqs_path=/share/rickyswork/ai_mof/generation/budget_confirmation_20261113/selected_sequences.json",
        "inference.num_samples=1",
        "inference.num_devices=1",
        "hydra.run.dir=/share/rickyswork/ai_mof/generation/budget_confirmation_20261113/hydra_pred"
      ]
    }
  },
  "native_cost_including_prediction_per_valid": null,
  "final_recommendation": "S",
  "physical_formal_jobs": 92,
  "derived_D7_records": [
    "D7_B01",
    "D7_B03",
    "D7_B04",
    "D7_B05",
    "D7_B06",
    "D7_B07",
    "D7_B08",
    "D7_B09",
    "D7_B10",
    "D7_B11",
    "D7_B12",
    "D7_B13",
    "D7_B14",
    "D7_B15",
    "D7_B16",
    "D7_B17",
    "D7_B18",
    "D7_B19",
    "D7_B20",
    "D7_B21",
    "D7_B22",
    "D7_B23",
    "D7_B24",
    "D7_B26",
    "D7_B27",
    "D7_B28",
    "D7_B29",
    "D7_B30"
  ],
  "physical_formal_wall_seconds": 8644.687703676522,
  "identity": {
    "unique_valid_frameworks": 28,
    "unique_all_identified_frameworks": 33,
    "reference_processed": 187047,
    "reference_identified": 171978,
    "reference_partial": 15069,
    "matched_valid_identities": 0,
    "unmatched_valid_identities": 28,
    "matches": []
  },
  "scope": {
    "heavy_atoms": [
      20,
      32
    ],
    "organic_elements": [
      "C",
      "N",
      "O",
      "S"
    ],
    "connection_axis_angles": [
      0.2491167618141289,
      35.06255337545123
    ],
    "retained_atoms": {
      "A300": [
        128,
        192
      ],
      "S300": [
        95,
        143
      ],
      "D7": [
        95,
        143
      ],
      "D19": [
        95,
        143
      ]
    }
  }
}
```

本阶段结果限于本批固定目标、二羧酸连接体、固定pcu/Zn4O与所用势能模型。统计已包含失败/超时，无追加修复；条件响应、热力学稳定性和吸附性能另评。