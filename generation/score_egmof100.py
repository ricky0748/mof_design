#!/usr/bin/env python3
"""用生产 G+Chem 代理给 EGMOF 100 样本打分，并检查适用域与护栏。

模型：CRAFTED 全量 + 132 组装结构 + 15 个生成标签（权重 1/20/20），目标 S_CO2（log10）。
输出：pred_mean/std/ucb、域内标记、D_fs/AV 护栏。
"""
import argparse, os, sys
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--zeo", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generation", "egmof100_zeo.csv"))
ap.add_argument("--chem", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generation", "egmof100_chem.csv"))
ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generation", "egmof100_scores.csv"))
_args = ap.parse_args()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "widom_sih4"))
from ood_chem_eval import load, add_metal, CHEM
from ood_augment_eval import fit, G, targets

R = os.path.join(ROOT, "widom_sih4", "results")
H = os.path.join(ROOT, "generation", "pilot_selection")

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

metals = sorted(set(C.metal) | set(O.metal) | set(gen.metal))
C, O, gen, P = add_metal(C, metals), add_metal(O, metals), add_metal(gen, metals), add_metal(P, metals)
FEATS = G + CHEM + [f"M_{m}" for m in metals]

tr = pd.concat([C[C.S_CO2.notna()], O[O.S_CO2.notna()], P[P.S_CO2.notna()]], ignore_index=True)
y = tr.S_CO2.values.astype(float)
w = np.r_[np.ones(C.S_CO2.notna().sum()), np.full(O.S_CO2.notna().sum(), 20.0),
          np.full(P.S_CO2.notna().sum(), 20.0)]
models = [fit(tr[FEATS].values.astype(float), y, w, seed=s) for s in range(5)]

E = pd.read_csv(_args.zeo).rename(
    columns={"name": "mof", "Density_sa": "Density"})
E = E.merge(pd.read_csv(_args.chem), on="mof")
E["known_metal"] = E.metal.isin(metals)
E["metal_name"] = E.metal
E = add_metal(E, metals)
X = np.vstack([m.predict(E[FEATS].values.astype(float)) for m in models])
E["pred_mean"] = X.mean(0); E["pred_std"] = X.std(0); E["ucb"] = E.pred_mean + E.pred_std

# 适用域：CRAFTED 的 G 特征 5–95%
lo = C[G].quantile(0.05); hi = C[G].quantile(0.95)
E["in_domain_5_95"] = ((E[G] >= lo) & (E[G] <= hi)).all(axis=1)
E["outside_dims"] = ((E[G] < lo) | (E[G] > hi)).sum(axis=1)
E["guard"] = (E.D_fs >= 3.3) & (E.AV_Volume_fraction >= 0.02)

cols = ["mof", "metal_name", "natoms", "pred_mean", "pred_std", "ucb", "in_domain_5_95",
        "outside_dims", "guard", "known_metal", "D_is", "D_fs", "AV_Volume_fraction",
        "Unitcell_volume", "Density"]
E = E.sort_values("ucb", ascending=False)
E[cols].to_csv(_args.out, index=False)

print(f"candidates: {len(E)}")
print("guard pass:", int(E.guard.sum()), "| in domain:", int(E.in_domain_5_95.sum()),
      "| both:", int((E.guard & E.in_domain_5_95).sum()))
print("pred logS>=0.3:", int((E.pred_mean >= 0.3).sum()),
      "| guard+domain+pred>=0.3:", int((E.guard & E.in_domain_5_95 & (E.pred_mean >= 0.3)).sum()))
print("known metals:", int(E.known_metal.sum()), "/", len(E))
print(E[cols].head(15).round(3).to_string(index=False))
