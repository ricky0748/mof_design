#!/usr/bin/env python3
"""检验「用 41 个组装结构扩训能否修复 OOD」：训练 CRAFTED / CRAFTED+41，测试剩余 91 个组装结构。

用法:
  python3 ood_augment_eval.py --crafted-zeo results/crafted_zeo.csv --henry results/henry_wide.csv \
      --pilot-zeo results/ood_zeo.csv --pilot-henry results/ood_henry_wide.csv \
      --test-zeo results/holdout_zeo.csv --test-henry results/holdout_henry_wide.csv \
      --out results/ood_augment
"""
import argparse, os, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import lightgbm as lgb
warnings.filterwarnings("ignore")

G = ["D_is", "D_fs", "D_isfs", "ASA_m2_cm3", "ASA_m2_g", "NASA_m2_cm3", "NASA_m2_g",
     "Unitcell_volume", "Density", "AV_Volume_fraction", "AV_cm3_g",
     "NAV_Volume_fraction", "NAV_cm3_g", "n_pockets"]
IMPS = ["H2", "N2", "O2", "Ar", "CH4", "CO", "CO2"]
TARGETS = ["K_SiH4", "S_H2", "S_Ar", "S_CH4"]          # np 组默认
TARGETS_ALL = ["K_SiH4"] + [f"S_{i}" for i in IMPS]


def ef10(y, p):
    k = max(1, int(round(0.1 * len(y))))
    return len(set(np.argsort(-y)[:k]) & set(np.argsort(-p)[:k])) / k / 0.1


def targets(H, max_err=0.5):
    """把 henry_wide 的 K/Kerr 转成 log10 目标量；缺列的分子自动跳过。"""
    T = pd.DataFrame({"mof": H.mof})
    rel = lambda m: H[f"Kerr_{m}"] / H[f"K_{m}"]
    T["K_SiH4"] = np.log10(H.K_SiH4.clip(lower=1e-30)).where(rel("SiH4") < max_err)
    for i in IMPS:
        if f"K_{i}" not in H:
            continue
        ok = (rel(i) < max_err) & (rel("SiH4") < max_err)
        T[f"S_{i}"] = np.log10(H[f"K_{i}"].clip(lower=1e-30) / H.K_SiH4.clip(lower=1e-30)).where(ok)
    return T


def load(features, henry):
    X = pd.read_csv(features).rename(columns={"name": "mof", "Density_sa": "Density"})
    H = pd.read_csv(henry)
    T = targets(H)
    return T.merge(X, on="mof")


def fit(Xtr, ytr, w=None, seed=0):
    m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=15,
                          min_child_samples=10, subsample=0.8, subsample_freq=1,
                          colsample_bytree=0.6, reg_lambda=1.0, random_state=seed, verbose=-1)
    m.fit(Xtr, ytr, sample_weight=w)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crafted-zeo", required=True); ap.add_argument("--henry", required=True)
    ap.add_argument("--pilot-zeo", required=True); ap.add_argument("--pilot-henry", required=True)
    ap.add_argument("--test-zeo", required=True); ap.add_argument("--test-henry", required=True)
    ap.add_argument("--out", default="results/ood_augment")
    ap.add_argument("--targets", nargs="*", default=TARGETS,
                    help="默认 np 组；pol 组用 K_SiH4 S_N2 S_O2 S_CO S_CO2")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    C = load(a.crafted_zeo, a.henry)
    P = load(a.pilot_zeo, a.pilot_henry)
    T = load(a.test_zeo, a.test_henry)
    print(f"CRAFTED {len(C)} | pilot {len(P)} | holdout {len(T)}")

    rows, preds = [], []
    for t in a.targets:
        c = C[C[t].notna() & C[G].notna().all(axis=1)]
        p = P[P[t].notna() & P[G].notna().all(axis=1)]
        te = T[T[t].notna() & T[G].notna().all(axis=1)]
        if len(te) < 5:
            continue
        for name, w in [("crafted", 0), ("aug_w1", 1), ("aug_w5", 5), ("aug_w20", 20)]:
            if w == 0:
                tr, ytr, sw = c, c[t].values, None
            else:
                tr = pd.concat([c, p]); ytr = tr[t].values
                sw = np.r_[np.ones(len(c)), np.full(len(p), w)]
            m = fit(tr[G].values, ytr, sw)
            pr = m.predict(te[G].values); y = te[t].values
            r2 = 1 - ((y - pr) ** 2).sum() / ((y - y.mean()) ** 2).sum()
            rows.append(dict(target=t, model=name, n_train=len(tr), n_test=len(te), R2=r2,
                             rho=spearmanr(y, pr).statistic, EF10=ef10(y, pr)))
            if name in ("crafted", "aug_w5"):
                d = te[["mof", t]].copy(); d["pred"] = pr; d["model"] = name; preds.append(d)
        print(t, "done", flush=True)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "metrics.csv"), index=False)
    pd.concat(preds).to_csv(os.path.join(a.out, "preds.csv"), index=False)
    print("\n=== mean over targets ===")
    print(R.groupby("model")[["R2", "rho", "EF10"]].mean().round(3).to_string())
    print("\n=== per target ===")
    print(R.pivot(index="target", columns="model", values="rho").round(3).to_string())


if __name__ == "__main__":
    main()
