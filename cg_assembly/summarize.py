"""汇总 results/*.json：每个用例 3 个种子的均值 ± 标准差（取末 10 帧平均），并对照登记的预测。"""
import sys, json, glob, collections
import numpy as np

KEYS = ["C_per_node", "frac_E_bound", "frac_bridging", "frac_intra_node", "largest_component_frac", "n_chains", "frac3", "frac4", "frac6", "n_rings", "n_periodic_loops"]
d = collections.defaultdict(list)
for f in sorted(glob.glob(f"{sys.argv[1] if len(sys.argv) > 1 else 'results'}/*.json")):
    r = json.load(open(f)); d[r["case"]].append(r)
print("case".ljust(16) + "".join(k[:14].rjust(15) for k in KEYS))
agg = {}
for c, rs in sorted(d.items()):
    row = {}
    for k in KEYS:
        v = [r["mean_last"].get(k) for r in rs if r["mean_last"].get(k) is not None]
        row[k] = (np.mean(v), np.std(v)) if v else (np.nan, np.nan)
    agg[c] = row
    print(c.ljust(16) + "".join(f"{m:8.3f}±{s:5.3f}".rjust(15) for m, s in row.values()) + f"   (n={len(rs)})")
    for r in rs:
        print("   seed", r["seed"], "末帧环分布", r["final"]["rings"])
g = lambda c, k: agg.get(c, {}).get(k, (np.nan,))[0]
print("\n登记预测核对（见 worklog）:")
checks = [
    ("P1 C0 复现 mof303（legacy 势）：每节点 C ≥ 3.9、最大连通 ≥ 0.9、E 位点占用率 ≤ 0.8（多占复现）",
     g("C0_patchy3_rod", "C_per_node") >= 3.9 and g("C0_patchy3_rod", "largest_component_frac") >= .9 and g("C0_patchy3_rod", "frac_E_bound") <= .8),
    ("P2 C0b 单占位：E 位点占用率 ≥ 0.9、最大连通 ≥ 0.5", g("C0b_patchy3_single", "frac_E_bound") >= .9 and g("C0b_patchy3_single", "largest_component_frac") >= .5),
    ("P3 C2 BDC/桨轮：frac4 ≥ 0.4 且 frac3 ≤ 0.15", g("C2_BDC_pw", "frac4") >= .4 and g("C2_BDC_pw", "frac3") <= .15),
    ("P4 C3 mBDC/桨轮：frac3 比 C2 高 ≥ 0.2", g("C3_mBDC_pw", "frac3") - g("C2_BDC_pw", "frac3") >= .2),
    ("P5 C4 BDC/Zn4O：frac4 ≥ 0.4 且 frac3 ≤ 0.1", g("C4_BDC_oct", "frac4") >= .4 and g("C4_BDC_oct", "frac3") <= .1),
]
for name, ok in checks:
    print(("  ✔ " if ok else "  ✘ ") + name)
print("\n判定规则（登记）：P3 与 P4 都不成立 → 模型分不出线性/弯曲配体，不接入工作流。")
