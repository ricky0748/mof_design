#!/usr/bin/env python3
"""分析同预算命中密度对照：known_holdout vs generated。"""
import argparse, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--gcmc", default=os.path.join(HERE, "fair_gcmc_results.csv"))
ap.add_argument("--selected", default=os.path.join(HERE, "fair_compare_selected.csv"))
ap.add_argument("--out", default=os.path.join(HERE, "fair_compare_results.csv"))
a = ap.parse_args()
G = pd.read_csv(a.gcmc); S = pd.read_csv(a.selected)
M = S.merge(G, on="mof", how="left")
M["hit"] = (M.logS_CO2 >= 0.3) & (M.q_SiH4 <= 1.5) & (M.q_CO2 >= 0.001)
M = M[M.status == "ok"].sort_values(["arm", "logS_CO2"], ascending=[True, False])
cols = ["arm", "mof", "smiles", "pred_mean", "pred_std", "ucb", "q_SiH4", "q_CO2", "logS_CO2", "hit"]
cols = [c for c in cols if c in M.columns]
M[cols].to_csv(a.out, index=False)
print(M[cols].round(3).to_string(index=False))
print("\n--- hit rate by arm ---")
print(M.groupby("arm").agg(n=("mof", "size"), hits=("hit", "sum"),
                            median_logS=("logS_CO2", "median"),
                            median_q_SiH4=("q_SiH4", "median"),
                            median_q_CO2=("q_CO2", "median")).round(3).to_string())
print(f"\n-> {a.out}")
