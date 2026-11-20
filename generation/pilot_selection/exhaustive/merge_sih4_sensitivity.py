#!/usr/bin/env python3
"""合并 4 个 SiH4 LJ 变体的解析结果，并与基线（普查二元结果）对照。"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANTS = ["eps_m20", "eps_p20", "sig_m01", "sig_p01"]
rows = []
for v in VARIANTS:
    p = os.path.join(HERE, "sih4_sensitivity", f"results_{v}.csv")
    if not os.path.exists(p):
        continue
    d = pd.read_csv(p); d["variant"] = v; rows.append(d)
if not rows:
    raise SystemExit("no variant results")
M = pd.concat(rows, ignore_index=True)

base = pd.read_csv(os.path.join(HERE, "campaign_results_partial.csv"))
base = base.rename(columns={"logS_CO2": "base_logS", "q_SiH4": "base_q_SiH4", "q_CO2": "base_q_CO2"})
M = M.merge(base[["mof", "base_logS", "base_q_SiH4", "base_q_CO2"]], on="mof", how="left")
M["hit"] = (M.logS_CO2 >= 0.3) & (M.q_SiH4 <= 1.5) & (M.q_CO2 >= 0.001)
M["dlogS"] = M.logS_CO2 - M.base_logS
M["rel_qSiH4"] = M.q_SiH4 / M.base_q_SiH4
out = os.path.join(HERE, "sih4_sensitivity_results.csv")
M.to_csv(out, index=False)
print(M.groupby("variant").agg(n=("hit", "size"), hits=("hit", "sum"),
      med_logS=("logS_CO2", "median"), med_qSiH4=("q_SiH4", "median"),
      med_dlogS=("dlogS", "median"), med_rel_qSiH4=("rel_qSiH4", "median")).round(3).to_string())
print("->", out)
