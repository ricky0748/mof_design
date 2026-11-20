#!/usr/bin/env python3
"""给生产批次做完整 8 分子打分：G+Chem，CRAFTED + 132 个组装标签扩训。

目标：K_SiH4 + S_H2/S_N2/S_O2/S_Ar/S_CH4/S_CO/S_CO2。
Chem 特征全部用 PACMOF 电荷；适用域用扩训后的 G 特征分位数。

用法（项目根目录）:
  python3 generation/score_candidates_full.py \
      --gen-g widom_sih4/results/gen_zeo.csv --gen-chem widom_sih4/results/chem_gen_pacmof.csv \
      --gen-meta generation/out/candidates.csv --out generation/scored_full.csv
"""
import argparse, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "widom_sih4"))
from ood_chem_eval import load, add_metal, CHEM
from ood_augment_eval import fit, G, IMPS
from applicability_domain import fit as dom_fit, score as dom_score, FEATURES

TARGETS = ["K_SiH4"] + [f"S_{i}" for i in IMPS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crafted-g", default=os.path.join(ROOT, "widom_sih4/results/crafted_zeo.csv"))
    ap.add_argument("--crafted-chem", default=os.path.join(ROOT, "widom_sih4/results/chem_crafted_pacmof.csv"))
    ap.add_argument("--henry", default=os.path.join(ROOT, "widom_sih4/results/henry_wide_pacmof.csv"))
    ap.add_argument("--ood-g", nargs="+", default=[os.path.join(ROOT, "widom_sih4/results/ood_zeo.csv"),
                                                    os.path.join(ROOT, "widom_sih4/results/holdout_zeo.csv")])
    ap.add_argument("--ood-chem", default=os.path.join(ROOT, "widom_sih4/results/chem_ood_pacmof.csv"))
    ap.add_argument("--ood-henry", nargs="+", default=[os.path.join(ROOT, "widom_sih4/results/ood_pilot_henry_pacmof.csv"),
                                                       os.path.join(ROOT, "widom_sih4/results/ood_holdout_henry_pacmof.csv")])
    ap.add_argument("--gen-g", required=True); ap.add_argument("--gen-chem", required=True)
    ap.add_argument("--gen-meta", default=os.path.join(ROOT, "generation/out/candidates.csv"))
    ap.add_argument("--out", default=os.path.join(ROOT, "generation/scored_full.csv"))
    ap.add_argument("--weight", type=float, default=20.0)
    ap.add_argument("--max-err", type=float, default=0.5)
    a = ap.parse_args()

    C = load(a.crafted_g, a.crafted_chem, a.henry)
    O = pd.concat([load(g, a.ood_chem, h) for g, h in zip(a.ood_g, a.ood_henry)], ignore_index=True).drop_duplicates("mof")
    gen_g = pd.read_csv(a.gen_g).rename(columns={"name": "mof", "Density_sa": "Density"})
    gen_c = pd.read_csv(a.gen_chem)
    gen = gen_g.merge(gen_c, on="mof")
    metals = sorted(set(C.metal) | set(O.metal) | set(gen.metal))
    C, O, gen = add_metal(C, metals), add_metal(O, metals), add_metal(gen, metals)
    FEATS = G + CHEM + [f"M_{m}" for m in metals]
    print(f"CRAFTED {len(C)} | OOD {len(O)} | generated {len(gen)} | features {len(FEATS)}")

    pred = gen[["mof"]].copy()
    for t in TARGETS:
        c = C[C[t].notna() & C[G].notna().all(axis=1)]
        o = O[O[t].notna() & O[G].notna().all(axis=1)]
        if len(c) < 30 or len(o) < 3:
            print("skip", t, len(c), len(o)); continue
        tr = pd.concat([c, o]); y = tr[t].values
        sw = np.r_[np.ones(len(c)), np.full(len(o), a.weight)]
        m = fit(tr[FEATS].values.astype(float), y, sw)
        pred["pred_" + t] = m.predict(gen[FEATS].values.astype(float))
        print(t, "ok", len(c), len(o), flush=True)

    bounds = dom_fit(pd.concat([C[G], O[G]], ignore_index=True), FEATURES)
    dom = dom_score(gen_g, bounds, FEATURES)
    pred = pd.concat([pred, dom.drop(columns=[c for c in dom.columns if c.startswith("r_")])], axis=1)

    meta = pd.read_csv(a.gen_meta)
    meta = meta[meta.success].copy(); meta["mof"] = meta.variant_id + "_" + meta.topo
    out = meta.merge(pred, on="mof", how="inner")
    # novelty 标注也带上
    ann_path = os.path.join(ROOT, "generation/annotated.csv")
    if os.path.exists(ann_path):
        ann = pd.read_csv(ann_path)[["mof", "novelty_tier", "known_name"]]
        out = out.merge(ann, on="mof", how="left")
    out.to_csv(a.out, index=False)
    print(f"\n打分 {len(out)} 个候选 -> {a.out}")
    print("action:", out.action.value_counts().to_dict())
    for t in ["pred_S_CO2", "pred_S_N2", "pred_S_H2"]:
        if t in out:
            print(t, "positive:", int((out[t] > 0).sum()), "median", round(float(out[t].median()), 3))
    cols = ["mof", "seed", "topo", "novelty_tier", "pred_S_CO2", "pred_S_N2", "pred_S_H2", "pred_S_CH4", "max_dev", "action"]
    cols = [c for c in cols if c in out.columns]
    print("\nTop in-domain by pred_S_CO2:")
    P = out[out.action == "proxy"] if "action" in out else out
    print(P.sort_values("pred_S_CO2", ascending=False)[cols].head(15).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
