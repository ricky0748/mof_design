"""由 CRAFTED 单组分等温线构建摸底用的目标量。

每条等温线 (mof, charge, ff, gas) 用双位点 Langmuir (DSL) 加权拟合 (权重 1/err^2)，
再从拟合曲线派生：
  K_CO2, K_N2       Henry 常数 (mol/kg/Pa) = q1*b1 + q2*b2
  S_henry           K_CO2/K_N2，低压/痕量极限下的选择性（痕量杂质分离的代理）
  N_CO2_15kPa       纯 CO2 在 0.15 bar 的吸附量 (mol/kg)
  S_iast            IAST CO2/N2 选择性，1 bar，y_CO2 = 0.15
  APS               S_iast * dN，dN = N_CO2^IAST(1 bar, 15%) - N_CO2^pure(1.5 kPa)
                    （Chung 等 2016 的 adsorbent performance score 思路；再生取 0.1 bar 同组成，忽略 N2）
所有压力 Pa，T = 298 K。
"""
import glob, numpy as np, pandas as pd
from scipy.optimize import least_squares, brentq

RAW = "/mnt/user-data/uploads/ai_mof/r2_probe/raw/*.csv"


def dsl(p, q1, b1, q2, b2):
    return q1 * b1 * p / (1 + b1 * p) + q2 * b2 * p / (1 + b2 * p)


def fit_dsl(p, q, e):
    ok = np.isfinite(q) & np.isfinite(e); p, q, e = p[ok], q[ok], e[ok]
    w = 1.0 / np.maximum(e, 1e-3 * max(q.max(), 1e-6) + 1e-6)
    qmax = max(q.max(), 1e-6)
    best = None
    for b1, b2 in [(1e-3, 1e-6), (1e-4, 1e-6), (1e-5, 1e-7), (1e-2, 1e-5)]:
        lo, hi = np.log([1e-6, 1e-12, 1e-6, 1e-12]), np.log([1e3, 1e2, 1e3, 1e2])
        x0 = np.clip(np.log([max(qmax * 0.6, 2e-6), b1, max(qmax * 0.8, 2e-6), b2]), lo + 1e-6, hi - 1e-6)
        r = least_squares(lambda x: (dsl(p, *np.exp(x)) - q) * w, x0,
                          bounds=(np.log([1e-6, 1e-12, 1e-6, 1e-12]), np.log([1e3, 1e2, 1e3, 1e2])))
        if best is None or r.cost < best.cost:
            best = r
    par = np.exp(best.x)
    pred = dsl(p, *par)
    ss = ((q - pred) ** 2).sum(); st = ((q - q.mean()) ** 2).sum() + 1e-30
    return par, 1 - ss / st


def spreading(par, p):
    """约化铺展压 pi*A/RT = ∫0^p q/p dp，DSL 有解析式。"""
    q1, b1, q2, b2 = par
    return q1 * np.log1p(b1 * p) + q2 * np.log1p(b2 * p)


def iast_binary(parA, parB, P, yA):
    yB = 1 - yA
    # 找 xA 使两组分在纯组分压力 P0 下铺展压相等: P*yA = P0A*xA
    def f(xA):
        p0a = P * yA / xA; p0b = P * yB / (1 - xA)
        return spreading(parA, p0a) - spreading(parB, p0b)
    xA = brentq(f, 1e-9, 1 - 1e-9)
    p0a = P * yA / xA; p0b = P * yB / (1 - xA)
    qa0 = dsl(p0a, *parA); qb0 = dsl(p0b, *parB)
    qt = 1.0 / (xA / max(qa0, 1e-12) + (1 - xA) / max(qb0, 1e-12))
    return xA, xA * qt, (1 - xA) * qt


def _fit_one(arg):
    (m, c, ff, g), s = arg
    par, r2 = fit_dsl(s.p_pa.values, s.q_molkg.values, s.q_err.values)
    dh = pd.to_numeric(s.dH_kjmol, errors="coerce")
    return dict(mof=m, charge=c, ff=ff, gas=g, q1=par[0], b1=par[1], q2=par[2], b2=par[3],
                fit_r2=r2, dH_low=dh.iloc[:5].mean())


def main():
    d = pd.concat([pd.read_csv(f) for f in glob.glob(RAW)])
    from multiprocessing import Pool
    groups = [(k, s.sort_values("p_pa")) for k, s in d.groupby(["mof", "charge", "ff", "gas"])]
    with Pool() as pool:
        fits = pool.map(_fit_one, groups, chunksize=50)
    F = pd.DataFrame(fits)
    F.to_csv("dsl_fits.csv", index=False)
    rows = []
    for (m, c, ff), s in F.groupby(["mof", "charge", "ff"]):
        if set(s.gas) != {"CO2", "N2"}:
            continue
        a = s[s.gas == "CO2"].iloc[0]; b = s[s.gas == "N2"].iloc[0]
        pa = a[["q1", "b1", "q2", "b2"]].values.astype(float); pb = b[["q1", "b1", "q2", "b2"]].values.astype(float)
        KA = pa[0] * pa[1] + pa[2] * pa[3]; KB = pb[0] * pb[1] + pb[2] * pb[3]
        try:
            xA, nA, nB = iast_binary(pa, pb, 1e5, 0.15)
            s_iast = (nA / max(nB, 1e-12)) / (0.15 / 0.85)
            dN = nA - dsl(1.5e3, *pa)
        except Exception:
            s_iast, nA, dN = np.nan, np.nan, np.nan
        rows.append(dict(mof=m, charge=c, ff=ff, K_CO2=KA, K_N2=KB, S_henry=KA / max(KB, 1e-30),
                         N_CO2_15kPa=dsl(1.5e4, *pa), N_CO2_mix=nA, S_iast=s_iast, dN=dN,
                         APS=s_iast * dN if dN == dN else np.nan,
                         dH_CO2=a.dH_low, dH_N2=b.dH_low, fit_r2_CO2=a.fit_r2, fit_r2_N2=b.fit_r2))
    T = pd.DataFrame(rows)
    T.to_csv("targets_all.csv", index=False)
    print(T.describe().T)


if __name__ == "__main__":
    main()
