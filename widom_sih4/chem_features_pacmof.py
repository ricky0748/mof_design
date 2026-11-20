#!/usr/bin/env python3
"""从任意带 _atom_site_charge 的 CIF 提取化学/电荷特征（与 r2_probe/cif_chem_features.py 同定义）。

输出列与 CRAFTED 的 chem_features_DDEC.csv 完全一致，只是电荷换成 PACMOF。
用法:
  python3 chem_features_pacmof.py --cif-dir /path/charged_cif --out chem_pacmof.csv [--strip _charged]
"""
import argparse, csv, os, statistics as st

METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi U Th".split())
FIELDS = ["mof", "natoms", "metal", "n_metal_types", "f_metal", "f_N", "f_O", "f_H", "f_C",
          "f_hal", "f_S", "f_P", "q_absmean", "q_std", "q_max", "q_min", "q_metal_mean",
          "q_metal_max", "f_q_gt05", "f_q_gt1"]


def parse_cif(path):
    lines = open(path, errors="ignore").read().splitlines()
    cols, atoms, inloop = [], [], False
    for l in lines:
        s = l.strip()
        if s == "loop_":
            cols, inloop = [], True; continue
        if inloop and s.startswith("_"):
            cols.append(s); continue
        if inloop and cols and "_atom_site_charge" in cols and s and not s.startswith("_"):
            t = s.split()
            if len(t) >= len(cols):
                sym = t[cols.index("_atom_site_type_symbol")] if "_atom_site_type_symbol" in cols else "".join(ch for ch in t[cols.index("_atom_site_label")] if ch.isalpha())
                sym = sym[:1].upper() + sym[1:2].lower() if len(sym) > 1 and sym[:2].capitalize() in METALS | {"Cl", "Br"} else sym[:1].upper()
                atoms.append((sym, float(t[cols.index("_atom_site_charge")])))
            continue
        if inloop and cols and s and not s.startswith("_"):
            inloop = False
    return atoms


def features(name, atoms):
    el = [a[0] for a in atoms]; q = [a[1] for a in atoms]; N = len(atoms)
    mq = [c for e, c in atoms if e in METALS]
    metals = sorted({e for e in el if e in METALS})
    frac = lambda S: sum(e in S for e in el) / N
    return dict(mof=name, natoms=N, metal=metals[0] if metals else "none", n_metal_types=len(metals),
                f_metal=frac(METALS), f_N=frac({"N"}), f_O=frac({"O"}), f_H=frac({"H"}), f_C=frac({"C"}),
                f_hal=frac({"F", "Cl", "Br", "I"}), f_S=frac({"S"}), f_P=frac({"P"}),
                q_absmean=sum(map(abs, q)) / N, q_std=st.pstdev(q), q_max=max(q), q_min=min(q),
                q_metal_mean=(sum(mq) / len(mq)) if mq else 0.0, q_metal_max=max(mq) if mq else 0.0,
                f_q_gt05=sum(abs(c) > 0.5 for c in q) / N, f_q_gt1=sum(abs(c) > 1.0 for c in q) / N)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cif-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strip", default="_charged")
    a = ap.parse_args()
    rows, bad = [], []
    for f in sorted(os.listdir(a.cif_dir)):
        if not f.endswith(".cif"):
            continue
        name = f[:-4]
        if a.strip and name.endswith(a.strip):
            name = name[:-len(a.strip)]
        try:
            atoms = parse_cif(os.path.join(a.cif_dir, f))
            if not atoms:
                bad.append(f); continue
            rows.append(features(name, atoms))
        except Exception as e:
            bad.append(f + ":" + repr(e)[:60])
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} rows, {len(bad)} bad -> {a.out}")
    if bad:
        print("bad sample:", bad[:10])


if __name__ == "__main__":
    main()
