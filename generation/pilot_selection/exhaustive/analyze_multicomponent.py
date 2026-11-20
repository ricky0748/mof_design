#!/usr/bin/env python3
"""分析多组分 / 过程条件结果：逐条件命中率、与二元基线的取舍变化。"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
COND_NAME = {"T298_P1": "298 K / 1 bar", "T273_P1": "273 K / 1 bar",
             "T323_P1": "323 K / 1 bar", "T298_P5": "298 K / 5 bar"}

R = pd.read_csv(os.path.join(HERE, "multicomponent_results.csv"))
C = pd.read_csv(os.path.join(HERE, "multicomponent_candidates.csv"))
R = R[R.status == "ok"].copy()
R["hit"] = (R.logS_CO2 >= 0.3) & (R.q_SiH4 <= 1.5) & (R.q_CO2 >= 0.001)
M = R.merge(C[["mof", "arm", "binary_logS", "binary_q_SiH4", "binary_q_CO2"]], on="mof", how="left")
M["dlogS"] = M.logS_CO2 - M.binary_logS
M["rel_qSiH4"] = M.q_SiH4 / M.binary_q_SiH4
M["cond_name"] = M.cond.map(COND_NAME)
M.to_csv(os.path.join(HERE, "multicomponent_analysis.csv"), index=False)

summary = M.groupby(["cond_name", "arm"]).agg(
    n=("hit", "size"), hits=("hit", "sum"), hit_rate=("hit", "mean"),
    med_logS=("logS_CO2", "median"), med_qSiH4=("q_SiH4", "median"),
    med_qCO2=("q_CO2", "median"), med_dlogS=("dlogS", "median"),
    med_rel_qSiH4=("rel_qSiH4", "median")).round(3)
print(summary.to_string())

lines = ["| 条件 | 臂 | n | 命中 | 中位 logS | 中位 q_SiH4 | 中位 q_CO2 | ΔlogS | q_SiH4 相对基线 |",
         "|---|---|---|---|---|---|---|---|---|"]
for (cond, arm), r in summary.iterrows():
    lines.append(f"| {cond} | {arm} | {int(r.n)} | {int(r.hits)} | {r.med_logS:.3f} | "
                 f"{r.med_qSiH4:.3f} | {r.med_qCO2:.4f} | {r.med_dlogS:+.3f} | {r.med_rel_qSiH4:.2f}× |")
open(os.path.join(HERE, "multicomponent_summary.md"), "w", encoding="utf-8").write("\n".join(lines))
print("-> multicomponent_analysis.csv / multicomponent_summary.md")
