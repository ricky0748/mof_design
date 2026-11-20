#!/usr/bin/env python3
"""汇总已回收的结果，输出报告用表格（支持部分完成）。"""
import os, sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
COND = {"T298_P1": "298 K / 1 bar", "T273_P1": "273 K / 1 bar",
        "T323_P1": "323 K / 1 bar", "T298_P5": "298 K / 5 bar"}

# ---------- multi ----------
mp = os.path.join(HERE, "multicomponent_results_partial.csv")
M = pd.read_csv(mp)
C = pd.read_csv(os.path.join(HERE, "multicomponent_candidates.csv"))
M = M[M.status == "ok"].merge(C[["mof", "arm", "binary_logS", "binary_q_SiH4", "binary_q_CO2"]], on="mof", how="left")
M["hit"] = (M.logS_CO2 >= 0.3) & (M.q_SiH4 <= 1.5) & (M.q_CO2 >= 0.001)
M["dlogS"] = M.logS_CO2 - M.binary_logS
M["rel_q"] = M.q_SiH4 / M.binary_q_SiH4
print("### MULTI")
print(M.groupby(["cond", "arm"]).agg(n=("hit", "size"), hits=("hit", "sum"),
      med_logS=("logS_CO2", "median"), med_q=("q_SiH4", "median"),
      med_qco2=("q_CO2", "median"), med_dlogS=("dlogS", "median"),
      med_relq=("rel_q", "median")).round(3).to_string())
print("\nmissing per cond (all candidates):")
for c in COND:
    have = set(M[M.cond == c].mof); allm = set(C.mof)
    print(c, sorted(allm - have))

# ---------- sensitivity ----------
rows = []
for v in ["eps_m20", "eps_p20", "sig_m01", "sig_p01"]:
    p = os.path.join(HERE, f"sih4_sensitivity_results_{v}.csv")
    d = pd.read_csv(p); d["variant"] = v; rows.append(d)
S = pd.concat(rows, ignore_index=True)
BS = pd.read_csv(os.path.join(HERE, "campaign_results_partial.csv"))
S = S.merge(BS.rename(columns={"logS_CO2": "base_logS", "q_SiH4": "base_q", "q_CO2": "base_qc"})[["mof", "base_logS", "base_q", "base_qc"]], on="mof", how="left")
S = S[S.status == "ok"]
S["hit"] = (S.logS_CO2 >= 0.3) & (S.q_SiH4 <= 1.5) & (S.q_CO2 >= 0.001)
S["basehit"] = (S.base_logS >= 0.3) & (S.base_q <= 1.5) & (S.base_qc >= 0.001)
print("\n### SENSITIVITY")
for v, g in S.groupby("variant"):
    rho = spearmanr(g.logS_CO2, g.base_logS).statistic if len(g) > 2 else np.nan
    print(v, "n", len(g), "hits", int(g.hit.sum()), "base", int(g.basehit.sum()),
          "flip_fail", int((g.basehit & ~g.hit).sum()), "flip_pass", int((~g.basehit & g.hit).sum()),
          "rho", round(rho, 3), "rel_q", round((g.q_SiH4 / g.base_q).median(), 3),
          "dlogS", round((g.logS_CO2 - g.base_logS).median(), 3))
P = S.pivot_table(index="mof", columns="variant", values="hit", aggfunc="first")
P["stable_hit"] = P.all(axis=1); P["stable_fail"] = (~P).all(axis=1)
print(P.to_string())

# ---------- shortlist ----------
B = pd.read_csv(os.path.join(HERE, "campaign_selected.csv")).merge(
    pd.read_csv(os.path.join(HERE, "campaign_results_partial.csv")), on="mof", how="left")
B["binary_hit"] = (B.logS_CO2 >= 0.3) & (B.q_SiH4 <= 1.5) & (B.q_CO2 >= 0.001)
m298 = M[M.cond == "T298_P1"].set_index("mof")
B["m4_hit"] = B.mof.map(m298.hit)
B["m4_qCO2"] = B.mof.map(m298.q_CO2)
B["m4_logS"] = B.mof.map(m298.logS_CO2)
B["m4_qSiH4"] = B.mof.map(m298.q_SiH4)
cand = B[B.binary_hit & (B.m4_hit == True)].copy()
cand = cand.sort_values(["m4_qCO2", "logS_CO2"], ascending=False)
print("\n### SHORTLIST (binary + 4-comp 298/1 bar)")
print(cand[["mof", "arm", "topo", "route", "logS_CO2", "q_SiH4", "q_CO2",
            "m4_logS", "m4_qSiH4", "m4_qCO2"]].round(3).to_string(index=False))
cand.to_csv(os.path.join(HERE, "shortlist.csv"), index=False)
