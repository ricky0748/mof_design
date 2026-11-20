"""描述符 → 吸附量/选择性/综合分 的可解释性摸底（CRAFTED 690 MOF，298 K）。

主标签：UFF + DDEC 电荷（CoRE-2014 原生电荷）。
特征组：G（14 个 Zeo++ 几何量）、G+RAC（+176 个 RAC）、G+Chem（+元素/电荷统计）、G+RAC+Chem。
模型：LightGBM，5 折 × 5 次重复交叉验证；对照 RF。
指标：R²、Spearman ρ、top-10% 富集因子 EF10（预测前 10% 中真实前 10% 的比例 / 0.1）。
另算"标签方法学不确定度"：同一目标在不同电荷方案/力场之间的一致性。
"""
import numpy as np, pandas as pd, glob, json, warnings
from scipy.stats import spearmanr, pearsonr
from sklearn.model_selection import KFold
from sklearn.ensemble import RandomForestRegressor
import lightgbm as lgb
warnings.filterwarnings("ignore")

U = "/mnt/user-data/uploads/"
TARGETS = {"N_CO2_15kPa": "CO2 吸附量 (0.15 bar)", "S_henry": "Henry 选择性 (痕量极限)",
           "S_iast": "IAST 选择性 (1 bar, 15:85)", "APS": "综合分 APS = S_IAST × ΔN"}


def load_targets():
    T = pd.read_csv("targets_all.csv")
    d = pd.concat([pd.read_csv(f) for f in glob.glob(U + "ai_mof/r2_probe/raw/*.csv")])
    piv = d.pivot_table(index=["mof", "charge", "ff"], columns=["gas", "p_pa"], values="q_molkg")
    emp = pd.DataFrame({"q1bar_CO2": piv[("CO2", 1e5)], "q10bar_N2": piv[("N2", 1e6)]}).reset_index()
    T = T.merge(emp, on=["mof", "charge", "ff"])
    qc = (T.fit_r2_CO2 > 0.98) & (T.fit_r2_N2 > 0.95) & (T.q1bar_CO2 > 0.05) & (T.q10bar_N2 > 0.01)
    T = T[qc].copy()
    for t in TARGETS:
        T[t] = np.log10(T[t].clip(lower=1e-6))
    return T


def load_features():
    g = pd.read_csv(U + "MOF-公开数据库/CRAFTED-2.0.0/RAC_DBSCAN/CRAFTED_MOF_geometric.csv").rename(columns={"FrameworkName": "mof"})
    r = pd.read_csv(U + "MOF-公开数据库/CRAFTED-2.0.0/RAC_DBSCAN/CRAFTED_MOF_full_featurization_frame.csv").rename(columns={"FrameworkName": "mof"})
    c = pd.read_csv(U + "ai_mof/r2_probe/chem_features_DDEC.csv")
    c = pd.concat([c.drop(columns=["metal"]), pd.get_dummies(c.metal, prefix="M").astype(float)], axis=1)
    G = [x for x in g.columns if x != "mof"]
    R = [x for x in r.columns if x != "mof"]
    C = [x for x in c.columns if x != "mof"]
    X = g.merge(r, on="mof").merge(c, on="mof")
    return X, {"G": G, "G+RAC": G + R, "G+Chem": G + C, "G+RAC+Chem": G + R + C}


def ef10(y, p):
    k = max(1, int(round(0.1 * len(y))))
    top_true = set(np.argsort(-y)[:k]); top_pred = np.argsort(-p)[:k]
    return len(top_true.intersection(top_pred)) / k / 0.1


def cv_eval(X, y, model="lgb", reps=5, seed=0):
    preds = []
    for rep in range(reps):
        p = np.zeros(len(y))
        for tr, te in KFold(5, shuffle=True, random_state=seed + rep).split(X):
            if model == "lgb":
                m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=10,
                                      subsample=0.8, subsample_freq=1, colsample_bytree=0.6, reg_lambda=1.0,
                                      random_state=rep, verbose=-1)
            else:
                m = RandomForestRegressor(n_estimators=500, min_samples_leaf=2, max_features=0.33, n_jobs=-1, random_state=rep)
            m.fit(X[tr], y[tr]); p[te] = m.predict(X[te])
        preds.append(p)
    res = [dict(R2=1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum(), rho=spearmanr(y, p).statistic, EF10=ef10(y, p)) for p in preds]
    df = pd.DataFrame(res)
    return {k: (df[k].mean(), df[k].std()) for k in df}


def label_agreement(T, ref=("DDEC", "UFF")):
    out = []
    base = T[(T.charge == ref[0]) & (T.ff == ref[1])].set_index("mof")
    for (c, ff), s in T.groupby(["charge", "ff"]):
        if (c, ff) == ref:
            continue
        s = s.set_index("mof"); idx = base.index.intersection(s.index)
        for t in TARGETS:
            a, b = base.loc[idx, t], s.loc[idx, t]
            out.append(dict(target=t, vs=f"{c}/{ff}", n=len(idx), pearson_r2=pearsonr(a, b).statistic ** 2,
                            rho=spearmanr(a, b).statistic, EF10=ef10(a.values, b.values)))
    return pd.DataFrame(out)


def main():
    T = load_targets()
    X, FS = load_features()
    results = []
    for label in [("DDEC", "UFF"), ("NEUTRAL", "UFF")]:
        L = T[(T.charge == label[0]) & (T.ff == label[1])].merge(X, on="mof")
        for t in TARGETS:
            y = L[t].values
            lo, hi = np.percentile(y, [1, 99]); y = np.clip(y, lo, hi)
            for fs, cols in FS.items():
                if label[0] == "NEUTRAL" and "Chem" in fs:
                    pass
                Xm = L[cols].values.astype(float)
                r = cv_eval(Xm, y, "lgb")
                results.append(dict(label="/".join(label), target=t, features=fs, model="LGBM", n=len(y), nfeat=len(cols),
                                    R2=r["R2"][0], R2_sd=r["R2"][1], rho=r["rho"][0], EF10=r["EF10"][0]))
                print(results[-1], flush=True)
            r = cv_eval(L[FS["G+RAC+Chem"]].values.astype(float), y, "rf", reps=3)
            results.append(dict(label="/".join(label), target=t, features="G+RAC+Chem", model="RF", n=len(y),
                                nfeat=len(FS["G+RAC+Chem"]), R2=r["R2"][0], R2_sd=r["R2"][1], rho=r["rho"][0], EF10=r["EF10"][0]))
            print(results[-1], flush=True)
    R = pd.DataFrame(results); R.to_csv("r2_results.csv", index=False)
    A = label_agreement(T); A.to_csv("label_agreement.csv", index=False)
    print(A.groupby("target")[["pearson_r2", "rho", "EF10"]].agg(["min", "median", "max"]).round(3))


if __name__ == "__main__":
    main()
