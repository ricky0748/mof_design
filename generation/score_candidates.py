#!/usr/bin/env python3
"""给生产批次的候选 CIF 打分：代理预测 + 扩训后的适用域门槛。

训练集 = CRAFTED 690 + 132 个已标注组装结构（权重 5）。
目标 = np 组：K_SiH4、S_H2、S_Ar、S_CH4（pol 组等 PACMOF 计算完成后再补）。
适用域 = 在扩训集上重新拟合的几何分位数（9 个有信息量特征）。

用法（从项目根目录运行）:
  python3 generation/score_candidates.py \
      --gen-features /path/gen_zeo.csv --gen-meta generation/out/candidates.csv \
      --out generation/scored.csv
"""
import argparse, os, sys, warnings
import numpy as np, pandas as pd
import lightgbm as lgb
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "widom_sih4"))
sys.path.insert(0, os.path.join(ROOT, "generation"))
from applicability_domain import fit, score, FEATURES
from ood_augment_eval import load, fit as lgb_fit

G = FEATURES
TARGETS = ["K_SiH4", "S_H2", "S_Ar", "S_CH4"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crafted-zeo", default=os.path.join(ROOT, "widom_sih4/results/crafted_zeo.csv"))
    ap.add_argument("--henry", default=os.path.join(ROOT, "widom_sih4/results/henry_wide.csv"))
    ap.add_argument("--ood-features", nargs="+", default=[
        os.path.join(ROOT, "widom_sih4/results/ood_zeo.csv"),
        os.path.join(ROOT, "widom_sih4/results/holdout_zeo.csv")])
    ap.add_argument("--ood-henry", nargs="+", default=[
        os.path.join(ROOT, "widom_sih4/results/ood_henry_wide.csv"),
        os.path.join(ROOT, "widom_sih4/results/holdout_henry_wide.csv")])
    ap.add_argument("--gen-features", required=True)
    ap.add_argument("--gen-meta", default=os.path.join(ROOT, "generation/out/candidates.csv"))
    ap.add_argument("--out", default=os.path.join(ROOT, "generation/scored.csv"))
    ap.add_argument("--weight", type=float, default=5.0)
    a = ap.parse_args()

    C = load(a.crafted_zeo, a.henry)
    O = pd.concat([load(f, h) for f, h in zip(a.ood_features, a.ood_henry)], ignore_index=True).drop_duplicates("mof")
    gen = pd.read_csv(a.gen_features).rename(columns={"name": "mof", "Density_sa": "Density"})
    print(f"CRAFTED {len(C)} | OOD train {len(O)} | generated {len(gen)}")

    pred = gen[["mof"]].copy()
    for t in TARGETS:
        c = C[C[t].notna() & C[G].notna().all(axis=1)]
        o = O[O[t].notna() & O[G].notna().all(axis=1)]
        tr = pd.concat([c, o]); y = tr[t].values
        sw = np.r_[np.ones(len(c)), np.full(len(o), a.weight)]
        m = lgb_fit(tr[G].values, y, sw)
        pred["pred_" + t] = m.predict(gen[G].values)

    # 适用域：在 CRAFTED + 132 个组装结构上重新拟合
    bounds = fit(pd.concat([C, O], ignore_index=True), G)
    dom = score(gen, bounds, G)
    pred = pd.concat([pred, dom.drop(columns=[c for c in dom.columns if c.startswith("r_")])], axis=1)

    meta = pd.read_csv(a.gen_meta)
    meta = meta[meta.success].copy()
    meta["mof"] = meta.variant_id + "_" + meta.topo
    out = meta.merge(pred, on="mof", how="inner")
    out = out.sort_values(["action", "pred_S_CH4"], ascending=[True, False])
    out.to_csv(a.out, index=False)
    print(f"打分 {len(out)} 个候选 -> {a.out}")
    print(out.action.value_counts().to_dict())
    cols = ["mof", "seed", "topo", "pred_K_SiH4", "pred_S_H2", "pred_S_Ar", "pred_S_CH4",
            "max_dev", "in_domain_5_95", "action"]
    print(out[cols].head(12).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
