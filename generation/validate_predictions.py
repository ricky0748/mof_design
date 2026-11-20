#!/usr/bin/env python3
"""对比生产候选的代理预测与真实 Widom 标签（15 个验证候选）。

用法:
  python3 validate_predictions.py --merged val_merged.csv --scored scored_full.csv \
      --out validation.csv
"""
import argparse, os, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "widom_sih4"))
from ood_augment_eval import targets, ef10

TARGETS = ["K_SiH4", "S_N2", "S_CH4", "S_CO2"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", required=True)
    ap.add_argument("--scored", default=os.path.join(HERE, "scored_full.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "validation.csv"))
    a = ap.parse_args()
    H = pd.read_csv(a.merged)
    T = targets(H)
    S = pd.read_csv(a.scored)
    M = T.merge(S, on="mof", suffixes=("_actual", "_pred"))
    print(f"验证 {len(M)} 个候选")
    rows = []
    for t in TARGETS:
        pa = f"pred_{t}"
        if t not in M or pa not in M:
            continue
        d = M[[ "mof", t, pa]].dropna()
        if len(d) < 5:
            print("skip", t, len(d)); continue
        y, p = d[t].values, d[pa].values
        r2 = 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        rows.append(dict(target=t, n=len(d), R2=r2, rho=spearmanr(y, p).statistic,
                         EF10=ef10(y, p), MAE=float(np.mean(np.abs(y - p)))))
        print(rows[-1])
    R = pd.DataFrame(rows); R.to_csv(a.out.replace(".csv", "_metrics.csv"), index=False)
    cols = ["mof", "seed", "topo", "pred_S_CO2", "S_CO2", "pred_S_N2", "S_N2", "pred_S_CH4", "S_CH4"]
    cols = [c for c in cols if c in M.columns]
    print("\n", M.sort_values("pred_S_CO2", ascending=False)[cols].round(3).to_string(index=False))
    M.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
