# 成键约束几何预处理小试结果

两失败案例与四成功控制，固定50步几何预处理+100步MACE预算。历史基线为150步MACE。

| 样本 | 旧联合终点 | 预处理通过 | 预处理步数 | MACE步数 | 新严格pcu联合终点 | 收敛 |
|---|---|---|---:|---:|---|---|
| U7_F11 | False | True | 23 | 88 | False | True |
| U7_F14 | False | True | 50 | 100 | False | False |
| U19_F11 | True | True | 0 | 18 | True | True |
| U19_F14 | True | True | 9 | 74 | True | True |
| U19_F04 | True | True | 50 | 45 | False | True |
| control_BDC19 | True | True | 0 | 6 | True | True |

```json
{
  "n": 6,
  "failed_cases_recovered": 0,
  "failed_cases_n": 2,
  "successful_controls_preserved": 3,
  "successful_controls_n": 4,
  "rows": [
    {
      "name": "U7_F11",
      "reason": "failed seed7, inter-linker clashes",
      "baseline_geometry": false,
      "baseline_joint": false,
      "status": "completed",
      "precondition": {
        "steps": 23,
        "initial_nonbonded_min": 0.5970785490427543,
        "dmin": 1.086870703378764,
        "max_bond_shift": 0.0012781980575504726,
        "geometry_objective": 0.27618537385336617,
        "passed": true
      },
      "converged": true,
      "mace_steps": 88,
      "topology": "pcu",
      "target_recovered": true,
      "exact_linker_set": false,
      "geometry": false,
      "after": {
        "natoms": 116,
        "volume": 4218.553783011533,
        "dmin": 0.8796336849029319,
        "fragments": 1
      },
      "volume_ratio": 1.0003732193711479,
      "initial_mace_fmax": 15.971538,
      "final_mace_fmax": 0.166151,
      "initial_mace_energy": -745.069205,
      "final_mace_energy": -765.593993,
      "joint": false,
      "strict_pcu_joint": false
    },
    {
      "name": "U7_F14",
      "reason": "failed seed7, inter-linker clashes",
      "baseline_geometry": false,
      "baseline_joint": false,
      "status": "completed",
      "precondition": {
        "steps": 50,
        "initial_nonbonded_min": 0.37616092550829877,
        "dmin": 1.0861726045500812,
        "max_bond_shift": 0.007066715019768299,
        "geometry_objective": 1.6579265363238194,
        "passed": true
      },
      "converged": false,
      "mace_steps": 100,
      "topology": "ERROR",
      "target_recovered": false,
      "exact_linker_set": false,
      "geometry": false,
      "after": {
        "natoms": 119,
        "volume": 4215.452118313228,
        "dmin": 0.5392286595341332,
        "fragments": 21
      },
      "volume_ratio": 0.9957497457776244,
      "initial_mace_fmax": 1635.613362,
      "final_mace_fmax": 14604.73597,
      "initial_mace_energy": -609.277789,
      "final_mace_energy": -4702.719427,
      "joint": false,
      "strict_pcu_joint": false
    },
    {
      "name": "U19_F11",
      "reason": "paired successful seed19",
      "baseline_geometry": true,
      "baseline_joint": true,
      "status": "completed",
      "precondition": {
        "steps": 0,
        "initial_nonbonded_min": 1.6229027595954038,
        "dmin": 1.0858595753286215,
        "max_bond_shift": 0.0,
        "geometry_objective": 0.0,
        "passed": true
      },
      "converged": true,
      "mace_steps": 18,
      "topology": "pcu",
      "target_recovered": true,
      "exact_linker_set": true,
      "geometry": true,
      "after": {
        "natoms": 116,
        "volume": 4244.897792750023,
        "dmin": 1.085290246868399,
        "fragments": 1
      },
      "volume_ratio": 1.0017760565313931,
      "initial_mace_fmax": 3.294799,
      "final_mace_fmax": 0.186057,
      "initial_mace_energy": -763.431162,
      "final_mace_energy": -767.699437,
      "joint": true,
      "strict_pcu_joint": true
    },
    {
      "name": "U19_F14",
      "reason": "paired successful seed19",
      "baseline_geometry": true,
      "baseline_joint": true,
      "status": "completed",
      "precondition": {
        "steps": 9,
        "initial_nonbonded_min": 0.9556674216289531,
        "dmin": 1.0862438195475093,
        "max_bond_shift": 0.001078759227995496,
        "geometry_objective": 0.0327946708893528,
        "passed": true
      },
      "converged": true,
      "mace_steps": 74,
      "topology": "pcu",
      "target_recovered": true,
      "exact_linker_set": true,
      "geometry": true,
      "after": {
        "natoms": 119,
        "volume": 4232.807523245574,
        "dmin": 1.0828483010156276,
        "fragments": 1
      },
      "volume_ratio": 1.0059932663067908,
      "initial_mace_fmax": 14.681054,
      "final_mace_fmax": 0.183335,
      "initial_mace_energy": -759.269663,
      "final_mace_energy": -787.736689,
      "joint": true,
      "strict_pcu_joint": true
    },
    {
      "name": "U19_F04",
      "reason": "successful despite sub0.9 initial contact",
      "baseline_geometry": true,
      "baseline_joint": true,
      "status": "completed",
      "precondition": {
        "steps": 50,
        "initial_nonbonded_min": 0.4897752577732644,
        "dmin": 1.0850813369220043,
        "max_bond_shift": 0.009599090242160768,
        "geometry_objective": 1.8012978933710055,
        "passed": true
      },
      "converged": true,
      "mace_steps": 45,
      "topology": "pcu",
      "target_recovered": true,
      "exact_linker_set": false,
      "geometry": false,
      "after": {
        "natoms": 131,
        "volume": 6531.567974819577,
        "dmin": 0.8964798458091481,
        "fragments": 5
      },
      "volume_ratio": 0.9993132984400784,
      "initial_mace_fmax": 11.615507,
      "final_mace_fmax": 0.194075,
      "initial_mace_energy": -847.669746,
      "final_mace_energy": -880.516663,
      "joint": false,
      "strict_pcu_joint": false
    },
    {
      "name": "control_BDC19",
      "reason": "positive BDC control",
      "baseline_geometry": true,
      "baseline_joint": true,
      "status": "completed",
      "precondition": {
        "steps": 0,
        "initial_nonbonded_min": 2.1504852205266767,
        "dmin": 1.0877867861715018,
        "max_bond_shift": 0.0,
        "geometry_objective": 0.0,
        "passed": true
      },
      "converged": true,
      "mace_steps": 6,
      "topology": "pcu",
      "target_recovered": true,
      "exact_linker_set": true,
      "geometry": true,
      "after": {
        "natoms": 53,
        "volume": 2176.789844906809,
        "dmin": 1.086782305226382,
        "fragments": 1
      },
      "volume_ratio": 1.000929950519449,
      "initial_mace_fmax": 2.029472,
      "final_mace_fmax": 0.143496,
      "initial_mace_energy": -358.200519,
      "final_mace_energy": -358.674776,
      "joint": true,
      "strict_pcu_joint": true
    }
  ]
}
```

原始基线保持冻结。这是已观察失败后的诊断试验；正面结果需在独立批次验证。几何目标与物理势能分开报告。

## 处置

本参数版本不进入主流程。两失败样本恢复0/2，四成功控制保持3/4。原始键长约束和短接触消除未保证后续分子类型保持；F11及F04出现额外自由基连接体类型。后续代码增加严格类型集合与预期拓扑校验，原34个新批次已接受U输出通过回归。独立输入/签名/落盘指标核验见AUDIT.json；决策见../DECISION.md。
