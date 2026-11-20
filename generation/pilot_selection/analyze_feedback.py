#!/usr/bin/env python3
"""分析反馈批次：真实 Widom 命中率，并与初始 proxy_top5 / random5 对比。"""
import argparse, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "widom_sih4"))
from ood_augment_eval import targets
from scipy.stats import spearmanr

ap = argparse.ArgumentParser()
ap.add_argument("--merged", default=os.path.join(HERE, "feedback_merged.csv"))
ap.add_argument("--selected", default=os.path.join(HERE, "feedback_selected.csv"))
ap.add_argument("--out", default=os.path.join(HERE, "feedback_results.csv"))
a = ap.parse_args()
H = pd.read_csv(a.merged)
T = targets(H)
S = pd.read_csv(a.selected)
M = S.merge(T, on="mof")
M["hit"] = M["S_CO2"] >= 0.3
cols = ["mof", "topo", "smiles", "pred_mean", "pred_std", "ucb", "S_CO2", "hit", "S_N2", "S_CH4"]
cols = [c for c in cols if c in M.columns]
M[cols].sort_values("S_CO2", ascending=False).to_csv(a.out, index=False)
print(M[cols].round(3).to_string(index=False))
print(f"\nfeedback hits: {int(M.hit.sum())}/{len(M)}; median logS_CO2 {M.S_CO2.median():.3f}")
d = M[["pred_mean", "S_CO2"]].dropna()
if len(d) >= 4:
    print(f"pred_mean vs actual: n={len(d)} rho={spearmanr(d.pred_mean, d.S_CO2).statistic:.3f} "
          f"MAE={np.mean(np.abs(d.pred_mean-d.S_CO2)):.3f}")
print(f"\n-> {a.out}")
