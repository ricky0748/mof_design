#!/usr/bin/env python3
"""分析 10 个命中候选的完整 GCMC：S_CO2、q_SiH4、q_CO2，并按登记标准判定。"""
import argparse, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

ap = argparse.ArgumentParser()
ap.add_argument("--gcmc", default=os.path.join(HERE, "gcmc_results.csv"))
ap.add_argument("--out", default=os.path.join(HERE, "gcmc_hits_results.csv"))
a = ap.parse_args()
G = pd.read_csv(a.gcmc)
S = pd.read_csv(os.path.join(ROOT, "generation/scored_full.csv"))
N = pd.read_csv(os.path.join(ROOT, "generation/scored_full_novelty.csv"))[["mof", "core_status"]]
W1 = pd.read_csv(os.path.join(HERE, "results.csv"))[["mof", "S_CO2"]].rename(columns={"S_CO2": "widom_logS_CO2"})
W2 = pd.read_csv(os.path.join(HERE, "feedback_results.csv"))[["mof", "S_CO2"]].rename(columns={"S_CO2": "widom_logS_CO2"})
W = pd.concat([W1, W2], ignore_index=True)
M = G.merge(S[["mof", "smiles", "topo", "pred_S_CO2"]], on="mof", how="left") \
     .merge(W, on="mof", how="left").merge(N, on="mof", how="left")
M = M[M.status == "ok"].copy()
M["hit"] = (M.logS_CO2 >= 0.3) & (M.q_SiH4 <= 1.5)
cols = ["mof", "topo", "smiles", "pred_S_CO2", "widom_logS_CO2", "q_SiH4", "q_CO2",
        "logS_CO2", "hit", "core_status"]
cols = [c for c in cols if c in M.columns]
M = M.sort_values("logS_CO2", ascending=False)
M[cols].to_csv(a.out, index=False)
print(M[cols].round(3).to_string(index=False))
print(f"\nvalid {len(M)}; GCMC logS_CO2 >=0.3: {int((M.logS_CO2>=0.3).sum())}; "
      f"with q_SiH4<=1.5: {int(M.hit.sum())}")
d = M[["widom_logS_CO2", "logS_CO2"]].dropna()
if len(d) >= 3:
    from scipy.stats import spearmanr
    print(f"Widom vs GCMC: n={len(d)} rho={spearmanr(d.widom_logS_CO2, d.logS_CO2).statistic:.3f} "
          f"MAE={np.mean(np.abs(d.widom_logS_CO2-d.logS_CO2)):.3f}")
print(f"-> {a.out}")
