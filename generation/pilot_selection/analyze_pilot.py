#!/usr/bin/env python3
"""分析生产端选择试点：proxy_top5 vs random5 的真实 Widom 命中率。

用法:
  python3 analyze_pilot.py --merged pilot_merged.csv --selected selected.csv --out results.csv
"""
import argparse, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "widom_sih4"))
from ood_augment_eval import targets
from scipy.stats import spearmanr

ap = argparse.ArgumentParser()
ap.add_argument("--merged", required=True)
ap.add_argument("--selected", default=os.path.join(HERE, "selected.csv"))
ap.add_argument("--out", default=os.path.join(HERE, "results.csv"))
a = ap.parse_args()
H = pd.read_csv(a.merged)
T = targets(H)
S = pd.read_csv(a.selected)
M = S.merge(T, on="mof")
M["hit"] = M["S_CO2"] >= 0.3
cols = ["mof", "group", "topo", "pred_S_CO2", "S_CO2", "hit", "pred_S_N2", "S_N2", "pred_S_CH4", "S_CH4"]
M[cols].sort_values(["group", "S_CO2"], ascending=[True, False]).to_csv(a.out, index=False)
print(M[cols].round(3).to_string(index=False))
print("\n--- group summary ---")
print(M.groupby("group").agg(n=("mof", "size"), hits=("hit", "sum"),
                              median_logS_CO2=("S_CO2", "median"),
                              median_pred=("pred_S_CO2", "median")).round(3).to_string())
d = M[["pred_S_CO2", "S_CO2"]].dropna()
if len(d) >= 4:
    print(f"\npred vs actual logS_CO2: n={len(d)} rho={spearmanr(d.pred_S_CO2, d.S_CO2).statistic:.3f} "
          f"MAE={np.mean(np.abs(d.pred_S_CO2-d.S_CO2)):.3f}")
print(f"\n-> {a.out}")
