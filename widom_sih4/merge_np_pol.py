#!/usr/bin/env python3
"""把 np 组（无电荷，电荷无关）和 PACMOF pol 组的结果合并成一份 henry_wide.csv。

np 组的 K 只取 SiH4/H2/Ar/CH4；pol 组的 K 只取 N2/O2/CO/CO2。
两组可以来自不同的计算批次（np 用 DDEC 批、pol 用 PACMOF 批），因为 np 组不读框架电荷。

用法:
  # CRAFTED：np 用原 DDEC 结果，pol 用 PACMOF 结果
  python3 merge_np_pol.py --np results/henry_wide.csv \
      --pol /path/widom_pacmof/results/henry_wide.csv --out results/henry_wide_pacmof.csv
  # OOD：np 是 41+91 两批，pol 是 132 的 PACMOF 结果
  python3 merge_np_pol.py --np results/ood_henry_wide.csv results/holdout_henry_wide.csv \
      --pol /path/ood_pol_results/henry_wide.csv --out results/ood_henry_wide_pacmof.csv
"""
import argparse
import pandas as pd

NP = ["SiH4", "H2", "Ar", "CH4"]
POL = ["N2", "O2", "CO", "CO2"]
VALS = ("K", "Kerr", "U")


def cols(mols):
    return [f"{p}_{m}" for m in mols for p in VALS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--np", nargs="+", required=True)
    ap.add_argument("--pol", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    npd = pd.concat([pd.read_csv(f) for f in a.np], ignore_index=True)
    pol = pd.read_csv(a.pol)
    A = npd[["mof", "status_np"] + cols(NP)].copy()
    B = pol[["mof", "status_pol"] + cols(POL)].copy()
    M = A.merge(B, on="mof", how="outer")
    M.to_csv(a.out, index=False)
    print(f"{len(M)} 个 MOF -> {a.out}")
    print("status_np:", M.status_np.value_counts().to_dict())
    print("status_pol:", M.status_pol.value_counts().to_dict())


if __name__ == "__main__":
    main()
