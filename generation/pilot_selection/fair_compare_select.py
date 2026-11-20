#!/usr/bin/env python3
"""同预算命中密度对照的选择：held-out 已知库 vs 生成池。

协议见 fair_compare_registration.md。只做计算，不涉及实验。
"""
import argparse, hashlib, os, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

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
FEEDBACK = {"V0006_nbo", "V0048_nbo", "V0047_nbo", "V0067_nbo", "V0024_nbo"}


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
    ap.add_argument("--scored", default=os.path.join(ROOT, "generation/scored_full.csv"))
    ap.add_argument("--pilot-labels", default=os.path.join(HERE, "pilot_merged.csv"))
    ap.add_argument("--feedback-labels", default=os.path.join(HERE, "feedback_merged.csv"))
    ap.add_argument("--holdout-frac", type=float, default=100/690)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--n-select", type=int, default=5)
    ap.add_argument("--min-dfs", type=float, default=3.3, help="最小 D_fs（Å），排除孔道阻塞造成的假高选择性")
    ap.add_argument("--min-av", type=float, default=0.02, help="最小 AV 体积分数")
    ap.add_argument("--rank-out", default=None, help="可选：保存两臂完整 UCB 排名")
    ap.add_argument("--exclude", nargs="*", default=[], help="排除已跑过的候选（跨划分复用时不重复跑）")
    ap.add_argument("--registration-out", default=os.path.join(HERE, "fair_compare_registration.md"))
    ap.add_argument("--out", default=os.path.join(HERE, "fair_compare_selected.csv"))
    a = ap.parse_args()

    C = load(a.crafted_g, a.crafted_chem, a.henry)
    O = pd.concat([load(g, a.ood_chem, h) for g, h in zip(a.ood_g, a.ood_henry)], ignore_index=True).drop_duplicates("mof")
    gen_g = pd.read_csv(a.gen_g).rename(columns={"name": "mof", "Density_sa": "Density"})
    gen = gen_g.merge(pd.read_csv(a.gen_chem), on="mof")
    # 生成池的已有标签（15 个命中）
    P1 = targets(pd.read_csv(a.pilot_labels))
    P2 = targets(pd.read_csv(a.feedback_labels))
    P = pd.concat([P1, P2], ignore_index=True).drop_duplicates("mof")
    P = P.merge(gen, on="mof")
    metals = sorted(set(C.metal) | set(O.metal) | set(gen.metal))
    C, O, gen = add_metal(C, metals), add_metal(O, metals), add_metal(gen, metals)
    P = add_metal(P, metals)
    FEATS = G + CHEM + [f"M_{m}" for m in metals]

    # 固定划分：CRAFTED 690 → train / held-out known
    C = C.reset_index(drop=True)
    rng = np.random.default_rng(a.seed)
    hold_idx = rng.choice(len(C), size=int(round(len(C) * a.holdout_frac)), replace=False)
    mask = np.zeros(len(C), dtype=bool); mask[hold_idx] = True
    C_train, C_hold = C[~mask].copy(), C[mask].copy()
    print(f"C train {len(C_train)} hold {len(C_hold)} | OOD {len(O)} | gen labels {len(P)} | feats {len(FEATS)}")

    tr = pd.concat([C_train[C_train.S_CO2.notna()], O[O.S_CO2.notna()], P[P.S_CO2.notna()]], ignore_index=True)
    y = tr.S_CO2.values
    sw = np.r_[np.ones(len(C_train[C_train.S_CO2.notna()])), np.full(len(O[O.S_CO2.notna()]), 20.0),
               np.full(len(P[P.S_CO2.notna()]), 20.0)]
    models = [fit(tr[FEATS].values.astype(float), y, sw, seed=s) for s in range(5)]
    print("trained 5 models")

    def ucb(df):
        X = np.vstack([m.predict(df[FEATS].values.astype(float)) for m in models])
        d = df.copy(); d["pred_mean"] = X.mean(0); d["pred_std"] = X.std(0); d["ucb"] = d.pred_mean + d.pred_std
        return d

    EXCL = set(a.exclude)
    known_pool = C_hold[C_hold[FEATS].notna().all(axis=1) &
                        (C_hold.D_fs >= a.min_dfs) & (C_hold.AV_Volume_fraction >= a.min_av) &
                        (~C_hold.mof.isin(EXCL))]
    known_rank = ucb(known_pool).sort_values("ucb", ascending=False).reset_index(drop=True)
    known = known_rank.head(a.n_select).copy()
    S = pd.read_csv(a.scored)
    pool = S[(S.action == "proxy") & (~S.mof.isin(VALIDATED)) & (~S.mof.isin(PILOT)) &
             (~S.mof.isin(FEEDBACK)) & (S.novelty_tier != "known_control")].copy()
    gpool = pool.merge(gen[["mof"] + FEATS], on="mof")
    gpool = gpool[gpool[FEATS].notna().all(axis=1) & (gpool.D_fs >= a.min_dfs) &
                  (gpool.AV_Volume_fraction >= a.min_av) & (~gpool.mof.isin(EXCL))]
    gen_rank = ucb(gpool).sort_values("ucb", ascending=False).reset_index(drop=True)
    gen_pool = gen_rank.head(a.n_select).copy()
    print(f"pools after guard: known {len(known_pool)} / generated {len(gpool)}")
    if a.rank_out:
        rk = pd.concat([
            known_rank.assign(arm="known_holdout", smiles=None, topo=None, novelty=None),
            gen_rank.assign(arm="generated").rename(columns={"novelty_tier": "novelty"})[
                ["arm", "mof", "smiles", "topo", "novelty", "pred_mean", "pred_std", "ucb"]]
        ], ignore_index=True)
        rk.to_csv(a.rank_out, index=False)
        print("ranked ->", a.rank_out)

    rows = []
    for _, r in known.iterrows():
        rows.append(dict(arm="known_holdout", mof=r.mof, smiles=None, topo=None,
                         pred_mean=r.pred_mean, pred_std=r.pred_std, ucb=r.ucb, novelty=None))
    for _, r in gen_pool.iterrows():
        rows.append(dict(arm="generated", mof=r.mof, smiles=r.smiles, topo=r.topo,
                         pred_mean=r.pred_mean, pred_std=r.pred_std, ucb=r.ucb, novelty=r.novelty_tier))
    out = pd.DataFrame(rows)
    out.to_csv(a.out, index=False)
    h = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
    print(out.round(3).to_string(index=False)); print("sha256", h)

    reg = f"""# 同预算命中密度对照（2026-10-28）

- 候选文件：`generation/pilot_selection/fair_compare_selected.csv`，sha256 `{h}`
- 问题：在同等 GCMC 预算下，生成池的选择命中率是否高于 held-out 已知库？
- 已知库：CRAFTED 690，固定随机种子 {a.seed} 抽 100 个 held-out；训练集不含这些结构。
- 生成池：268 个规则式候选中排除已验证 15 个、试点 10 个、反馈 5 个、known control 17 个。
- 模型：G+Chem 集成（5×LightGBM；CRAFTED train + 132 组装 + 15 个生成标签；权重 20）。
- 适用域/孔径护栏：D_fs ≥ {a.min_dfs} Å 且 AV_Volume_fraction ≥ {a.min_av}；两臂相同。目的：排除极小孔（D_fs 2.4–2.7 Å）造成的“孔道阻塞假高选择性”（此前试选曾出现 logS_CO2 ≈ 14.7 的记录，已作废，未跑 GCMC）。
- 选择：两个池各按 UCB = mean + 1.0×std 选前 {a.n_select} 个；不做池间调参。
- 精算：298 K、1 bar、CO₂ 1000 ppm、SiH₄ 平衡；PACMOF/UFF/Ewald；30k cycles / 5k init。
- 判定：GCMC logS_CO2 ≥ 0.3、q_SiH4 ≤ 1.5 mol/kg、**q_CO2 ≥ 0.001 mol/kg**（容量地板）；比较两臂命中率。
- 预算：每个臂 {a.n_select} 个 GCMC，共 {2*a.n_select} 个；不追加临时候选。
- 说明：已知库 held-out 的标签只用于评估，不参与选择；生成池的 15 个已有标签参与训练，但已从池中排除。
- 登记时间：{datetime.now(timezone.utc).isoformat()}
"""
    open(a.registration_out, "w", encoding="utf-8").write(reg)
    print("registration written")


if __name__ == "__main__":
    main()
