#!/usr/bin/env python3
"""代理模型的适用域门槛。

用 CRAFTED 的 G 特征分布定义适用域：新结构的每个特征换算成在 CRAFTED 中的百分位，
落在 [q_lo, q_hi] 之外即视为分布外。默认只看 9 个有信息量的几何量（NASA/NAV/n_pockets
在 CRAFTED 里大多是 0，放进门槛会过度过滤）。

输出每个结构的 in_domain_1_99 / in_domain_5_95、max_dev（偏离 0.5 的最大百分位）、
以及建议动作 action：proxy（代理模型可打分）或 gcmc（直接精算）。

用法:
  python3 applicability_domain.py --crafted-zeo results/crafted_zeo.csv \
      --features results/ood_zeo.csv --out results/domain
"""
import argparse, json, os
import numpy as np, pandas as pd

FEATURES = ["D_is", "D_fs", "D_isfs", "ASA_m2_cm3", "ASA_m2_g",
            "Unitcell_volume", "Density", "AV_Volume_fraction", "AV_cm3_g"]


def fit(C, cols=FEATURES, q=(1, 5, 95, 99)):
    out = {}
    for c in cols:
        v = pd.to_numeric(C[c], errors="coerce").dropna().values
        out[c] = {f"p{int(p)}": float(np.percentile(v, p)) for p in q}
    return out


def score(X, bounds, cols=FEATURES):
    R = pd.DataFrame(index=X.index)
    ranks = {}
    for c in cols:
        # 用 bounds 里的分位点做分段线性插值，避免把整份 CRAFTED 特征带进门槛
        b = bounds[c]
        v = pd.to_numeric(X[c], errors="coerce").values
        r = np.full(len(v), np.nan)
        for i, x in enumerate(v):
            if not np.isfinite(x):
                continue
            if x <= b["p1"]:
                r[i] = 0.0
            elif x >= b["p99"]:
                r[i] = 1.0
            elif x < b["p5"]:
                r[i] = 0.01 + 0.04 * (x - b["p1"]) / max(b["p5"] - b["p1"], 1e-12)
            elif x <= b["p95"]:
                r[i] = 0.05 + 0.90 * (x - b["p5"]) / max(b["p95"] - b["p5"], 1e-12)
            else:
                r[i] = 0.95 + 0.04 * (x - b["p95"]) / max(b["p99"] - b["p95"], 1e-12)
        ranks[c] = r
    RK = pd.DataFrame(ranks, index=X.index)
    R["max_dev"] = (RK.sub(0.5).abs() * 2).max(axis=1)       # 0=中位，1=边界
    R["in_domain_1_99"] = (RK.ge(0.01) & RK.le(0.99)).all(axis=1)
    R["in_domain_5_95"] = (RK.ge(0.05) & RK.le(0.95)).all(axis=1)
    R["action"] = np.where(R.in_domain_5_95, "proxy", "gcmc")
    for c in cols:
        R[f"r_{c}"] = RK[c]
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crafted-zeo", required=True)
    ap.add_argument("--features", required=True)
    ap.add_argument("--out", default="results/domain")
    ap.add_argument("--cols", nargs="*", default=FEATURES)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    C = pd.read_csv(a.crafted_zeo).rename(columns={"name": "mof", "Density_sa": "Density"})
    X = pd.read_csv(a.features).rename(columns={"name": "mof", "Density_sa": "Density"})
    bounds = fit(C, a.cols)
    json.dump(bounds, open(os.path.join(a.out, "bounds.json"), "w"), indent=2)
    S = score(X, bounds, a.cols)
    S.insert(0, "mof", X["mof"].values)
    S.to_csv(os.path.join(a.out, "domain_scores.csv"), index=False)
    print(f"{len(S)} 个结构；1–99% 域内 {S.in_domain_1_99.sum()}；5–95% 域内 {S.in_domain_5_95.sum()}")
    print(S.sort_values("max_dev").head(10)[["mof", "max_dev", "in_domain_1_99", "in_domain_5_95", "action"]].to_string(index=False))


if __name__ == "__main__":
    main()
