#!/usr/bin/env python3
"""评价 MOFDiff 弛豫后标签对代理的扩训效果（leave-one-out）。

训练集与生产代理一致：CRAFTED + 132 组装 + 15 生成标签（权重 1/20/20）。
评价集：41 个 UFF 有效 MOFDiff 结构（带 Widom 标签，log10 S_CO2）。
  - baseline：只用原训练集预测 41 个，算 rho / EF10 / R2；
  - aug_w*：LOO，训练集 + 其余 40 个（权重 w），预测留出的 1 个。
用法:
  python3 mofdiff_aug_eval.py --mofdiff-zeo ... --mofdiff-chem ... --mofdiff-henry ... --out ...
"""
import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "widom_sih4"))
from ood_chem_eval import load, add_metal, CHEM  # noqa: E402
from ood_augment_eval import fit, G, targets, ef10  # noqa: E402

R = os.path.join(ROOT, "widom_sih4", "results")
H = os.path.join(ROOT, "generation", "pilot_selection")
TARGET = "S_CO2"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / den, (c + h) / den)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mofdiff-zeo", required=True)
    ap.add_argument("--mofdiff-chem", required=True)
    ap.add_argument("--mofdiff-henry", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--min-logk", type=float, default=-9.0,
                    help="排除 log10(K_SiH4) 低于此值的不可评估结构（孔道塌缩/不吸附）")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)

    C = load(os.path.join(R, "crafted_zeo.csv"), os.path.join(R, "chem_crafted_pacmof.csv"),
             os.path.join(R, "henry_wide_pacmof.csv"))
    O = pd.concat([
        load(os.path.join(R, "ood_zeo.csv"), os.path.join(R, "chem_ood_pacmof.csv"),
             os.path.join(R, "ood_pilot_henry_pacmof.csv")),
        load(os.path.join(R, "holdout_zeo.csv"), os.path.join(R, "chem_ood_pacmof.csv"),
             os.path.join(R, "ood_holdout_henry_pacmof.csv")),
    ], ignore_index=True).drop_duplicates("mof")
    gen = pd.read_csv(os.path.join(R, "gen_zeo.csv")).rename(columns={"name": "mof", "Density_sa": "Density"})
    gen = gen.merge(pd.read_csv(os.path.join(R, "chem_gen_pacmof.csv")), on="mof")
    P1 = targets(pd.read_csv(os.path.join(H, "pilot_merged.csv")))
    P2 = targets(pd.read_csv(os.path.join(H, "feedback_merged.csv")))
    P = pd.concat([P1, P2], ignore_index=True).drop_duplicates("mof").merge(gen, on="mof")

    M = load(a.mofdiff_zeo, a.mofdiff_chem, a.mofdiff_henry)
    metals = sorted(set(C.metal) | set(O.metal) | set(gen.metal) | set(M.metal))
    C, O, gen, P, M = [add_metal(d, metals) for d in (C, O, gen, P, M)]
    FEATS = G + CHEM + [f"M_{m}" for m in metals]

    tr = pd.concat([C[C[TARGET].notna()], O[O[TARGET].notna()], P[P[TARGET].notna()]],
                   ignore_index=True)
    y = tr[TARGET].values.astype(float)
    w0 = np.r_[np.ones(C[TARGET].notna().sum()), np.full(O[TARGET].notna().sum(), 20.0),
               np.full(P[TARGET].notna().sum(), 20.0)]

    Mv = M[M[TARGET].notna() & M[G].notna().all(axis=1) & (M["K_SiH4"] > a.min_logk)].reset_index(drop=True)
    yM = Mv[TARGET].values.astype(float)
    print(f"train {len(tr)} | MOFDiff eval {len(Mv)} | hit rate {(yM >= 0.3).mean():.3f}")

    # baseline（生产模型）
    preds = np.vstack([fit(tr[FEATS].values.astype(float), y, w0, seed=s).predict(
        Mv[FEATS].values.astype(float)) for s in range(5)]).mean(0)
    r2 = 1 - ((yM - preds) ** 2).sum() / ((yM - yM.mean()) ** 2).sum()
    base = dict(model="baseline", weight=0, rho=spearmanr(yM, preds).statistic,
                EF10=ef10(yM, preds), R2=r2)

    rows = [base]
    for w in (1.0, 5.0, 20.0):
        pred = np.zeros(len(Mv))
        for i in range(len(Mv)):
            mask = np.ones(len(Mv), bool); mask[i] = False
            tr2 = pd.concat([tr, Mv.loc[mask]], ignore_index=True)
            y2 = np.r_[y, yM[mask]]
            sw = np.r_[w0, np.full(mask.sum(), w)]
            ps = [fit(tr2[FEATS].values.astype(float), y2, sw, seed=s).predict(
                Mv.loc[[i], FEATS].values.astype(float))[0] for s in range(a.seeds)]
            pred[i] = float(np.mean(ps))
        r2 = 1 - ((yM - pred) ** 2).sum() / ((yM - yM.mean()) ** 2).sum()
        rows.append(dict(model=f"aug_w{w:g}", weight=w, rho=spearmanr(yM, pred).statistic,
                         EF10=ef10(yM, pred), R2=r2))
        Mv[f"pred_{w:g}"] = pred
        print(rows[-1], flush=True)

    Mv["pred_baseline"] = preds
    Rdf = pd.DataFrame(rows)
    Rdf.to_csv(a.out, index=False)
    Mv[["mof", TARGET, "pred_baseline"] + [c for c in Mv.columns if c.startswith("pred_") and c != "pred_baseline"]].to_csv(
        a.out.replace(".csv", "_preds.csv"), index=False)

    k = int((yM >= 0.3).sum()); lo, hi = wilson(k, len(yM))
    print(f"\nWidom hit rate (logS>=0.3): {k}/{len(yM)} = {k/len(yM):.3f} (Wilson {lo:.3f}-{hi:.3f})")
    print(Rdf.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
