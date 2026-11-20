#!/usr/bin/env python3
"""在 PORMAKE 组装结构上检验代理模型的分布外富集能力（np 组：SiH4/H2/Ar/CH4）。

训练：CRAFTED 690 个 MOF，特征用 zeo_features.py 重算的 G 组（与 OOD 同一版 Zeo++、同一口径）。
测试：41 个组装结构，Widom 用同一套 np 组参数（298 K、5000 cycles、12.8 Å、UFF、无电荷）。
指标：R²、Spearman ρ、EF10（预测前 10% 命中真实前 10% 的比例除以 0.1）。

用法:
  python3 ood_assembly_eval.py --crafted-zeo crafted_zeo.csv --henry results/henry_wide.csv \
      --ood-zeo ood_zeo.csv --ood-henry ood_results/henry_wide.csv --out results/ood_assembly
"""
import argparse, os, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import lightgbm as lgb
warnings.filterwarnings("ignore")

G = ["D_is", "D_fs", "D_isfs", "ASA_m2_cm3", "ASA_m2_g", "NASA_m2_cm3", "NASA_m2_g",
     "Unitcell_volume", "Density", "AV_Volume_fraction", "AV_cm3_g",
     "NAV_Volume_fraction", "NAV_cm3_g", "n_pockets"]
TARGETS = ["K_SiH4", "S_H2", "S_Ar", "S_CH4"]


def ef10(y, p):
    k = max(1, int(round(0.1 * len(y))))
    return len(set(np.argsort(-y)[:k]) & set(np.argsort(-p)[:k])) / k / 0.1


def targets(H, max_err=0.5):
    T = pd.DataFrame({"mof": H.mof})
    rel = lambda m: H[f"Kerr_{m}"] / H[f"K_{m}"]
    T["K_SiH4"] = np.log10(H.K_SiH4.clip(lower=1e-30)).where(rel("SiH4") < max_err)
    for i in ["H2", "Ar", "CH4"]:
        ok = (rel(i) < max_err) & (rel("SiH4") < max_err)
        T[f"S_{i}"] = np.log10(H[f"K_{i}"].clip(lower=1e-30) / H.K_SiH4.clip(lower=1e-30)).where(ok)
    return T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crafted-zeo", required=True)
    ap.add_argument("--henry", required=True)
    ap.add_argument("--ood-zeo", required=True)
    ap.add_argument("--ood-henry", required=True)
    ap.add_argument("--out", default="results/ood_assembly")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)

    C = pd.read_csv(a.crafted_zeo).rename(columns={"name": "mof", "Density_sa": "Density"})
    H = pd.read_csv(a.henry)
    H = H[(H.status_np == "ok") & (H.status_pol == "ok")]
    T = targets(H)
    L = T.merge(C, on="mof")
    print(f"CRAFTED train: {len(L)} rows, zeo errors: {L[G].isna().any(axis=1).sum()}")

    O = pd.read_csv(a.ood_zeo).rename(columns={"name": "mof", "Density_sa": "Density"})
    HO = pd.read_csv(a.ood_henry)
    TO = targets(HO)
    LO = TO.merge(O, on="mof")
    print(f"OOD test: {len(LO)} rows, zeo errors: {LO[G].isna().any(axis=1).sum()}")

    rows = []
    for t in TARGETS:
        tr = L[L[t].notna() & L[G].notna().all(axis=1)]
        te = LO[LO[t].notna() & LO[G].notna().all(axis=1)]
        if len(te) < 5:
            print("skip", t, len(te)); continue
        m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=15,
                              min_child_samples=10, subsample=0.8, subsample_freq=1,
                              colsample_bytree=0.6, reg_lambda=1.0, random_state=0, verbose=-1)
        m.fit(tr[G].values, tr[t].values)
        p = m.predict(te[G].values); y = te[t].values
        r2 = 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        rows.append(dict(target=t, n_train=len(tr), n_test=len(te), R2=r2,
                         rho=spearmanr(y, p).statistic, EF10=ef10(y, p)))
        print(rows[-1], flush=True)
        d = te[["mof", t]].copy(); d["pred"] = p; d.to_csv(os.path.join(a.out, f"pred_{t}.csv"), index=False)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "metrics.csv"), index=False)
    print("\n", R.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
