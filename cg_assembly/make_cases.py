"""生成验证用例：cases/<case>_s<seed>.npz、cases/cases.csv、run_all.sh。

用例（预测见 worklog "预测先登记"）:
  C0_patchy3_rod   cg_patchy3 原版（legacy 势）+ v3 参数 AA=8/EC=20：复现检查，应与 mof303 结论一致
  C0b_patchy3_single 同上但改为单占位位点：看 mof303 的"配位 = 4、网络贯通"结论在去掉多占之后是否还成立
  C1_PZDC_rod      锚点规则自动生成的 PZDC 几何 + rod
  C2_BDC_pw        对苯二甲酸 + Cu 桨轮            （实验：sql 层，4 元环）
  C3_mBDC_pw       间苯二甲酸 + Cu 桨轮            （实验：kgm 层或 MOP-1 立方八面体笼，都含 3 元环）
  C4_BDC_oct       对苯二甲酸 + Zn4O               （实验：pcu，4 元环）
  C5_BTC_pw        均苯三甲酸 + Cu 桨轮            （实验：tbo/HKUST-1；探索性，不登记定量预测）
"""
import os, sys, csv, json
import numpy as np
from cg_build import cg_linker_geometry, patchy3_pzdc, calibrate_sigma, build, scale, NODE_FAMILY

SEEDS = [1, 2, 3]
CASES = [
    ("C0_patchy3_rod", None, "Al_rod", 36, "patchy3", "legacy"),
    ("C0b_patchy3_single", None, "Al_rod", 36, "patchy3", "single"),
    ("C1_PZDC_rod", "OC(=O)c1cc(C(=O)O)[nH]n1", "Al_rod", 36, "patchy3", "single"),
    ("C2_BDC_pw", "OC(=O)c1ccc(cc1)C(=O)O", "Cu_paddlewheel", 36, "real", "single"),
    ("C3_mBDC_pw", "OC(=O)c1cccc(c1)C(=O)O", "Cu_paddlewheel", 36, "real", "single"),
    ("C4_BDC_oct", "OC(=O)c1ccc(cc1)C(=O)O", "Zn4O", 27, "real", "single"),
    ("C5_BTC_pw", "OC(=O)c1cc(cc(c1)C(=O)O)C(=O)O", "Cu_paddlewheel", 36, "real", "single"),
]


def main(out="cases"):
    os.makedirs(out, exist_ok=True)
    sigma = calibrate_sigma()
    rows = []
    for name, smi, node, n_m, size, patch in CASES:
        lig = patchy3_pzdc() if smi is None else cg_linker_geometry(smi, node, sigma)
        case = dict(name=name, linker=lig, family=NODE_FAMILY[node])
        for s in SEEDS:
            spec = build(case, n_m, s, sigma, node_size=size, patch=patch)
            fn = os.path.join(out, f"{name}_s{s}.npz"); np.savez(fn, **spec)
            m = json.loads(str(spec["meta"]))
        R = [p for t, p in lig["beads"] if t == "R"]
        Cb = [p for t, p in lig["beads"] if t == "C"]
        ang = [round(m["angle_par"][t]["t0"] * 180 / np.pi, 1) for t in m["angle_types"] if t.startswith("T")]
        rows.append(dict(case=name, patch=patch, smiles=lig["smiles"], node=node, family=m["family"], node_size=size, n_m=m["n_m"], n_l=m["n_l"],
                         n_beads=len(spec["position"]), L=round(m["L"], 2), node_d=round(m["node_d"], 3),
                         n_R=len(R), n_C=len(Cb), linker_angles_deg=ang,
                         linker_bonds=[round(m["bond_par"][t]["r0"], 3) for t in m["bond_types"] if t.startswith("L")]))
        print(rows[-1])
    with open(os.path.join(out, "cases.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump(dict(sigma_A=sigma), open(os.path.join(out, "sigma.json"), "w"))
    with open("run_all.sh", "w") as f:
        f.write("#!/bin/bash\n# 在服务器 hoomd5 环境中运行：conda activate hoomd5 && bash run_all.sh [并行数]\n")
        f.write("# 每个用例 3 个随机种子；单个 200k 步，CPU。\nP=${1:-6}\nmkdir -p runs results\n")
        f.write("# 冒烟测试：每类节点各跑 2000 步，确认 API/参数无误再全量\n")
        f.write("for c in C0_patchy3_rod_s1 C2_BDC_pw_s1 C4_BDC_oct_s1 C5_BTC_pw_s1; do python run_cg.py cases/$c.npz smoke 2000 || exit 1; done\n")
        f.write("ls cases/*.npz | xargs -P $P -I{} sh -c 'n=$(basename {} .npz); python run_cg.py {} runs > runs/$n.out 2>&1 && "
                "python analyze_cg.py {} runs/$n.gsd --json results/$n.json > /dev/null'\n")
        f.write("python summarize.py results > results/summary.txt && cat results/summary.txt\n")
    print("sigma =", round(sigma, 3), "Å")


if __name__ == "__main__":
    main(*sys.argv[1:])
