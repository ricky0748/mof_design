#!/usr/bin/env python3
"""对比代理预测、Widom Henry 选择性、完整 GCMC 选择性（298 K, 1 bar, 1000 ppm CO2）。

用法: python3 compare_gcmc.py --gcmc gcmc_results.csv --scored scored_full.csv \
          --validation validation.csv --out gcmc_vs_proxy.csv
"""
import argparse, os
import numpy as np, pandas as pd
from scipy.stats import spearmanr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gcmc", default="gcmc_results.csv")
    ap.add_argument("--scored", default="scored_full.csv")
    ap.add_argument("--validation", default="validation.csv")
    ap.add_argument("--out", default="gcmc_vs_proxy.csv")
    a = ap.parse_args()
    G = pd.read_csv(a.gcmc)
    S = pd.read_csv(a.scored)[["mof", "seed", "topo", "novelty_tier", "pred_S_CO2", "pred_S_N2", "pred_S_CH4"]]
    V = pd.read_csv(a.validation)[["mof", "S_CO2"]].rename(columns={"S_CO2": "S_CO2_widom"})
    M = G.merge(S, on="mof", how="left").merge(V, on="mof", how="left")
    M = M[M.status == "ok"].copy()
    print(f"有效 GCMC: {len(M)}")
    for col, name in [("pred_S_CO2", "代理预测"), ("S_CO2_widom", "Widom Henry")]:
        d = M[["logS_CO2", col]].dropna()
        if len(d) >= 4:
            print(f"GCMC vs {name}: n={len(d)} rho={spearmanr(d.logS_CO2, d[col]).statistic:.3f} "
                  f"R2={1-((d.logS_CO2-d[col])**2).sum()/((d.logS_CO2-d.logS_CO2.mean())**2).sum():.3f} "
                  f"MAE={np.mean(np.abs(d.logS_CO2-d[col])):.3f}")
    cols = ["mof", "seed", "topo", "pred_S_CO2", "S_CO2_widom", "logS_CO2", "q_SiH4", "q_CO2", "novelty_tier"]
    cols = [c for c in cols if c in M.columns]
    print("\n", M.sort_values("logS_CO2", ascending=False)[cols].round(3).to_string(index=False))
    M.to_csv(a.out, index=False)
    print(f"\n-> {a.out}")


if __name__ == "__main__":
    main()
