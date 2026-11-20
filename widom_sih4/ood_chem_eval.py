#!/usr/bin/env python3
"""比较 G-only 与 G+Chem 在组装结构 OOD 扩训上的表现（重点 CO2）。

所有 Chem 特征都用 PACMOF 电荷（与 OOD/生成结构同口径）。
用法:
  python3 ood_chem_eval.py --crafted-g results/crafted_zeo.csv --crafted-chem results/chem_crafted_pacmof.csv \
      --henry results/henry_wide_pacmof.csv --pilot-g results/ood_zeo.csv --pilot-chem results/chem_ood_pacmof.csv \
      --pilot-henry results/ood_pilot_henry_pacmof.csv --test-g results/holdout_zeo.csv \
      --test-chem results/chem_ood_pacmof.csv --test-henry results/ood_holdout_henry_pacmof.csv \
      --targets S_CO2 S_N2 S_O2 S_CO --out results/ood_chem_eval
"""
import argparse, os, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr
warnings.filterwarnings("ignore")
from ood_augment_eval import targets, fit, ef10, G

CHEM = ["natoms", "n_metal_types", "f_metal", "f_N", "f_O", "f_H", "f_C", "f_hal", "f_S", "f_P",
        "q_absmean", "q_std", "q_max", "q_min", "q_metal_mean", "q_metal_max", "f_q_gt05", "f_q_gt1"]


def load(g_csv, chem_csv, henry_csv):
    Gf = pd.read_csv(g_csv).rename(columns={"name": "mof", "Density_sa": "Density"})
    Cf = pd.read_csv(chem_csv)
    T = targets(pd.read_csv(henry_csv))
    return T.merge(Gf, on="mof").merge(Cf, on="mof")


def add_metal(d, metals):
    for m in metals:
        d[f"M_{m}"] = (d.metal == m).astype(float)
    return d.drop(columns=["metal"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crafted-g", required=True); ap.add_argument("--crafted-chem", required=True); ap.add_argument("--henry", required=True)
    ap.add_argument("--pilot-g", required=True); ap.add_argument("--pilot-chem", required=True); ap.add_argument("--pilot-henry", required=True)
    ap.add_argument("--test-g", required=True); ap.add_argument("--test-chem", required=True); ap.add_argument("--test-henry", required=True)
    ap.add_argument("--targets", nargs="*", default=["S_CO2"])
    ap.add_argument("--weight", type=float, default=20.0)
    ap.add_argument("--out", default="results/ood_chem_eval")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    C = load(a.crafted_g, a.crafted_chem, a.henry)
    P = load(a.pilot_g, a.pilot_chem, a.pilot_henry)
    T = load(a.test_g, a.test_chem, a.test_henry)
    metals = sorted(set(C.metal) | set(P.metal) | set(T.metal))
    C, P, T = add_metal(C, metals), add_metal(P, metals), add_metal(T, metals)
    CHEM_ALL = CHEM + [f"M_{m}" for m in metals]
    FS = {"G": G, "G+Chem": G + CHEM_ALL}
    print(f"CRAFTED {len(C)} | pilot {len(P)} | holdout {len(T)} | metals {metals}")

    rows = []
    for t in a.targets:
        c = C[C[t].notna() & C[G].notna().all(axis=1)]
        p = P[P[t].notna() & P[G].notna().all(axis=1)]
        te = T[T[t].notna() & T[G].notna().all(axis=1)]
        for fs, cols in FS.items():
            for name, w in [("crafted", 0), ("aug", a.weight)]:
                if w == 0:
                    tr, y, sw = c, c[t].values, None
                else:
                    tr = pd.concat([c, p]); y = tr[t].values
                    sw = np.r_[np.ones(len(c)), np.full(len(p), w)]
                m = fit(tr[cols].values.astype(float), y, sw)
                pr = m.predict(te[cols].values.astype(float)); yy = te[t].values
                r2 = 1 - ((yy - pr) ** 2).sum() / ((yy - yy.mean()) ** 2).sum()
                rows.append(dict(target=t, features=fs, model=name, n_train=len(tr), n_test=len(te),
                                 R2=r2, rho=spearmanr(yy, pr).statistic, EF10=ef10(yy, pr)))
                print(rows[-1], flush=True)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "metrics.csv"), index=False)
    print("\n=== rho ===")
    print(R.pivot_table(index="target", columns=["features", "model"], values="rho").round(3).to_string())


if __name__ == "__main__":
    main()
