#!/usr/bin/env python3
"""合并首轮 5/臂与扩展 5/臂，给出 new-5、combined-10 和阈值敏感性。"""
import argparse, os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--first", default=os.path.join(HERE, "fair_compare_results.csv"))
ap.add_argument("--ext-gcmc", default=os.path.join(HERE, "fair_ext_results.csv"))
ap.add_argument("--ext-selected", default=os.path.join(HERE, "fair_compare_extension_selected.csv"))
ap.add_argument("--out", default=os.path.join(HERE, "fair_compare_combined.csv"))
a = ap.parse_args()

F = pd.read_csv(a.first); F["round"] = "initial"
S = pd.read_csv(a.ext_selected); E = pd.read_csv(a.ext_gcmc)
E = S.merge(E, on="mof", how="left")
E["hit"] = (E.logS_CO2 >= 0.3) & (E.q_SiH4 <= 1.5) & (E.q_CO2 >= 0.001)
E["round"] = "extension"
cols = ["round", "arm", "mof", "smiles", "pred_mean", "pred_std", "ucb",
        "q_SiH4", "q_CO2", "logS_CO2", "hit"]
M = pd.concat([F[cols], E[cols]], ignore_index=True)
M.to_csv(a.out, index=False)
print("=== summary by arm/round ===")
print(M.groupby(["arm", "round"]).agg(n=("mof", "size"), hits=("hit", "sum"),
      median_logS=("logS_CO2", "median"), median_q_SiH4=("q_SiH4", "median"),
      median_q_CO2=("q_CO2", "median")).round(3).to_string())
print("\n=== combined 10/arm ===")
print(M.groupby("arm").agg(n=("mof", "size"), hits=("hit", "sum"),
      median_logS=("logS_CO2", "median")).round(3).to_string())
print("\n=== q_SiH4 threshold sensitivity (logS>=0.3, q_CO2>=0.001) ===")
for T in [1.5, 2.0, 2.5]:
    M[f"h{T}"] = (M.logS_CO2 >= 0.3) & (M.q_CO2 >= 0.001) & (M.q_SiH4 <= T)
    print(f"q_SiH4<={T}:", M.groupby("arm")[f"h{T}"].sum().to_dict(),
          " / n", M.groupby("arm").size().to_dict())
print(f"\n-> {a.out}")
