#!/usr/bin/env python3
"""金属留一法（leave-one-metal-out）分布偏移检验。

训练集用除目标金属外的所有 MOF，测试集只用该金属的 MOF，衡量代理模型在未见金属化学上的
排序/富集能力。特征只用 G 和 G+RAC（不含金属 one-hot），避免"测试集金属在训练集里没有对应
哑变量"这种人为泄漏/缺失。结果写到 results/ood_metal_holdout.csv。

用法:
  python3 ood_metal_holdout.py --henry results/henry_wide.csv \
      --crafted <CRAFTED-2.0.0> --chem ../r2_probe/chem_features_DDEC.csv --out results
依赖: numpy pandas scipy scikit-learn lightgbm
"""
import argparse, os, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import lightgbm as lgb
warnings.filterwarnings("ignore")
IMPS = ["H2", "N2", "O2", "Ar", "CH4", "CO", "CO2"]
TARGETS = ["K_SiH4"] + [f"S_{i}" for i in IMPS] + ["S_bottleneck"]


def ef10(y, p):
    k = max(1, int(round(0.1 * len(y))))
    return len(set(np.argsort(-y)[:k]) & set(np.argsort(-p)[:k])) / k / 0.1


def fit_eval(Xtr, ytr, Xte, yte, seed=0):
    m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=15,
                          min_child_samples=10, subsample=0.8, subsample_freq=1,
                          colsample_bytree=0.6, reg_lambda=1.0, random_state=seed, verbose=-1)
    m.fit(Xtr, ytr)
    p = m.predict(Xte)
    r2 = 1 - ((yte - p) ** 2).sum() / ((yte - yte.mean()) ** 2).sum()
    rho = spearmanr(yte, p).statistic if len(yte) >= 3 else np.nan
    return r2, rho, ef10(yte, p)


def build_targets(H, max_rel_err=0.5):
    T = pd.DataFrame({"mof": H.mof})
    rel = lambda m: H[f"Kerr_{m}"] / H[f"K_{m}"]
    T["K_SiH4"] = np.log10(H.K_SiH4.clip(lower=1e-30)).where(rel("SiH4") < max_rel_err)
    for i in IMPS:
        ok = (rel(i) < max_rel_err) & (rel("SiH4") < max_rel_err)
        T[f"S_{i}"] = np.log10(H[f"K_{i}"].clip(lower=1e-30) / H.K_SiH4.clip(lower=1e-30)).where(ok)
    sub = T[[f"S_{i}" for i in IMPS]].abs()
    T["S_bottleneck"] = sub.min(axis=1, skipna=False)
    return T


def build_features(crafted, chem):
    g = pd.read_csv(os.path.join(crafted, "RAC_DBSCAN", "CRAFTED_MOF_geometric.csv")).rename(columns={"FrameworkName": "mof"})
    r = pd.read_csv(os.path.join(crafted, "RAC_DBSCAN", "CRAFTED_MOF_full_featurization_frame.csv")).rename(columns={"FrameworkName": "mof"})
    c = pd.read_csv(chem)[["mof", "metal"]]
    X = g.merge(r, on="mof").merge(c, on="mof")
    G = [x for x in g.columns if x != "mof"]
    R = [x for x in r.columns if x != "mof"]
    return X, {"G": G, "G+RAC": G + R}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--henry", default="results/henry_wide.csv")
    ap.add_argument("--crafted", required=True)
    ap.add_argument("--chem", default="../r2_probe/chem_features_DDEC.csv")
    ap.add_argument("--out", default="results")
    ap.add_argument("--min-test", type=int, default=20, help="测试金属最少样本数")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    H = pd.read_csv(a.henry)
    H = H[(H.status_np == "ok") & (H.status_pol == "ok")].copy()
    T = build_targets(H)
    X, FS = build_features(a.crafted, a.chem)
    L = T.merge(X, on="mof")

    groups = {m: (L.metal == m) for m in L.metal.value_counts().index if (L.metal == m).sum() >= a.min_test}
    groups["non-Zn"] = L.metal != "Zn"
    rows = []
    for name, mask in groups.items():
        for fs, cols in FS.items():
            for t in TARGETS:
                tr = L[~mask & L[t].notna()]
                te = L[mask & L[t].notna()]
                if len(tr) < 30 or len(te) < 5:
                    continue
                r2, rho, e = fit_eval(tr[cols].values.astype(float), tr[t].values,
                                      te[cols].values.astype(float), te[t].values)
                rows.append(dict(holdout=name, n_train=len(tr), n_test=len(te), target=t,
                                 features=fs, R2=r2, rho=rho, EF10=e))
                print(rows[-1], flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(a.out, "ood_metal_holdout.csv"), index=False)
    print("\n=== mean over targets (excluding S_bottleneck) ===")
    print(R[R.target != "S_bottleneck"].groupby(["holdout", "features"])[["R2", "rho", "EF10"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
