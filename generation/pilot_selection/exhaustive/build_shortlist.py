#!/usr/bin/env python3
"""汇总二元普查、多组分、敏感性、novelty，生成最终候选短名单。"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

base = pd.read_csv(os.path.join(HERE, "campaign_results_partial.csv"))
sel = pd.read_csv(os.path.join(HERE, "campaign_selected.csv"))
B = sel.merge(base, on="mof", how="left")
B["binary_hit"] = (B.logS_CO2 >= 0.3) & (B.q_SiH4 <= 1.5) & (B.q_CO2 >= 0.001)

# 多组分（298 K / 1 bar 为主）
mp = os.path.join(HERE, "multicomponent_results.csv")
if os.path.exists(mp):
    M = pd.read_csv(mp)
    M = M[M.status == "ok"]
    M["hit"] = (M.logS_CO2 >= 0.3) & (M.q_SiH4 <= 1.5) & (M.q_CO2 >= 0.001)
    m298 = M[M.cond == "T298_P1"][["mof", "logS_CO2", "q_SiH4", "q_CO2", "S_N2", "S_CH4", "hit"]]
    m298 = m298.rename(columns={"logS_CO2": "m4_logS", "q_SiH4": "m4_qSiH4",
                                "q_CO2": "m4_qCO2", "hit": "m4_hit"})
    cond_hits = M.groupby("mof").hit.sum().rename("n_cond_hit")
    B = B.merge(m298, on="mof", how="left").merge(cond_hits, on="mof", how="left")
else:
    B["m4_hit"] = None

# 力场敏感性稳定性
sp = os.path.join(HERE, "sih4_sensitivity_consistency.csv")
if os.path.exists(sp):
    S = pd.read_csv(sp)
    if "stable_hit" in S.columns:
        B = B.merge(S[["mof", "stable_hit"]], on="mof", how="left")

# novelty（top 5 已查）
nov = {}
for f in ("novelty_csd_top5.csv", "novelty_core2024_top5.csv"):
    p = os.path.join(HERE, f)
    if os.path.exists(p):
        d = pd.read_csv(p)
        for c in d.candidate.unique() if len(d) else []:
            nov[c] = "match"
B["novelty_top5"] = B.mof.map(nov).fillna("")

B["short"] = B.binary_hit & (B.get("m4_hit", True) == True)
cand = B[B["short"]].copy()
cand = cand.sort_values(["m4_qCO2", "logS_CO2"], ascending=False)
cols = [c for c in ["mof", "arm", "topo", "route", "logS_CO2", "q_SiH4", "q_CO2",
                    "m4_logS", "m4_qSiH4", "m4_qCO2", "n_cond_hit", "stable_hit",
                    "novelty_top5"] if c in cand.columns]
cand[cols].to_csv(os.path.join(HERE, "shortlist.csv"), index=False)
print(cand[cols].round(3).to_string(index=False))
print("->", os.path.join(HERE, "shortlist.csv"))
