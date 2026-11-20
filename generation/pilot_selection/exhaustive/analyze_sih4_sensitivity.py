#!/usr/bin/env python3
"""分析 SiH4 LJ 敏感性：达标变化 + 排名变化 + 稳定/翻转候选。"""
import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
M = pd.read_csv(os.path.join(HERE, "sih4_sensitivity_results.csv"))
M["hit"] = (M.logS_CO2 >= 0.3) & (M.q_SiH4 <= 1.5) & (M.q_CO2 >= 0.001)
VAR = ["eps_m20", "eps_p20", "sig_m01", "sig_p01"]

rows = []
for v, g in M.groupby("variant"):
    g = g[g.status == "ok"]
    if not len(g):
        continue
    base_hit = (g.base_logS >= 0.3) & (g.base_q_SiH4 <= 1.5) & (g.base_q_CO2 >= 0.001)
    rho = spearmanr(g.logS_CO2, g.base_logS).statistic if len(g) > 2 else np.nan
    rows.append(dict(variant=v, n=len(g), hits=int(g.hit.sum()),
                     base_hits=int(base_hit.sum()),
                     flips_to_fail=int((base_hit & ~g.hit).sum()),
                     flips_to_pass=int((~base_hit & g.hit).sum()),
                     spearman_logS=round(rho, 3),
                     med_rel_qSiH4=round((g.q_SiH4 / g.base_q_SiH4).median(), 3),
                     med_dlogS=round((g.logS_CO2 - g.base_logS).median(), 3)))
S = pd.DataFrame(rows)
print(S.to_string(index=False))
S.to_csv(os.path.join(HERE, "sih4_sensitivity_summary.csv"), index=False)

# 每个候选在 4 个变体下是否始终达标
P = M[M.status == "ok"].pivot_table(index="mof", columns="variant", values="hit", aggfunc="first")
if len(P.columns):
    P["stable_hit"] = P[VAR].all(axis=1)
    P["stable_fail"] = (~P[VAR]).all(axis=1)
    P["flips"] = ~(P.stable_hit | P.stable_fail)
    P.to_csv(os.path.join(HERE, "sih4_sensitivity_consistency.csv"))
    print("\nconsistency:")
    print(P.to_string())

lines = ["| 变体 | n | 达标 | 基线达标 | 基线→失败 | 基线→达标 | Spearman(logS) | q_SiH4 相对 | ΔlogS |",
         "|---|---|---|---|---|---|---|---|---|"]
for _, r in S.iterrows():
    lines.append(f"| {r.variant} | {r.n} | {r.hits} | {r.base_hits} | {r.flips_to_fail} | "
                 f"{r.flips_to_pass} | {r.spearman_logS} | {r.med_rel_qSiH4:.2f}× | {r.med_dlogS:+.3f} |")
open(os.path.join(HERE, "sih4_sensitivity_summary.md"), "w", encoding="utf-8").write("\n".join(lines))
print("-> sih4_sensitivity_summary.csv/.md")
