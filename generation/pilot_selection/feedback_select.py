#!/usr/bin/env python3
"""反馈批次选择：用 CRAFTED + 132 组装标签 + 10 个试点标签训练集成代理，按 UCB 选 5 个。

用法:
  python3 feedback_select.py --out feedback_selected.csv
"""
import argparse, hashlib, os, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd
from sklearn.model_selection import KFold
import lightgbm as lgb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "widom_sih4"))
from ood_chem_eval import load, add_metal, CHEM
from ood_augment_eval import fit, G, targets

VALIDATED = {"V0039_nbo", "V0164_nbo", "V0037_nbo", "V0033_nbo", "V0032_nbo", "V0036_nbo",
             "V0017_nbo", "V0156_nbo", "V0035_nbo", "V0058_nbo", "V0064_fcu", "V0003_fcu",
             "V0001_fcu", "V0000_nbo", "V0011_nbo"}
PILOT = {"V0157_nbo", "V0031_nbo", "V0041_nbo", "V0034_nbo", "V0023_nbo",
         "V0015_pcu", "V0053_nbo", "V0042_pcu", "V0140_fcu", "V0013_pcu"}


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
    ap.add_argument("--gen-g", default=os.path.join(ROOT, "widom_sih4/results/gen_zeo.csv"))
    ap.add_argument("--gen-chem", default=os.path.join(ROOT, "widom_sih4/results/chem_gen_pacmof.csv"))
    ap.add_argument("--pilot-labels", default=os.path.join(HERE, "pilot_merged.csv"))
    ap.add_argument("--scored", default=os.path.join(ROOT, "generation/scored_full.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "feedback_selected.csv"))
    ap.add_argument("--n-select", type=int, default=5)
    ap.add_argument("--beta", type=float, default=1.0)
    a = ap.parse_args()

    C = load(a.crafted_g, a.crafted_chem, a.henry)
    O = pd.concat([load(g, a.ood_chem, h) for g, h in zip(a.ood_g, a.ood_henry)], ignore_index=True).drop_duplicates("mof")
    gen_g = pd.read_csv(a.gen_g).rename(columns={"name": "mof", "Density_sa": "Density"})
    gen_c = pd.read_csv(a.gen_chem)
    gen = gen_g.merge(gen_c, on="mof")
    # 试点标签
    P = targets(pd.read_csv(a.pilot_labels))
    P = P.merge(gen, on="mof")
    metals = sorted(set(C.metal) | set(O.metal) | set(gen.metal))
    C, O, gen = add_metal(C, metals), add_metal(O, metals), add_metal(gen, metals)
    P = P.merge(gen[[c for c in gen.columns if c.startswith("M_")]], left_on="mof", right_index=True, how="left") if False else P
    # add_metal for P via its own metal column
    P = add_metal(P, metals)
    FEATS = G + CHEM + [f"M_{m}" for m in metals]
    print(f"C {len(C)} | O {len(O)} | P {len(P)} | gen {len(gen)} | feats {len(FEATS)}")

    tr = pd.concat([C[C.S_CO2.notna()], O[O.S_CO2.notna()], P[P.S_CO2.notna()]], ignore_index=True)
    y = tr["S_CO2"].values
    sw = np.r_[np.ones(len(C[C.S_CO2.notna()])), np.full(len(O[O.S_CO2.notna()]), 20.0),
               np.full(len(P[P.S_CO2.notna()]), 20.0)]
    models = [fit(tr[FEATS].values.astype(float), y, sw, seed=s) for s in range(5)]
    print("trained 5 models")

    S = pd.read_csv(a.scored)
    pool = S[(S.action == "proxy") & (~S.mof.isin(VALIDATED)) & (~S.mof.isin(PILOT)) &
             (S.novelty_tier != "known_control")].copy()
    X = pool.merge(gen[["mof"] + FEATS], on="mof")
    ps = np.vstack([m.predict(X[FEATS].values.astype(float)) for m in models])
    X["pred_mean"] = ps.mean(0); X["pred_std"] = ps.std(0)
    X["ucb"] = X["pred_mean"] + a.beta * X["pred_std"]
    sel = X.sort_values("ucb", ascending=False).head(a.n_select).copy()
    sel = sel[["mof", "variant_id", "smiles", "topo", "pred_mean", "pred_std", "ucb",
               "pred_S_CO2", "max_dev", "novelty_tier"]]
    sel.to_csv(a.out, index=False)
    h = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
    print(sel.round(3).to_string(index=False)); print("sha256", h)

    reg = f"""# 反馈批次登记（2026-10-26）

- 候选文件：`generation/pilot_selection/feedback_selected.csv`，sha256 `{h}`
- 模型：G+Chem 集成（5 个 LightGBM，CRAFTED + 132 组装 + 10 个试点标签；组装/试点权重 20）
- 选择：在剩余 in-domain 候选池中，排除已验证 15 个、试点 10 个、known control；按 UCB = mean + {a.beta} * std 选前 {a.n_select} 个。
- 条件：298 K，1 bar，CO₂ 1000 ppm，SiH₄ 平衡；PACMOF 电荷 + UFF + Ewald；Widom np+pol，5000 cycles。
- 判定标准（运行前冻结）：`logS_CO2 >= 0.3`（S_CO2 >= 2）记为命中；与初始 proxy_top5 的 5/5、random5 的 1/5 比较。
- 登记时间：{datetime.now(timezone.utc).isoformat()}
"""
    open(os.path.join(HERE, "feedback_registration.md"), "w", encoding="utf-8").write(reg)
    print("registration written")


if __name__ == "__main__":
    main()
