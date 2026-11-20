#!/usr/bin/env python3
"""学习曲线：用多少个组装结构标签，代理模型才能在同类组装结构上恢复排序？

池子 = 41 个试点 + 91 个留出（共 132 个，都有 Widom np 标签和 Zeo++ 特征）。
对每个 N，随机抽 N 个组装结构加入 CRAFTED 训练集（权重 5），在剩余结构上测试；
每个 N 重复 5 个随机划分，报告 4 个目标平均的 R² / ρ / EF10。

用法:
  python3 ood_learning_curve.py --crafted-zeo results/crafted_zeo.csv --henry results/henry_wide.csv \
      --pilot-zeo results/ood_zeo.csv --pilot-henry results/ood_henry_wide.csv \
      --holdout-zeo results/holdout_zeo.csv --holdout-henry results/holdout_henry_wide.csv \
      --out results/ood_learning_curve
"""
import argparse, os, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr
warnings.filterwarnings("ignore")
from ood_augment_eval import load, fit, ef10, G, TARGETS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crafted-zeo", required=True); ap.add_argument("--henry", required=True)
    ap.add_argument("--pilot-zeo", required=True); ap.add_argument("--pilot-henry", required=True)
    ap.add_argument("--holdout-zeo", required=True); ap.add_argument("--holdout-henry", required=True)
    ap.add_argument("--out", default="results/ood_learning_curve")
    ap.add_argument("--sizes", nargs="*", type=int, default=[5, 10, 20, 30, 41, 60, 90, 110])
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--weight", type=float, default=5.0)
    ap.add_argument("--targets", nargs="*", default=TARGETS)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    C = load(a.crafted_zeo, a.henry)
    O = pd.concat([load(a.pilot_zeo, a.pilot_henry), load(a.holdout_zeo, a.holdout_henry)],
                  ignore_index=True).drop_duplicates("mof")
    print(f"CRAFTED {len(C)} | OOD pool {len(O)}")

    rows = []
    for N in a.sizes:
        if N >= len(O):
            continue
        for seed in range(a.repeats):
            rng = np.random.default_rng(seed)
            idx = rng.choice(len(O), N, replace=False)
            tr_o = O.iloc[idx]; te_o = O.drop(index=idx)
            for t in a.targets:
                c = C[C[t].notna() & C[G].notna().all(axis=1)]
                p = tr_o[tr_o[t].notna() & tr_o[G].notna().all(axis=1)]
                te = te_o[te_o[t].notna() & te_o[G].notna().all(axis=1)]
                if len(p) < 3 or len(te) < 5:
                    continue
                tr = pd.concat([c, p]); ytr = tr[t].values
                sw = np.r_[np.ones(len(c)), np.full(len(p), a.weight)]
                m = fit(tr[G].values, ytr, sw, seed=seed)
                pr = m.predict(te[G].values); y = te[t].values
                r2 = 1 - ((y - pr) ** 2).sum() / ((y - y.mean()) ** 2).sum()
                rows.append(dict(N=N, seed=seed, target=t, n_train_ood=len(p), n_test=len(te),
                                 R2=r2, rho=spearmanr(y, pr).statistic, EF10=ef10(y, pr)))
        print("N", N, "done", flush=True)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "runs.csv"), index=False)
    S = R.groupby("N")[["R2", "rho", "EF10"]].agg(["mean", "std"]).round(3)
    print(S.to_string())
    S.to_csv(os.path.join(a.out, "summary.csv"))


if __name__ == "__main__":
    main()
