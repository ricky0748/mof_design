"""稳健性检查：① 用经验低压比 S_emp 代替 DSL 外推的 S_henry；② 标签一致性按对比对拆开；③ 特征重要性。"""
import numpy as np, pandas as pd, glob
from r2_probe import load_features, cv_eval, ef10, U
from scipy.stats import spearmanr, pearsonr
import lightgbm as lgb
T = pd.read_csv("targets_all.csv")
d = pd.concat([pd.read_csv(f) for f in glob.glob(U + "ai_mof/r2_probe/raw/*.csv")])
piv = d.pivot_table(index=["mof", "charge", "ff"], columns=["gas", "p_pa"], values="q_molkg")
emp = pd.DataFrame({"q1bar_CO2": piv[("CO2", 1e5)], "q10bar_N2": piv[("N2", 1e6)],
                    "S_emp": (piv[("CO2", 2e3)] / 2e3) / (piv[("N2", 2e4)] / 2e4).clip(lower=1e-12)}).reset_index()
T = T.merge(emp, on=["mof", "charge", "ff"])
qc = (T.fit_r2_CO2 > 0.98) & (T.fit_r2_N2 > 0.95) & (T.q1bar_CO2 > 0.05) & (T.q10bar_N2 > 0.01) & (T.S_emp > 0)
T = T[qc].copy()
for t in ["S_henry", "S_emp", "S_iast"]:
    T[t] = np.log10(T[t].clip(lower=1e-6))
X, FS = load_features()
rows = []
for lab in [("DDEC", "UFF"), ("NEUTRAL", "UFF")]:
    L = T[(T.charge == lab[0]) & (T.ff == lab[1])].merge(X, on="mof")
    y = L.S_emp.values; lo, hi = np.percentile(y, [1, 99]); y = np.clip(y, lo, hi)
    for fs in ["G", "G+Chem", "G+RAC+Chem"]:
        r = cv_eval(L[FS[fs]].values.astype(float), y)
        rows.append(dict(label="/".join(lab), target="S_emp", features=fs, n=len(y), R2=r["R2"][0], rho=r["rho"][0], EF10=r["EF10"][0]))
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv("robust_semp.csv", index=False)
# 标签一致性逐对
base = T[(T.charge == "DDEC") & (T.ff == "UFF")].set_index("mof")
agree = []
for (c, ff), s in T.groupby(["charge", "ff"]):
    if (c, ff) == ("DDEC", "UFF"): continue
    s = s.set_index("mof"); idx = base.index.intersection(s.index)
    for t in ["S_henry", "S_emp", "S_iast"]:
        a, b = base.loc[idx, t], s.loc[idx, t]
        agree.append(dict(target=t, vs=f"{c}/{ff}", n=len(idx), r2=pearsonr(a, b).statistic ** 2, rho=spearmanr(a, b).statistic, EF10=ef10(a.values, b.values)))
A = pd.DataFrame(agree); A.to_csv("label_agreement_pairs.csv", index=False)
print(A.pivot(index="vs", columns="target", values="rho").round(3))
# 特征重要性（DDEC/UFF，S_henry，G+Chem）
L = T[(T.charge == "DDEC") & (T.ff == "UFF")].merge(X, on="mof")
cols = FS["G+Chem"]; y = np.clip(L.S_henry.values, *np.percentile(L.S_henry.values, [1, 99]))
m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=10, subsample=0.8, subsample_freq=1, colsample_bytree=0.6, verbose=-1, importance_type="gain").fit(L[cols].values.astype(float), y)
imp = pd.Series(m.feature_importances_, index=cols).sort_values(ascending=False); imp = imp / imp.sum()
imp.to_csv("importance_Shenry_GChem.csv"); print(imp.head(12).round(3))
