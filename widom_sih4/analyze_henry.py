#!/usr/bin/env python3
"""Widom Henry 常数 -> SiH4 体系的 R² 摸底（沿用 r2_probe 的特征组和交叉验证口径）。

目标量（均取 log10）：
  K_SiH4                SiH4 的 Henry 常数
  S_<杂质>              K_杂质 / K_SiH4（痕量极限选择性；>1 表示材料优先吸杂质）
  S_bottleneck          各 MOF 对 7 种杂质中"最难分"的那个：min_i |log10 S_i|（越接近 0 越难分）
另做一致性检查：Widom 的 K_CO2/K_N2 与 CRAFTED 等温线得到的经验低压选择性比较（同力场同电荷，应高度一致）。

用法:
  python3 analyze_henry.py --henry henry_wide.csv --crafted <CRAFTED-2.0.0> --chem chem_features_DDEC.csv \
                           [--crafted-targets targets_all.csv] --out results/
依赖：numpy pandas scipy scikit-learn lightgbm
"""
import argparse, os, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
from sklearn.model_selection import KFold
import lightgbm as lgb
warnings.filterwarnings("ignore")
IMPS = ["H2", "N2", "O2", "Ar", "CH4", "CO", "CO2"]


def ef10(y, p):
    k = max(1, int(round(0.1 * len(y))))
    return len(set(np.argsort(-y)[:k]) & set(np.argsort(-p)[:k])) / k / 0.1


def cv(X, y, reps=5):
    out = []
    for rep in range(reps):
        p = np.zeros(len(y))
        for tr, te in KFold(5, shuffle=True, random_state=rep).split(X):
            m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=10, subsample=0.8,
                                  subsample_freq=1, colsample_bytree=0.6, reg_lambda=1.0, random_state=rep, verbose=-1)
            m.fit(X[tr], y[tr]); p[te] = m.predict(X[te])
        out.append((1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum(), spearmanr(y, p).statistic, ef10(y, p)))
    o = np.array(out)
    return dict(R2=o[:, 0].mean(), R2_sd=o[:, 0].std(), rho=o[:, 1].mean(), EF10=o[:, 2].mean())


def features(crafted, chem):
    g = pd.read_csv(os.path.join(crafted, "RAC_DBSCAN", "CRAFTED_MOF_geometric.csv")).rename(columns={"FrameworkName": "mof"})
    r = pd.read_csv(os.path.join(crafted, "RAC_DBSCAN", "CRAFTED_MOF_full_featurization_frame.csv")).rename(columns={"FrameworkName": "mof"})
    c = pd.read_csv(chem)
    c = pd.concat([c.drop(columns=["metal"]), pd.get_dummies(c.metal, prefix="M").astype(float)], axis=1)
    G = [x for x in g if x != "mof"]; R = [x for x in r if x != "mof"]; C = [x for x in c if x != "mof"]
    return g.merge(r, on="mof").merge(c, on="mof"), {"G": G, "G+RAC": G + R, "G+Chem": G + C, "G+RAC+Chem": G + R + C}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--henry", required=True); ap.add_argument("--crafted", required=True); ap.add_argument("--chem", required=True)
    ap.add_argument("--crafted-targets", default=None); ap.add_argument("--out", default="results")
    ap.add_argument("--max-rel-err", type=float, default=0.5, help="K 相对误差超过此值的点视为不可靠，剔除")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    H = pd.read_csv(a.henry)
    H = H[(H.status_np == "ok") & (H.status_pol == "ok")].copy()
    T = pd.DataFrame({"mof": H.mof})
    rel = lambda m: H[f"Kerr_{m}"] / H[f"K_{m}"]
    T["K_SiH4"] = np.log10(H.K_SiH4.clip(lower=1e-30)).where(rel("SiH4") < a.max_rel_err)
    for i in IMPS:
        ok = (rel(i) < a.max_rel_err) & (rel("SiH4") < a.max_rel_err)
        T[f"S_{i}"] = np.log10(H[f"K_{i}"].clip(lower=1e-30) / H.K_SiH4.clip(lower=1e-30)).where(ok)
    sub = T[[f"S_{i}" for i in IMPS]].abs()
    T["S_bottleneck"] = sub.min(axis=1, skipna=False)
    T["hardest"] = sub.apply(lambda r: r.idxmin()[2:] if r.notna().any() else None, axis=1)
    T.to_csv(os.path.join(a.out, "henry_targets.csv"), index=False)
    print("最难分杂质分布:\n", T.hardest.value_counts())

    X, FS = features(a.crafted, a.chem)
    L = T.merge(X, on="mof")
    rows = []
    for t in ["K_SiH4"] + [f"S_{i}" for i in IMPS] + ["S_bottleneck"]:
        s = L[L[t].notna()]; y = s[t].values
        y = np.clip(y, *np.percentile(y, [1, 99]))
        for fs, cols in FS.items():
            r = cv(s[cols].values.astype(float), y)
            rows.append(dict(target=t, features=fs, n=len(y), **r)); print(rows[-1], flush=True)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "henry_r2_results.csv"), index=False)
    print(R.pivot(index="target", columns="features", values="R2").round(2))

    if a.crafted_targets:  # Widom vs CRAFTED 等温线 一致性
        C = pd.read_csv(a.crafted_targets); C = C[(C.charge == "DDEC") & (C.ff == "UFF")]
        C = C[["mof", "K_CO2", "K_N2", "S_henry"]].add_prefix("crafted_").rename(columns={"crafted_mof": "mof"})
        M = H.merge(C, on="mof"); msgs = []
        for name, w, c in [("K_CO2", np.log10(M.K_CO2), np.log10(M.crafted_K_CO2)),
                           ("K_N2", np.log10(M.K_N2), np.log10(M.crafted_K_N2)),
                           ("K_CO2/K_N2", np.log10(M.K_CO2 / M.K_N2), np.log10(M.crafted_S_henry))]:
            ok = np.isfinite(w) & np.isfinite(c)
            msgs.append(f"Widom {name} vs CRAFTED 等温线 DSL 外推: n={ok.sum()} r2={pearsonr(w[ok], c[ok]).statistic**2:.3f} "
                        f"rho={spearmanr(w[ok], c[ok]).statistic:.3f} 中位偏差(log10)={np.median(w[ok]-c[ok]):+.3f}")
        print("\n".join(msgs)); open(os.path.join(a.out, "consistency.txt"), "w").write("\n".join(msgs) + "\n")


if __name__ == "__main__":
    main()
